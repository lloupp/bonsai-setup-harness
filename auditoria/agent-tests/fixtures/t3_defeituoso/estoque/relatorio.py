def itens_em_falta(estoque, minimo):
    return sorted(nome for nome, qtd in estoque.itens.items() if qtd > minimo)
