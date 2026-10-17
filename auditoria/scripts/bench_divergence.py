"""Reaproveitamento de cache quando o FINAL do prompt muda (padrao observado no Claude Code).
Modelos hibridos (DeltaNet) nao podem desfazer tokens do estado recorrente; sem checkpoint
anterior ao ponto de divergencia, o servidor reprocessa o prompt inteiro.
Uso: python bench_divergence.py <rotulo>"""
import random, sys, time
from common import chat, save

label = sys.argv[1]
rnd = random.Random(7)
words = "agente modelo arquivo teste funcao memoria contexto servidor token ferramenta projeto codigo".split()
base = "Instrucoes do agente.\n" + " ".join(rnd.choice(words) for _ in range(3300))
results = []
for i, tail in enumerate(["A " * 150, "B " * 150, "C " * 150]):
    msgs = [{"role": "system", "content": base}, {"role": "user", "content": f"Contexto variavel {i}: {tail}\nResponda OK."}]
    t0 = time.perf_counter()
    r = chat(msgs, profile="agente", max_tokens=4, extra={"cache_prompt": True})
    t = r.get("timings", {})
    results.append({"req": i, "prompt_total": r["usage"]["prompt_tokens"], "cache_n": t.get("cache_n"), "prompt_n": t.get("prompt_n"),
                    "wall_s": round(time.perf_counter() - t0, 1)})
    print(results[-1], flush=True)
print(save(f"divergence_{label}.json", {"label": label, "results": results}))
