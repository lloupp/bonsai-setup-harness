"""Benchmark de desempenho via API (servidor ja carregado).
Uso: python bench_perf.py <rotulo>   -> grava raw/perf_<rotulo>.json
Mede TTFT, velocidade de prompt/geracao, p50/p95, RAM e reaproveitamento de cache de prefixo
no padrao de um agente (mesmo prefixo + mensagens novas no final)."""
import sys, time, random
from common import chat_stream, server_proc_stats, percentile, save, get

label = sys.argv[1] if len(sys.argv) > 1 else "x"
random.seed(1)
WORDS = "agente modelo arquivo teste funcao memoria contexto servidor token ferramenta projeto codigo".split()


def filler(n_words, seed):
    rnd = random.Random(seed)
    return " ".join(rnd.choice(WORDS) for _ in range(n_words))


res = {"label": label, "props_n_ctx": get("/props")["default_generation_settings"]["n_ctx"],
       "mem_idle": server_proc_stats(), "runs": {}}

# aquecimento
chat_stream([{"role": "user", "content": "Diga OK."}], max_tokens=8)

def run(name, messages, max_tokens, reps=3):
    out = []
    for i in range(reps):
        r = chat_stream(messages(i), max_tokens=max_tokens, extra={"cache_prompt": True})
        t = r["timings"] or {}
        out.append({"ttft_s": r["ttft_s"], "total_s": r["total_s"], "prompt_n": t.get("prompt_n"),
                    "cache_n": t.get("cache_n"), "pp_tps": t.get("prompt_per_second"),
                    "tg_tps": t.get("predicted_per_second"), "gen_n": t.get("predicted_n")})
    res["runs"][name] = {"reps": out, "mem_after": server_proc_stats()}
    tt = [o["total_s"] for o in out]
    res["runs"][name]["p50_total_s"] = percentile(tt, 50)
    res["runs"][name]["p95_total_s"] = percentile(tt, 95)
    print(name, out, flush=True)

# 1) prompt curto, geracao 128 (prompts distintos: sem cache)
run("curto_gen128", lambda i: [{"role": "user", "content": f"[{i}{time.time()}] Escreva um paragrafo sobre arvores bonsai."}], 128)
# 2) prompt ~1500 tokens, distinto a cada rep (medir pp frio)
run("medio_1500_frio", lambda i: [{"role": "user", "content": f"rep {i} {time.time()}\n" + filler(1200, i) + "\nResuma em uma frase."}], 32)
# 3) padrao agente: prefixo fixo ~3000 tokens + pergunta nova a cada turno
prefix = "Voce e um agente de programacao.\n" + filler(2400, 99)
run("agente_prefixo_3000", lambda i: [{"role": "system", "content": prefix},
                                      {"role": "user", "content": f"Turno {i}: responda apenas o numero {i}."}], 16)
# 4) conversa crescente (historico acumulado), 4 turnos
hist = [{"role": "system", "content": prefix}]
grow = []
for i in range(4):
    hist.append({"role": "user", "content": f"Turno {i}: liste 3 palavras."})
    r = chat_stream(hist, max_tokens=24, extra={"cache_prompt": True})
    t = r["timings"] or {}
    grow.append({"turno": i, "prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"), "ttft_s": r["ttft_s"], "total_s": r["total_s"]})
    hist.append({"role": "assistant", "content": r["text"]})
res["runs"]["conversa_crescente"] = {"reps": grow, "mem_after": server_proc_stats()}
print("conversa", grow, flush=True)
# 5) estabilidade: 10 requisicoes curtas seguidas
lat = []
for i in range(10):
    r = chat_stream([{"role": "user", "content": f"{i}: quanto e {i}+{i}? Responda so o numero."}], max_tokens=8)
    lat.append(r["total_s"])
res["runs"]["estabilidade_10"] = {"lat_s": lat, "p50": percentile(lat, 50), "p95": percentile(lat, 95), "mem_after": server_proc_stats()}
print("estab", lat)
print(save(f"perf_{label}.json", res))
