class Estoque:
    def __init__(self):
        self.itens = {}

    def adicionar(self, nome, qtd):
        if qtd <= 0:
            raise ValueError("quantidade deve ser positiva")
        self.itens[nome] = qtd

    def remover(self, nome, qtd):
        atual = self.itens.get(nome, 0)
        if qtd > atual:
            raise ValueError("estoque insuficiente")
        self.itens[nome] = atual - qtd

    def total(self):
        return len(self.itens)
