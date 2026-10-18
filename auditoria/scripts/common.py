"""Utilitarios compartilhados da bateria de testes do Bonsai (somente stdlib)."""
import json, os, re, subprocess, sys, time, urllib.request

BASE = os.environ.get("BONSAI_URL", "http://127.0.0.1:8080")
MODEL = os.environ.get("BONSAI_MODEL", "bonsai-2-4b").strip()
if not MODEL:
    raise ValueError("BONSAI_MODEL nao pode ser vazio")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Perfis de amostragem comparados nos testes
PROFILES = {
    # padrao do iniciar-bonsai.ps1 (recomendacao PrismML para chat sem raciocinio)
    "padrao": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0, "presence_penalty": 1.5},
    # perfil para codigo/agentes: menos aleatoriedade e sem penalidade de presenca
    "agente": {"temperature": 0.2, "top_p": 0.95, "top_k": 20, "min_p": 0, "presence_penalty": 0.0},
}


def post(path, body, timeout=1800):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(path, timeout=10):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read())


_model_verified = False


def verify_model():
    """Impede medir o 4B por engano ao solicitar o 2B (ou vice-versa)."""
    global _model_verified
    if _model_verified:
        return
    response = get("/v1/models")
    available = [item.get("id") for item in response.get("data", []) if isinstance(item, dict)]
    if MODEL not in available:
        raise RuntimeError(
            f"Modelo solicitado {MODEL!r} nao esta ativo em {BASE}. "
            f"Modelos disponiveis: {available}. "
            "Reinicie o servidor com o modelo correto ou defina BONSAI_MODEL."
        )
    _model_verified = True


def chat(messages, profile="padrao", max_tokens=512, tools=None, seed=None, extra=None, timeout=1800):
    verify_model()
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}, **PROFILES[profile]}
    if tools:
        body["tools"] = tools
    if seed is not None:
        body["seed"] = seed
    if extra:
        body.update(extra)
    t0 = time.perf_counter()
    r = post("/v1/chat/completions", body, timeout)
    r["_wall_s"] = time.perf_counter() - t0
    return r


def chat_stream(messages, profile="padrao", max_tokens=128, extra=None):
    """Mede TTFT real pelo stream SSE. Retorna dict com ttft, total e timings do servidor."""
    verify_model()
    body = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "stream": True,
            "chat_template_kwargs": {"enable_thinking": False}, **PROFILES[profile],
            "stream_options": {"include_usage": True}}
    if extra:
        body.update(extra)
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter(); ttft = None; timings = None; text = []
    with urllib.request.urlopen(req, timeout=1800) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            ev = json.loads(payload)
            if ev.get("timings"):
                timings = ev["timings"]
            for ch in ev.get("choices", []):
                piece = (ch.get("delta") or {}).get("content")
                if piece:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    text.append(piece)
    return {"ttft_s": ttft, "total_s": time.perf_counter() - t0, "timings": timings, "text": "".join(text)}


def _linux_proc_stats():
    """Memoria residente e CPU do PID iniciado pelo projeto; nao confundir RSS com private commit."""
    pid_file = os.path.join(os.path.dirname(ROOT), "logs", "server.pid")
    try:
        with open(pid_file, encoding="utf-8") as fh:
            pid = int(fh.read().strip())
        if pid <= 0:
            raise ValueError("PID invalido")
        exe = os.path.realpath(f"/proc/{pid}/exe")
        if not os.path.basename(exe).startswith("llama-server"):
            raise ValueError(f"PID {pid} nao pertence ao llama-server")
        with open(f"/proc/{pid}/status", encoding="utf-8") as fh:
            status = fh.read()
        rss = re.search(r"^VmRSS:\s*(\d+)\s+kB", status, flags=re.M)
        if not rss:
            raise ValueError("VmRSS ausente em /proc")
        with open(f"/proc/{pid}/stat", encoding="utf-8") as fh:
            fields = fh.read().rsplit(")", 1)[1].split()
        cpu_s = (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")
        with open("/proc/meminfo", encoding="utf-8") as fh:
            meminfo = fh.read()
        available = re.search(r"^MemAvailable:\s*(\d+)\s+kB", meminfo, flags=re.M)
        return {
            "ws_mb": int(rss.group(1)) // 1024,
            "priv_mb": None,  # private commit do Windows nao e comparavel a RSS do Linux
            "cpu_s": round(cpu_s, 2),
            "free_mb": int(available.group(1)) // 1024 if available else None,
            "ram_metric": "RSS Linux (ws_mb); priv_mb indisponivel",
        }
    except (OSError, ValueError, IndexError) as error:
        return {"ws_mb": None, "priv_mb": None, "cpu_s": None, "free_mb": None,
                "erro": f"Falha ao ler processo Linux: {error}"}


def server_proc_stats():
    """RAM/CPU do llama-server (PowerShell no Windows; /proc no Linux)."""
    if sys.platform.startswith("linux"):
        return _linux_proc_stats()
    ps = ("$p=Get-Process llama-server -ErrorAction SilentlyContinue | Select -First 1;"
          "$o=Get-CimInstance Win32_OperatingSystem;"
          "if($p){@{ws_mb=[int]($p.WorkingSet64/1MB);priv_mb=[int]($p.PrivateMemorySize64/1MB);cpu_s=$p.CPU;"
          "free_mb=[int]($o.FreePhysicalMemory/1KB)}|ConvertTo-Json -Compress}")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30).stdout
        return json.loads(out) if out.strip() else None
    except Exception as e:  # noqa
        return {"erro": str(e)}


def percentile(values, p):
    v = sorted(values)
    if not v:
        return None
    k = (len(v) - 1) * p / 100
    f = int(k); c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def save(name, obj):
    path = os.path.join(ROOT, "raw", name)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
    return path
