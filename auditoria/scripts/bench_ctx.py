"""Contexto progressivo: recuperacao de fatos em posicoes 10/50/90%, instrucao antiga, tempo e RAM.
Uso: python bench_ctx.py <rotulo> <tamanhos separados por virgula, em palavras aprox.>"""
import random, sys, time
from common import chat, server_proc_stats, save

label = sys.argv[1]
sizes = [int(x) for x in sys.argv[2].split(",")]
TOPICS = ["O relatorio trimestral mostrou estabilidade nas vendas.", "A equipe revisou o processo de implantacao.",
          "O servidor de arquivos foi migrado para outro rack.", "Os testes de integracao passaram na segunda tentativa.",
          "A reuniao de planejamento foi adiada para quinta.", "O fornecedor enviou a nova tabela de precos."]
results = []
for n in sizes:
    rnd = random.Random(n)
    for pos in (0.1, 0.5, 0.9):
        code = f"{rnd.choice(['JADE','RUBI','ONIX','OPALA'])}-{rnd.randint(1000, 9999)}"
        sents = [rnd.choice(TOPICS) for _ in range(n // 7)]
        sents.insert(int(len(sents) * pos), f"Nota importante: a senha do cofre azul e {code}.")
        doc = " ".join(sents)
        msgs = [{"role": "system", "content": "Regra permanente: sempre termine a resposta com a palavra BONSAI em maiusculas."},
                {"role": "user", "content": "Documento:\n" + doc + "\n\nQual e a senha do cofre azul? Responda curto."}]
        t0 = time.perf_counter()
        r = chat(msgs, profile="agente", max_tokens=40, extra={"cache_prompt": False})
        txt = r["choices"][0]["message"]["content"] or ""
        t = r.get("timings", {})
        res = {"palavras": n, "posicao": pos, "prompt_tokens": r["usage"]["prompt_tokens"], "acertou": code in txt,
               "seguiu_instrucao_antiga": txt.strip().rstrip(".!").endswith("BONSAI"), "wall_s": round(time.perf_counter() - t0, 1),
               "pp_tps": t.get("prompt_per_second"), "tg_tps": t.get("predicted_per_second"), "mem": server_proc_stats(), "resposta": txt[:120]}
        results.append(res)
        print(res, flush=True)
print(save(f"ctx_{label}.json", {"label": label, "results": results}))
