"""Testa os falsos positivos identificados na primeira mini-bateria."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "auditoria" / "scripts"))
from bench_mini import check_code, check_format  # noqa: E402


class MiniValidationTests(unittest.TestCase):
    def test_formato_aceita_frutas_reais(self):
        self.assertTrue(check_format("- BANANA\n- LARANJA\n- ABACATE", {}))

    def test_formato_rejeita_palavras_invalidas_vistas_nos_logs(self):
        self.assertFalse(check_format("- BANANA\n- MAUVE\n- ABACATE", {}))
        self.assertFalse(check_format("- BANANA\n- LARANJA\n- MAÇON", {}))

    def test_funcao_sem_tratamento_de_negativos_rejeitada(self):
        original_2b = """```python
def soma_digitos(n):
    total = 0
    while n > 0:
        total += n % 10
        n //= 10
    total += n
    return total
```"""
        self.assertFalse(check_code(original_2b, {}))

    def test_funcao_com_abs_aceita_estaticamente(self):
        original_4b = """```python
def soma_digitos(n):
    n = abs(n)
    soma = 0
    while n > 0:
        soma += n % 10
        n //= 10
    return soma
```"""
        self.assertTrue(check_code(original_4b, {}))


if __name__ == "__main__":
    unittest.main()
