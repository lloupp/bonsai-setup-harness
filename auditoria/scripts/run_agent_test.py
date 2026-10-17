"""Executa a mesma tarefa em Pi, Hermes ou Claude Code com o Bonsai local, em pasta temporaria isolada.
Uso: python run_agent_test.py <pi|hermes|claude> <t1|t2|t3> <rotulo> [orcamento_s]
Mede tempo total, chamadas ao modelo (pelo log do servidor), RAM de pico do harness e verifica o resultado
com um verificador oculto (o agente nao o ve). Variaveis de ambiente valem apenas para o processo filho."""
import json, os, shutil, subprocess, sys, time, threading, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # pasta bonsai
AUD = os.path.join(ROOT, "auditoria")
harness, test, label = sys.argv[1], sys.argv[2], sys.argv[3]
BUDGET = int(sys.argv[4]) if len(sys.argv) > 4 else 3600

PROMPTS = {
    "t1": "Crie o arquivo digitos.py com a funcao soma_digitos(n) que devolve a soma dos digitos de um inteiro (para negativos, use o valor absoluto; soma_digitos(0) == 0). Crie tambem test_digitos.py com testes unittest. Execute os testes com 'python -m unittest' e corrija ate passarem. Ao final diga FEITO.",
    "t2": "Crie um pacote Python 'conversor' nesta pasta com: conversor/core.py (funcoes celsius_para_fahrenheit e fahrenheit_para_celsius que levantam ValueError abaixo do zero absoluto), conversor/__main__.py (CLI: 'python -m conversor c2f 100' imprime 212.0; 'python -m conversor f2c 32' imprime 0.0; entrada invalida imprime mensagem de erro amigavel sem traceback e sai com codigo 1) e tests/test_core.py com testes unittest (crie tests/__init__.py). Rode 'python -m unittest discover -s tests -t .' e corrija ate passar. Ao final diga FEITO.",
    "t3": "Este projeto tem testes falhando. Investigue a estrutura, rode 'python -m unittest discover -s tests -t .', identifique as causas, corrija o codigo em estoque/ (nao altere nem remova os testes), rode os testes novamente e repita ate todos passarem. Ao final diga FEITO e resuma as correcoes.",
}
PROMPTS["t2sub"] = PROMPTS["t2"].replace("Ao final diga FEITO.", "Divida o trabalho: delegue a um SUBAGENTE (ferramenta de delegacao/subagente disponivel) a criacao de tests/test_core.py enquanto voce cria o codigo; depois rode os testes e corrija. Ao final diga FEITO.")

ts = time.strftime("%Y%m%d-%H%M%S")
work = os.path.join(AUD, "agent-tests", "runs", f"{harness}_{test}_{label}_{ts}")
fixture = os.path.join(AUD, "agent-tests", "fixtures", "t3_defeituoso")
if test == "t3":
    shutil.copytree(fixture, work)
else:
    os.makedirs(work)
log_out = work + ".stream.jsonl"
env = os.environ.copy()
prompt = PROMPTS[test]

if harness == "pi":
    cli = os.path.join(ROOT, "pi-runtime", "node_modules", "@earendil-works", "pi-coding-agent", "dist", "bundle", "cli.js")
    env.update(PI_CODING_AGENT_DIR=os.path.join(ROOT, "pi-profile"), PI_OFFLINE="1", PI_SKIP_VERSION_CHECK="1", PI_TELEMETRY="0")
    cmd = ["node", cli, "--provider", "bonsai-local", "--model", os.environ.get("PI_MODEL", "bonsai-2-4b"), "--thinking", "off", "--no-session",
           "--no-extensions", "--no-skills", "--no-prompt-templates", "--no-context-files",
           "--tools", "read,bash,write,edit,ls", "--mode", "json", "--print", prompt]
