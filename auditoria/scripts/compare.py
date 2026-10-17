"""Resume e compara resultados brutos (raw/*.json). Uso: python compare.py <rotulo_antes> <rotulo_depois>"""
import json, os, statistics as st, sys
RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw")
a, b = sys.argv[1], sys.argv[2]
load = lambda n: json.load(open(os.path.join(RAW, n), encoding="utf-8")) if os.path.exists(os.path.join(RAW, n)) else None


def perf(label):
    d = load(f"perf_{label}.json")
    if not d:
        return {}
    r = d["runs"]; m = lambda k, f: st.mean(x[f] for x in r[k]["reps"] if x[f] is not None)
    return {"tg_tps_curto": m("curto_gen128", "tg_tps"), "pp_tps_1500": m("medio_1500_frio", "pp_tps"),
            "ttft_1500_s": m("medio_1500_frio", "ttft_s"), "ttft_prefixo_frio_s": r["agente_prefixo_3000"]["reps"][0]["ttft_s"],
            "ttft_prefixo_cache_s": st.mean(x["ttft_s"] for x in r["agente_prefixo_3000"]["reps"][1:]),
            "lat_p50_s": r["estabilidade_10"]["p50"], "lat_p95_s": r["estabilidade_10"]["p95"],
            "ram_priv_mb_repouso": d["mem_idle"]["priv_mb"], "ram_priv_mb_final": r["estabilidade_10"]["mem_after"]["priv_mb"]}


def ctx(label):
    d = load(f"ctx_{label}.json")
    if not d:
        return {}
    out = {}
    for r in d["results"]:
        k = r["palavras"]
        out.setdefault(f"ctx_{k}_tokens", r["prompt_tokens"])
        out.setdefault(f"ctx_{k}_pp_tps", []).append(r["pp_tps"])
        out.setdefault(f"ctx_{k}_acerto", []).append(r["acertou"])
        out[f"ctx_{k}_ram_priv_mb"] = r["mem"]["priv_mb"]
    for k in list(out):
        if isinstance(out[k], list):
            out[k] = st.mean(out[k]) if "pp" in k else sum(out[k]) / len(out[k])
    return out


res = {}
for lab in (a, b):
    res[lab] = {**perf(lab), **ctx(lab)}
rows = []
for k in res[a]:
    va, vb = res[a].get(k), res[b].get(k)
    if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va:
        rows.append((k, va, vb, (vb - va) / va * 100))
for k, va, vb, p in rows:
    print(f"{k:28s} {va:10.2f} {vb:10.2f} {p:+7.1f}%")
json.dump(res, open(os.path.join(RAW, f"compare_{a}_vs_{b}.json"), "w", encoding="utf-8"), indent=2)
