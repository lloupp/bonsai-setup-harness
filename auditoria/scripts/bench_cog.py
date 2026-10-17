"""Bateria cognitiva com verificacao automatica (nada avaliado 'pela aparencia').
Uso: python bench_cog.py <rotulo> <perfil> <repeticoes>"""
import json, os, re, subprocess, sys, tempfile
from common import chat, save

label, profile, reps = sys.argv[1], sys.argv[2], int(sys.argv[3])
SYS = "Voce e um assistente preciso. Siga o formato pedido exatamente."


def final(text):
    m = re.findall(r"RESPOSTA:\s*(.+)", text)
    return m[-1].strip().strip("*. ").lower() if m else ""


def code(text, lang):
    blocks = re.findall(r"```(?:" + lang + r")?\s*\n(.*?)```", text, re.S)
    return max(blocks, key=len) if blocks else text


def run_py(src, tests):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.py")
        open(p, "w", encoding="utf-8").write(src + "\n\n" + tests + "\nprint('OK_ALL')\n")
        r = subprocess.run([sys.executable, "-I", p], capture_output=True, text=True, timeout=20, cwd=d)
        return "OK_ALL" in r.stdout, (r.stderr or r.stdout)[-300:]


def run_js(src, tests):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.js")
        open(p, "w", encoding="utf-8").write(src + "\n\n" + tests + "\nconsole.log('OK_ALL');\n")
        r = subprocess.run(["node", p], capture_output=True, text=True, timeout=20, cwd=d)
        return "OK_ALL" in r.stdout, (r.stderr or r.stdout)[-300:]


BUGGY_BS = '''def busca_binaria(lista, alvo):
    lo, hi = 0, len(lista)
    while lo < hi:
        meio = (lo + hi) // 2
        if lista[meio] == alvo:
            return meio
        elif lista[meio] < alvo:
            lo = meio
        else:
            hi = meio - 1
    return -1'''

REPETITIVE = '''def total_a(p):
    return round(p * 1.10, 2)
def total_b(p):
    return round(p * 1.10 + 5, 2)
def total_c(p):
    return round(p * 1.10 + 12, 2)'''

PROJECT = '''=== app/config.py ===
TAXA = 0.15
=== app/calc.py ===
from app.config import TAXA
def preco_final(preco):
    return preco * (1 + TAXA)
=== app/report.py ===
from app.calc import preco_final
def relatorio(itens):
    return sum(preco_final(i) for i in itens) / len(itens) * 0 + sum(itens)
=== tests/test_report.py ===
# Falha: relatorio([10, 20]) deveria ser 34.5, retorna 30
'''

INI = """[servidor]
porta = 8080
host = 127.0.0.1
[banco]
host = db.local
porta = 5433
usuario = app
[cache]
porta = 6379
"""

