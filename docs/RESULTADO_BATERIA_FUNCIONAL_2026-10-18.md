# Testes reais Bonsai 2B vs 4B — mini-bateria CPU (18/10/2026)

## Fonte de evidencia

- [GitHub Actions #39097145336](https://github.com/lloupp/bonsai-setup-harness/actions/runs/39097145336), conclusao: **success**.
- Script: `auditoria/scripts/bench_mini.py`, uma repeticao por caso e por modelo.
- Runner: GitHub-hosted `ubuntu-latest`, CPU; contexto de 4096 tokens, KV f16,
  `--cache-ram 128`, sem visao; perfil de amostragem `agente`.
- Download com SHA256 confirmado: runtime Ubuntu x64, GGUF 2B/4B e mmproj 2B/4B.
- Nenhum codigo gerado pelo LLM foi executado; a funcao Python foi **somente
  analisada por AST**. O benchmark pediu tool calls, mas **nao executou** ferramentas.
- Artefato: `bonsai-linux-smoke`, com `mini_cpu_2b.json`,
  `mini_cpu_4b.json` e logs, com retencao limitada.

## Resultados da verificacao programada

| Caso | 2B | 4B | Duracao 2B | Duracao 4B |
|---|---|---|---:|---:|
| Aritmetica 37 x 43 | FALHOU: 1391 | OK: 1591 | 0,970 s | 2,250 s |
| Logica de ordenacao | OK: Caio | OK: Caio | 0,871 s | 1,940 s |
| JSON estrito | OK | OK | 3,066 s | 6,406 s |
| Tres linhas maiusculas | OK no **formato** | OK no **formato** | 1,625 s | 3,534 s |
| Sintaxe Python `soma_digitos` | OK no **AST** | OK no **AST** | 4,102 s | 8,890 s |
| Tool call `multiply(7,8)` | OK: 1 chamada | OK: 1 chamada | 6,522 s | 15,276 s |
| Recuperacao contexto (1754 tokens) | OK: OPALA-7362 | OK: OPALA-7362 | 24,155 s | 60,460 s |
| **Total das verificacoes originais** | **6/7** | **7/7** | — | — |

## Falhas adicionais detectadas na revisao humana

A pontuacao original e **otimista** porque dois validadores so verificavam
formato/sintaxe, nao comportamento:

- **2B, codigo:** a funcao gerada faz `while n > 0` e nao converte `n`
  para valor absoluto. Para `soma_digitos(-907)`, devolve um valor incorreto.
  **Falha funcional** apesar de passar no verificador AST.
- **4B, codigo:** usa `n = abs(n)` antes do loop; trata corretamente o
  caso negativo observado **por revisao manual**, mas o codigo nao foi executado.
- **2B, frutas:** gerou `BANANA`, `MAUVE`, `ABACATE`. `MAUVE` nao e
  uma fruta no sentido esperado.
- **4B, frutas:** gerou `BANANA`, `LARANJA`, `MAÇON`. `MAÇON` nao e fruta.
  Ambos passaram apenas no validador de **3 linhas maiusculas**.

Assim, a pontuacao automatica de 6/7 e 7/7 **nao significa** que 6 e 7
solicitacoes foram inteiramente atendidas. A revisao humana aponta pelo menos
tres falhas adicionais: codigo e lista de frutas no 2B; lista de frutas no 4B.
Se cada caso exigir todos os requisitos do prompt, as respostas observadas
atendem **4/7 (2B)** e **6/7 (4B)**, sob a revisao acima.

## Interpretacao

- Ambos os modelos realizam inferencia real em CPU e chamam ferramenta no
  formato esperado (sem executar a ferramenta).
- O 4B acertou a multiplicacao que o 2B errou e produziu uma funcao Python
  mais plausivelmente correta. Em compensacao, suas latencias foram maiores
  neste runner CPU.
- A recuperacao de `OPALA-7362` em 1754 tokens demonstra uma observacao de
  acesso ao contexto, **nao** capacidade geral em contextos longos.
- Sao 7 casos com 1 repeticao; os tempos dependem do runner, warm-up, carga e
  comprimento da resposta. Nao inferir robustez, taxa real de tool calling
  ou desempenho dos tres harnesses.

## O que nao foi possivel testar

Pi Agent, Hermes, Claude Code, agent loops, subagentes e o Linux Mint
instalado no PC do usuario dependem das instalacoes/configuracoes locais,
nao publicadas neste repositorio. Nenhum desses recursos foi validado neste
teste. Para aprofundar, consultar `docs/TESTES_PENDENTES.md`.
