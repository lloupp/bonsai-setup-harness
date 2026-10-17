"""Reaplica os verificadores atuais as respostas salvas (sem nova inferencia). Uso: python rescore_cog.py arquivo.json"""
import json, sys, importlib.util, os
sys.argv_backup = sys.argv
path = sys.argv[1]
src = open(os.path.join(os.path.dirname(__file__), "bench_cog.py"), encoding="utf-8").read().split("results = []")[0]
ns = {"__file__": __file__}
sys.argv = ["x", "x", "padrao", "1"]
exec(src, ns)
checks = {n: c for n, _, c in ns["TASKS"]}
d = json.load(open(path, encoding="utf-8"))
for r in d["results"]:
    if r["task"] == "planejamento":
        try:
            ok = checks["planejamento"](r["resposta"])
        except Exception:
            ok = False
        r["ok"] = bool(ok); r["rescored"] = True
d["score"] = sum(r["ok"] for r in d["results"]) / len(d["results"])
agg = {}
for r in d["results"]:
    agg.setdefault(r["task"], []).append(r["ok"])
d["por_tarefa"] = {k: sum(v) / len(v) for k, v in agg.items()}
json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("score", round(d["score"] * 100, 1), d["por_tarefa"]["planejamento"])
