"""Tool calling real (ferramentas executadas de fato em sandbox temporario).
Uso: python bench_tools.py <rotulo> <perfil> <repeticoes> [max_iter]
Classifica falhas em: modelo (args/nome/abandono), servidor (tool call vazado como texto, HTTP) e sucesso."""
import json, os, re, shutil, subprocess, sys, tempfile, time
from common import chat, save

label, profile, reps = sys.argv[1], sys.argv[2], int(sys.argv[3])
MAX_ITER = int(sys.argv[4]) if len(sys.argv) > 4 else 8

TOOLS = [
    {"type": "function", "function": {"name": "list_dir", "description": "Lista os arquivos da pasta de trabalho.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "read_file", "description": "Le um arquivo texto da pasta de trabalho.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Cria ou sobrescreve um arquivo texto.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "run_python", "description": "Executa um arquivo .py da pasta de trabalho e devolve stdout/stderr.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]
SYSTEM = ("Voce e um agente que executa tarefas usando ferramentas reais. Use as ferramentas; nunca invente o conteudo de arquivos. "
          "Quando terminar, responda com uma frase curta comecando com 'FEITO:'.")


def exec_tool(d, name, args):
    safe = lambda p: os.path.join(d, os.path.basename(str(p)))
    if name == "list_dir":
        return "\n".join(sorted(os.listdir(d)))
    if name == "read_file":
        p = safe(args["path"])
        if not os.path.exists(p):
            return f"ERRO: arquivo '{args['path']}' nao existe. Use list_dir para ver os arquivos."
        return open(p, encoding="utf-8").read()
    if name == "write_file":
        open(safe(args["path"]), "w", encoding="utf-8").write(args["content"])
        return "ok, gravado"
    if name == "run_python":
        r = subprocess.run([sys.executable, "-I", safe(args["path"])], capture_output=True, text=True, timeout=20, cwd=d)
        return (r.stdout + r.stderr)[-1500:] or "(sem saida)"
    return f"ERRO: ferramenta desconhecida {name}"


def setup_files(d, files):
    for k, v in files.items():
        open(os.path.join(d, k), "w", encoding="utf-8").write(v)


def read(d, f):
    p = os.path.join(d, f)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def fizz_ok(d):
    if read(d, "fizz.py") is None:
        return False
    out = subprocess.run([sys.executable, "-I", os.path.join(d, "fizz.py")], capture_output=True, text=True, timeout=20, cwd=d).stdout.split()
    exp = ["FizzBuzz" if i % 15 == 0 else "Fizz" if i % 3 == 0 else "Buzz" if i % 5 == 0 else str(i) for i in range(1, 16)]
    return out == exp

TASKS = [
    ("t1_leitura_simples", {"segredo.txt": "O codigo e 48213."}, "Leia segredo.txt e grave em resposta.txt somente o numero do codigo.",
     lambda d: (read(d, "resposta.txt") or "").strip() == "48213"),
    ("t2_sequencial", {"inicio.txt": "Abra o arquivo etapa2.txt", "etapa2.txt": "palavra: girassol"},
     "Leia inicio.txt e siga a instrucao que ele contem. Depois grave em final.txt a palavra encontrada, em MAIUSCULAS.",
     lambda d: (read(d, "final.txt") or "").strip() == "GIRASSOL"),
    ("t3_multiplas", {"a.txt": "17", "b.txt": "25", "c.txt": "58"}, "Leia a.txt, b.txt e c.txt, some os tres numeros e grave o total em soma.txt.",
     lambda d: (read(d, "soma.txt") or "").strip() == "100"),
    ("t4_recuperacao_erro", {"config.yaml": "porta: 7311\n"}, "Leia o arquivo config.json e grave em porta.txt o valor da porta.",
     lambda d: (read(d, "porta.txt") or "").strip() == "7311"),
    ("t5_codigo_executado", {}, "Crie fizz.py que imprime FizzBuzz de 1 a 15 (um item por linha), execute-o com run_python e confirme que a saida esta correta.",
     fizz_ok),
]

results = []
for name, files, task, check in TASKS:
    for rep in range(reps):
        d = tempfile.mkdtemp(prefix="bonsai_tool_")
        setup_files(d, files)
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
        stats = {"iter": 0, "calls": 0, "bad_args": 0, "unknown_tool": 0, "leaked_text_call": 0, "dup_calls": 0, "http_err": None, "tokens_prompt": 0}
        seen = set(); t0 = time.perf_counter(); finished = False
        for it in range(MAX_ITER):
            stats["iter"] = it + 1
            try:
                r = chat(msgs, profile=profile, max_tokens=800, tools=TOOLS, seed=2000 + rep, timeout=900)
            except Exception as e:
                stats["http_err"] = str(e)[:200]; break
            stats["tokens_prompt"] += r["usage"]["prompt_tokens"]
            m = r["choices"][0]["message"]
            calls = m.get("tool_calls") or []
            content = m.get("content") or ""
            if not calls:
                if re.search(r"<tool_call>|\"name\"\s*:\s*\"(read_file|write_file|list_dir|run_python)\"", content):
                    stats["leaked_text_call"] += 1
                finished = True
                stats["final"] = content[-200:]
                break
            msgs.append({"role": "assistant", "content": content, "tool_calls": calls})
            for c in calls:
                stats["calls"] += 1
                fn = c["function"]["name"]
                key = fn + c["function"].get("arguments", "")
                if key in seen:
                    stats["dup_calls"] += 1
                seen.add(key)
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                    out = exec_tool(d, fn, args)
                    if out.startswith("ERRO: ferramenta"):
                        stats["unknown_tool"] += 1
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    stats["bad_args"] += 1
                    out = f"ERRO: argumentos invalidos ({e})"
                msgs.append({"role": "tool", "tool_call_id": c.get("id", ""), "content": out})
        ok = False
        try:
            ok = bool(check(d))
        except Exception:
            pass
        stats.update({"task": name, "rep": rep, "ok": ok, "finished": finished, "wall_s": round(time.perf_counter() - t0, 1)})
        results.append(stats)
        print(name, rep, "OK" if ok else "FALHOU", {k: stats[k] for k in ("iter", "calls", "bad_args", "dup_calls", "leaked_text_call", "wall_s")}, flush=True)
        shutil.rmtree(d, ignore_errors=True)

score = sum(r["ok"] for r in results) / len(results)
print("SCORE", round(score * 100, 1))
print(save(f"tools_{label}_{profile}.json", {"label": label, "profile": profile, "max_iter": MAX_ITER, "score": score, "results": results}))
