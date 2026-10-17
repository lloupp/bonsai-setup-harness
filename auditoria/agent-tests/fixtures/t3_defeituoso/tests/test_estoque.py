import unittest
from estoque.modelo import Estoque
from estoque.relatorio import itens_em_falta


class TestEstoque(unittest.TestCase):
    def test_adicionar_acumula(self):
        e = Estoque()
        e.adicionar("caneta", 5)
        e.adicionar("caneta", 3)
        self.assertEqual(e.itens["caneta"], 8)

    def test_total_soma_quantidades(self):
        e = Estoque()
        e.adicionar("caneta", 5)
        e.adicionar("lapis", 2)
        self.assertEqual(e.total(), 7)

    def test_remover(self):
        e = Estoque()
        e.adicionar("caneta", 5)
        e.remover("caneta", 2)
        self.assertEqual(e.itens["caneta"], 3)
        with self.assertRaises(ValueError):
            e.remover("caneta", 10)

    def test_itens_em_falta(self):
        e = Estoque()
        e.adicionar("caneta", 1)
        e.adicionar("lapis", 10)
        self.assertEqual(itens_em_falta(e, 3), ["caneta"])


if __name__ == "__main__":
    unittest.main()
