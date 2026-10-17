# Comparação dos harnesses (mesmo Bonsai 2 4B, mesma máquina, mesmas tarefas)

Executor: `scripts/run_agent_test.py`. Cada tarefa roda numa pasta nova e é aprovada por um **verificador oculto** que o agente não vê (`agent-tests/hidden/`). Chamadas e tokens vêm do log do servidor.

## T1 — função Python + testes unitários

| Harness | Config | Resultado | Tempo | Chamadas ao modelo | Tokens de prompt processados | Tokens gerados |
|---|---|---|---|---|---|---|
| Pi 1.3.0 | baseline | VALIDADO | 89 s | 4 | 2.070 | 696 |
| Pi 1.3.0 | otimizado | VALIDADO | **85 s** | 4 | 2.499 | 686 |
| Hermes 0.22.2 | baseline | VALIDADO | 209 s | 4 | 5.362 | 502 |
| Hermes 0.22.2 | otimizado | VALIDADO | **155 s** (−26%) | 3 | 5.385 | 557 |
| Claude Code 2.1.302 (6 ferramentas) | baseline | VALIDADO | 701 s | 4 | 22.720 | 832 |
| Claude Code | só adaptador corrigido | VALIDADO | 733 s (trajetória mais longa: 10 chamadas) | 10 | 10.361 | 3.170 |
| Claude Code | otimizado | VALIDADO | **235 s** (−66%) | 5 | 6.735 | 1.298 |

## T2 — pacote multi-arquivo com CLI, tratamento de erros e testes

| Harness | Resultado | Tempo | Chamadas | Observação |
|---|---|---|---|---|
| Pi | VALIDADO | 551 s | 26 | Precisou de vários ciclos de correção, mas concluiu e o verificador passou |
| Hermes | INTERROMPIDO | — | — | Parado a pedido do usuário |
| Claude Code | NÃO TESTADO | — | — | — |

## T3 (projeto defeituoso), T4 (agent loop) e T5 (subagentes)

NÃO TESTADOS nesta sessão (interrompidos). Os fixtures e os verificadores estão prontos; ver `PROGRESSO.md`.

## Características medidas

| | Pi | Hermes | Claude Code |
|---|---|---|---|
| Prompt inicial (sistema + ferramentas) | **~1,9k tokens** | ~4–5k tokens | ~4,5k (6 ferramentas) / **19,8k** (22 padrão) |
| Protocolo | OpenAI Chat Completions | OpenAI Chat Completions | Anthropic Messages, via adaptador |
| Reaproveitamento de cache entre turnos | Excelente (cresce só no fim) | Bom (pequenas mudanças, checkpoint resolve) | Ruim antes da correção do adaptador; bom depois |
| RAM do processo do harness | ~90–103 MB | ~40 MB (*só o launcher Python; subprocessos não somados de forma confiável*) | ~190–207 MB |
| Subagentes | Só via extensão de exemplo | Nativo (`delegate_task`) | Nativo (`Task`) |
| Particularidades | Retorna exit 0 mesmo com erro de conexão | `--yolo` necessário em modo não interativo | Envia `role:system` dinâmico a cada turno; exige adaptador |

## Conclusão (só o que os dados sustentam)

- **Tarefas simples (T1):** os três concluíram. **Pi é o mais rápido** em ambas as configurações, por ter o menor prompt de sistema e o melhor reaproveitamento de cache.
- **Tarefa intermediária (T2):** só o Pi foi medido, e concluiu. Sem dados para comparar os outros.
- **Claude Code** foi o que mais ganhou com as otimizações (−66%) e continua o mais pesado. Com as 22 ferramentas padrão, a primeira resposta leva ~15 min nesta CPU.
- **Não há vencedor geral declarado:** T2/T3/T5 estão incompletos.
