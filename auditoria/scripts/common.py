"""Utilitarios compartilhados da bateria de testes do Bonsai (somente stdlib)."""
import json, os, subprocess, time, urllib.request

BASE = os.environ.get("BONSAI_URL", "http://127.0.0.1:8080")
MODEL = "bonsai-2-4b"
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


def chat(messages, profile="padrao", max_tokens=512, tools=None, seed=None, extra=None, timeout=1800):
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


def server_proc_stats():
    """RAM/CPU do llama-server via PowerShell (sem dependencias)."""
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