TASKS = [
    ("logica_ordem", "Ana e mais alta que Bia. Bia e mais alta que Caio. Davi e mais alto que Ana. Quem e o mais baixo? Termine com 'RESPOSTA: <nome>'.",
     lambda t: final(t).startswith("caio")),
    ("logica_cavaleiros", "Numa ilha, cavaleiros sempre dizem a verdade e patifes sempre mentem. A diz: 'B e patife'. B diz: 'A e eu somos do mesmo tipo'. O que e A? Termine com 'RESPOSTA: cavaleiro' ou 'RESPOSTA: patife'.",
     lambda t: final(t).startswith("cavaleiro")),
    ("mat_mult", "Quanto e 37 * 43? Termine com 'RESPOSTA: <numero>'.", lambda t: final(t).replace(".", "") == "1591"),
    ("mat_troco", "Uma caneta custa R$ 2,50. Compro 14 canetas e pago com R$ 50,00. Quanto recebo de troco? Termine com 'RESPOSTA: <valor numerico>'.",
     lambda t: re.sub(r"[^0-9,\.]", "", final(t)).replace(",", ".").rstrip("0").rstrip(".") in ("15",)),
    ("mat_primos", "Qual a soma de todos os numeros primos menores que 30? Termine com 'RESPOSTA: <numero>'.", lambda t: final(t) == "129"),
    ("multietapa_datas", "Hoje e quarta-feira. Que dia da semana sera daqui a 10 dias? E daqui a 100 dias? Termine com 'RESPOSTA: <dia1>, <dia2>'.",
     lambda t: "sabado" in final(t).replace("á", "a") and "sexta" in final(t)),
    ("instrucoes_formato", "Liste exatamente 3 frutas. Regras: exatamente 3 linhas, cada linha comeca com '- ', tudo em MAIUSCULAS, nada mais na resposta.",
     lambda t: (lambda ls: len(ls) == 3 and all(l.startswith("- ") and l == l.upper() for l in ls))([l for l in t.strip().splitlines() if l.strip()])),
    ("json_estrito", "Responda SOMENTE com um objeto JSON (sem markdown) com as chaves: nome (string), idade (inteiro 30), tags (lista com exatamente 2 strings).",
     lambda t: (lambda o: isinstance(o, dict) and o.get("idade") == 30 and isinstance(o.get("tags"), list) and len(o["tags"]) == 2 and isinstance(o.get("nome"), str))(json.loads(t.strip().strip("`").removeprefix("json").strip()))),
    ("py_palindromo", "Escreva em Python a funcao eh_palindromo(s) que ignora maiusculas, espacos e pontuacao. Responda so com o codigo em um bloco ```python.",
     lambda t: run_py(code(t, "python"), "assert eh_palindromo('Socorram-me, subi no onibus em Marrocos')\nassert not eh_palindromo('bonsai')\nassert eh_palindromo('')\nassert eh_palindromo('A man, a plan, a canal: Panama')")),
    ("py_intervalos", "Escreva em Python mesclar(intervalos) que recebe lista de pares [ini, fim] (possivelmente desordenados) e devolve a lista mesclada e ordenada de intervalos sobrepostos (intervalos que se tocam, como [1,2] e [2,3], tambem se mesclam). Responda so com o codigo em um bloco ```python.",
     lambda t: run_py(code(t, "python"), "assert [list(x) for x in mesclar([[8,10],[1,3],[2,6],[15,18]])]==[[1,6],[8,10],[15,18]]\nassert [list(x) for x in mesclar([[1,2],[2,3]])]==[[1,3]]\nassert list(mesclar([]))==[]")),
    ("js_snake", "Escreva em JavaScript a funcao camelToSnake(str) que converte 'meuNomeCompleto' em 'meu_nome_completo' e 'HTTPServerError' em 'http_server_error'. Responda so com o codigo em um bloco ```javascript.",
     lambda t: run_js(code(t, "javascript|js"), "const a=require('assert');a.strictEqual(camelToSnake('meuNomeCompleto'),'meu_nome_completo');a.strictEqual(camelToSnake('simples'),'simples');a.strictEqual(camelToSnake('HTTPServerError'),'http_server_error');")),
    ("debug_busca", "Este codigo tem bugs (pode entrar em loop infinito ou errar). Corrija e devolva a funcao completa em um bloco ```python.\n```python\n" + BUGGY_BS + "\n```",
     lambda t: run_py(code(t, "python"), "L=[1,3,5,7,9,11]\nfor i,x in enumerate(L): assert busca_binaria(L,x)==i\nassert busca_binaria(L,4)==-1\nassert busca_binaria([],1)==-1\nassert busca_binaria([2],2)==0")),
    ("refatoracao", "Refatore o codigo abaixo removendo a repeticao: crie uma funcao preco_com_taxa(p, adicional=0) e reescreva total_a, total_b e total_c usando-a, mantendo exatamente o comportamento. Devolva todo o codigo em um bloco ```python.\n```python\n" + REPETITIVE + "\n```",
     lambda t: run_py(code(t, "python"), "assert total_a(100)==110.0 and total_b(100)==115.0 and total_c(10)==23.0\nassert preco_com_taxa(100)==110.0 and preco_com_taxa(100,5)==115.0")),
    ("leitura_arquivo", "Arquivo config.ini:\n" + INI + "\nQual a porta da secao [banco]? Termine com 'RESPOSTA: <numero>'.", lambda t: final(t) == "5433"),
    ("analise_projeto", "Projeto:\n" + PROJECT + "\nQual arquivo contem o bug que faz o teste falhar? Termine com 'RESPOSTA: <caminho do arquivo>'.",
     lambda t: "report.py" in final(t)),
    ("planejamento", "Ordene estas etapas para publicar uma biblioteca Python, respeitando dependencias: [rodar testes, criar ambiente virtual, publicar no PyPI, instalar dependencias, gerar pacote]. Termine com 'RESPOSTA: ' seguido das etapas separadas por ' > '.",
     lambda t: (lambda s: all(s.find(a) < s.find(b) and s.find(a) >= 0 for a, b in [("ambiente", "instalar"), ("instalar", "testes"), ("testes", "publicar"), ("gerar", "publicar")]))(final(t))),
]

results = []
for name, prompt, check in TASKS:
    for rep in range(reps):
        r = chat([{"role": "system", "content": SYS}, {"role": "user", "content": prompt}], profile=profile, max_tokens=700, seed=1000 + rep)
        text = r["choices"][0]["message"].get("content") or ""
        try:
            ok = check(text)
            detail = ""
            if isinstance(ok, tuple):
                ok, detail = ok
        except Exception as e:
            ok, detail = False, f"{type(e).__name__}: {e}"[:200]
        results.append({"task": name, "rep": rep, "ok": bool(ok), "detail": detail, "gen_tokens": r["usage"]["completion_tokens"],
                        "wall_s": round(r["_wall_s"], 2), "resposta": text[-400:]})
        print(name, rep, "OK" if ok else "FALHOU", detail[:80], flush=True)

score = sum(r["ok"] for r in results) / len(results)
summary = {}
for r in results:
    summary.setdefault(r["task"], []).append(r["ok"])
out = {"label": label, "profile": profile, "reps": reps, "score": score,
       "por_tarefa": {k: sum(v) / len(v) for k, v in summary.items()}, "results": results}
print("SCORE", round(score * 100, 1))
print(save(f"cog_{label}_{profile}.json", out))
