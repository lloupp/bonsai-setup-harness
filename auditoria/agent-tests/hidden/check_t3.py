import sys, subprocess
d = sys.argv[1]; sys.path.insert(0, d)
from estoque.modelo import Estoque
from estoque.relatorio import itens_em_falta
e = Estoque(); e.adicionar("a", 2); e.adicionar("a", 2); e.adicionar("b", 1)
assert e.itens["a"] == 4 and e.total() == 5 and itens_em_falta(e, 3) == ["b"]
try:
    e.adicionar("c", 0); raise SystemExit("validacao removida")
except ValueError:
    pass
src = open(d + "/tests/test_estoque.py", encoding="utf-8").read()
assert src.count("def test_") >= 4, "testes removidos"
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."], capture_output=True, text=True, cwd=d)
assert r.returncode == 0, r.stderr[-500:]
print("T3_OK")
