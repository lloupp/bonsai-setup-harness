# Gargalos — evidências e causas

Cada item foi medido. "Causa" só aparece quando um experimento isolou a variável; o restante está marcado como hipótese.

| # | Gargalo | Evidência (arquivo) | Causa comprovada? | Status |
|---|---|---|---|---|
| 1 | **Claude Code reprocessava o prompt inteiro a cada turno** | `server.err.log`: `f_keep` 0,885 → 0,803 → 0,776 e 5–6k tokens reprocessados por chamada; corpos capturados em `raw/claude-capture/req-0*.json` | **Sim.** O CLI envia, a cada turno, uma mensagem `role:system` nova (`<total_tokens>N tokens left`). O adaptador a movia para o system prompt **no início** do contexto. Em modelo híbrido (DeltaNet), o estado recorrente não pode ser rebobinado sem checkpoint, então o servidor recomputava tudo | CORRIGIDO (adaptador) — VALIDADO |
| 2 | **KV cache q4_0 deixa o prompt lento em contexto longo** | `raw/bench_depth_kv.md`: pp256 @ 4096 = 33,0 t/s (q4_0/q4_0) contra 57,2 t/s (f16/f16). Na API: 31,5 → 49,1 t/s com 8,4k tokens (`raw/compare_baseline_vs_otimizado.json`) | **Sim** (só o tipo de KV variou no llama-bench). A desquantização do V no flash attention da CPU domina | CORRIGIDO — VALIDADO |
| 3 | **Memória: cache de prompts em RAM sem limite prático** | Memória privada 3,6 GB → **11,9 GB** após ~20 requisições; RAM livre 1–2 GB (`raw/ctx_baseline.json`) | **Sim.** O padrão `--cache-ram 8192` guarda até 8 GB de estados de prompt. Com `--cache-ram 2048`: 5,3–5,4 GB estáveis | CORRIGIDO — VALIDADO |
| 4 | **Contexto de 262k superdimensionado** | 262k exige KV q4_0 para caber (f16 = 8,6 GB). Os agentes usam no máximo ~20k | Sim (cálculo: 8 camadas de atenção × 4 KV heads × 256 × 2 × 2 bytes = 32 KB/token) | Ajustado para 64k + f16 (2 GB) |
| 5 | **Prompt de sistema grande do Claude Code** | 19.822 tokens com as 22 ferramentas padrão (15–19 min a ~18 t/s), contra ~4.500 com 6 ferramentas (`raw/agents/claude_t1_*`) | Sim | Opção `-Enxuto` (padrão mantido a pedido do usuário) |
| 6 | **Velocidade de prompt baixa mesmo em contexto curto (~60–73 t/s)** | `raw/bench_threads.md`, `bench_ubatch*.md`, `bench_q4_0.md` | **Parcial.** Q4_0 (kernel de matmul diferente) não acelerou, e ubatch maior *piora* (512: 37 t/s; 128: 70 t/s). Logo, o limite não está no matmul dos pesos. Hipótese: operações recorrentes DeltaNet e transformadas Hadamard na CPU. Não verificável sem profiling de kernel | Limite do runtime/CPU |
| 7 | **Threads** | 4: 46 / 6: 57 / 8: 59 / 12: 53 / 14: 51 t/s (prompt); geração com pico em 6 (20,1 t/s) | Sim: com mais de 8 threads entram os E-cores e a sincronização piora | Mantido `-t 6 -tb 8` (já era o ótimo) |
| 8 | **iGPU** | Vulkan UHD 770: prompt 31 t/s, geração 8,6 t/s (CPU: 73 / 20) | Sim (medido) | GPU integrada descartada |
| 9 | **Loops repetitivos de ferramenta** | `raw/tools_baseline_padrao.json` t2: 8 iterações, 2 chamadas duplicadas, sem concluir | Correlação com amostragem: com o perfil "agente" (temp 0,2, presence 0), 10/10 (`raw/tools_otimizado_agente.json`). Amostra pequena | Mitigado |
| 10 | **Presence penalty 1,5 em código** | Cognitivo: 68,8% (padrão) contra 75,0% (agente), mesmo servidor | Tendência (32 amostras cada). Mecanismo plausível: a penalidade desencoraja repetir identificadores, o que é essencial em código | Perfil "agente" aplicado aos harnesses |
| 11 | **Pi retorna código 0 mesmo com erro de conexão** | `pi_t1_baseline` (descartado): `stopReason:error`, exit 0 | Sim: comportamento do harness | Documentado; o verificador oculto detecta |
| 12 | Gateway não estava ativo | Primeira execução do Pi falhou com "Connection error" | Sim: infraestrutura, não modelo | Launchers o iniciam; manual explica |
| 13 | Temperatura/throttling | Sensores inacessíveis sem administrador | — | NÃO TESTADO |
| 14 | Overhead de JSON/serialização e do gateway | Requisições curtas: p50 0,55 s, p95 0,59 s em 10 seguidas | Desprezível frente ao processamento de prompt | Sem ação |
| 15 | Concorrência | `-np 1`: agentes simultâneos entram em fila | Por desenho (RAM/CPU limitadas) | Recomendação: um agente por vez |

## Diferenciação de responsabilidades

- **Modelo:** erros aritméticos (37×43 → 1291), contas de datas, nomes de variáveis inconsistentes (`additional` × `adicional`) e loops em tarefas sequenciais.
- **Servidor:** KV q4_0 lento, cache de RAM excessivo, ausência de rollback de estado recorrente (próprio da arquitetura híbrida).
- **Framework/adaptador:** reordenação de mensagens de sistema pelo adaptador (corrigida), prompt grande do Claude Code e exit code do Pi.
- **Tool calling em si:** nenhuma chamada malformada, nenhuma chamada "vazada" como texto e nenhuma ferramenta inexistente em todas as execuções via API.