elif harness == "hermes":
    tools_dir = os.path.join(ROOT, "hermes-profile", "tools")
    py = next(os.path.join(tools_dir, d, "python.exe") for d in os.listdir(tools_dir) if d.startswith("python-"))
    env.update(HERMES_HOME=os.path.join(ROOT, "hermes-profile"), HERMES_RUNTIME_DIR=tools_dir, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    cmd = [py, os.path.join(ROOT, "hermes-test", "launch.py"), "chat", "--toolsets", os.environ.get("HERMES_TOOLSETS", "terminal,file"),
           "--max-turns", "30", "--oneshot", "--format", "stream-json", "--yolo", "--query", prompt]
elif harness == "claude":
    exe = os.path.join(os.environ["USERPROFILE"], ".local", "bin", "claude.exe")
    for k in ("ANTHROPIC_API_KEY",):
        env.pop(k, None)
    env.update(CLAUDE_CONFIG_DIR=os.path.join(ROOT, "claude-test", "profile"), ANTHROPIC_BASE_URL=os.environ.get("CLAUDE_ADAPTER", "http://127.0.0.1:8082"),
               ANTHROPIC_AUTH_TOKEN="bonsai-local", ANTHROPIC_MODEL="bonsai-2-4b", ANTHROPIC_DEFAULT_HAIKU_MODEL="bonsai-2-4b",
               ANTHROPIC_DEFAULT_SONNET_MODEL="bonsai-2-4b", ANTHROPIC_DEFAULT_OPUS_MODEL="bonsai-2-4b",
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1", DISABLE_AUTOUPDATER="1", CLAUDE_CODE_MAX_OUTPUT_TOKENS="4096",
               MAX_THINKING_TOKENS="0", API_TIMEOUT_MS="3600000",
               CLAUDE_CODE_MAX_CONTEXT_TOKENS="65536", CLAUDE_CODE_AUTO_COMPACT_WINDOW="60000")
    tools = os.environ.get("CLAUDE_TOOLS", "Read,Write,Edit,Bash,Glob,Grep")
    cmd = [exe, "-p", prompt, "--model", "bonsai-2-4b", "--output-format", "stream-json", "--verbose", "--no-session-persistence",
           "--max-turns", "30", "--permission-mode", "acceptEdits", "--allowedTools", tools, "--tools", tools]
    extra = os.environ.get("CLAUDE_EXTRA_ARGS")
    if extra:
        cmd += extra.split("|")
else:
    raise SystemExit("harness invalido")

srv_log = os.path.join(ROOT, "logs", "server.err.log")
log_start = os.path.getsize(srv_log) if os.path.exists(srv_log) else 0

peak = {"rss_mb": 0}
def sample(pid, stop):
    ps = f"(Get-CimInstance Win32_Process | ?{{ $_.ProcessId -eq {pid} -or $_.ParentProcessId -eq {pid} }} | %{{ (Get-Process -Id $_.ProcessId -EA SilentlyContinue).WorkingSet64 }} | Measure -Sum).Sum"
    while not stop.is_set():
        try:
            v = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=20).stdout.strip()
            if v:
                peak["rss_mb"] = max(peak["rss_mb"], int(float(v)) // (1024 * 1024))
        except Exception:
            pass
        stop.wait(10)

t0 = time.perf_counter()
with open(log_out, "w", encoding="utf-8") as fh:
    p = subprocess.Popen(cmd, cwd=work, env=env, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
    stop = threading.Event(); th = threading.Thread(target=sample, args=(p.pid, stop), daemon=True); th.start()
    try:
        rc = p.wait(timeout=BUDGET); timed_out = False
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        rc = None; timed_out = True
    stop.set()
elapsed = time.perf_counter() - t0

# chamadas ao modelo e tokens a partir do log do servidor
calls, prompt_tok, cached_info, gen_tok, pp_time = 0, 0, [], 0, 0.0
with open(srv_log, encoding="utf-8", errors="replace") as fh:
    fh.seek(log_start); text = fh.read()
for m in re.finditer(r"prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens", text):
    calls += 1; prompt_tok += int(m.group(2)); pp_time += float(m.group(1)) / 1000
for m in re.finditer(r"\s eval time =\s*[\d.]+ ms /\s*(\d+) tokens", text):
    gen_tok += int(m.group(1))
cancel = len(re.findall(r"cancel task", text))

chk = subprocess.run([sys.executable, "-I", os.path.join(AUD, "agent-tests", "hidden", f"check_{test.replace('sub', '')}.py"), work], capture_output=True, text=True, timeout=120, cwd=work)
ok = f"{test.replace('sub', '').upper()}_OK" in chk.stdout
# contagem de chamadas de ferramenta no stream do harness
stream = open(log_out, encoding="utf-8", errors="replace").read()
tool_calls = len(re.findall(r'"type"\s*:\s*"tool_use"|"toolCallId"|"type":"tool_execution_start"', stream))
res = {"harness": harness, "test": test, "label": label, "ok": ok, "timed_out": timed_out, "exit_code": rc, "wall_s": round(elapsed, 1),
       "model_calls": calls, "prompt_tokens_processed": prompt_tok, "prompt_time_s": round(pp_time, 1), "gen_tokens": gen_tok,
       "cancelled": cancel, "tool_events": tool_calls, "harness_peak_rss_mb": peak["rss_mb"], "check": (chk.stdout + chk.stderr)[-600:],
       "workdir": work, "stream_log": log_out}
os.makedirs(os.path.join(AUD, "raw", "agents"), exist_ok=True)
with open(os.path.join(AUD, "raw", "agents", f"{harness}_{test}_{label}_{ts}.json"), "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=2)
print(json.dumps(res, ensure_ascii=False, indent=2))
