# Relatório final — Bonsai 4B local com Pi, Hermes e Claude Code

**Máquina:** Intel Core i5-14500T (14 núcleos, 35 W), 16 GB de RAM, sem placa de vídeo dedicada · **Data:** 17/10/2026
**Modelo:** Ternary Bonsai 2 4B (PrismML), pesos ternários PQ2_0 de 1,1 GB · **Runtime:** fork PrismML do llama.cpp b10777 (CPU)

Legenda: **VALIDADO** = executado com evidência · **PARCIAL** = incompleto · **FALHOU** = executado sem sucesso · **NÃO TESTADO** = não executado.

---

## 1. Resumo geral

- O Bonsai 4B **funciona como agente de programação real** nos três harnesses: criou código, rodou testes e passou num verificador independente (T1 VALIDADO nos três).
- O maior problema era de **integração, não do modelo**. O adaptador do Claude Code mudava o início do prompt a cada turno e obrigava o servidor a reprocessar tudo. Corrigido, o Claude Code ficou **66% mais rápido** na mesma tarefa (701 s → 235 s).
- A configuração do servidor tinha dois gargalos medidos:
  - o **cache de atenção em 4 bits** deixava a leitura de textos longos até **56% mais lenta**;
  - o **cache de prompts** chegava a ocupar **12 GB de RAM**.
- Corrigindo os dois, o servidor ficou **mais rápido com metade da memória** e sem perda de precisão.
- Ajustar a "criatividade" das respostas para o modo agente aumentou a **taxa de acerto de 56% para 75%** nos testes verificáveis e de **90% para 100%** no uso de ferramentas.
- Limite real: é um modelo pequeno. **Erra contas e lógica com frequência** e é lento para ler textos longos nesta CPU.

## 2. Desempenho do Bonsai 4B

| Métrica (via API, configuração final) | Valor | Status |
|---|---|---|
| Carregamento do modelo | 6–9 s | VALIDADO |
| Velocidade de escrita (geração) | 17–20 tokens/s | VALIDADO |
| Velocidade de leitura (prompt) curto / 3k / 8k tokens | 63 / 61 / 49 tokens/s | VALIDADO |
| Primeira palavra de uma resposta curta | ~0,6 s (p50 0,57 s, p95 0,60 s) | VALIDADO |
| Prompt de 3k tokens já em cache | 0,60 s, contra 42 s sem cache | VALIDADO |
| RAM do servidor (repouso → após testes) | 3,3 GB → 5,4 GB | VALIDADO |
| Estabilidade (10 requisições seguidas + baterias longas) | sem erros ou travamentos | VALIDADO |
| Recuperar um fato no início, meio e fim de 8,4k tokens | 9/9 acertos, e manteve uma instrução antiga | VALIDADO |
| Temperatura/throttling | sensores exigem administrador | NÃO TESTADO |

**Threads:** 6 para escrever e 8 para ler são o ótimo. Com mais que isso entram os núcleos de eficiência e piora.
**GPU integrada (UHD 770):** testada com a build oficial Vulkan e **2× mais lenta** que a CPU.

## 3. Comparação dos harnesses

| Tarefa | Pi | Hermes | Claude Code |
|---|---|---|---|
| T1 – função + testes (otimizado) | **VALIDADO, 85 s** | VALIDADO, 155 s | VALIDADO, 235 s |
| T2 – app multi-arquivo + CLI + testes | **VALIDADO, 551 s** | interrompido | NÃO TESTADO |
| T3 – consertar projeto defeituoso | NÃO TESTADO | NÃO TESTADO | NÃO TESTADO |
| T5 – subagentes | sem suporte nativo | NÃO TESTADO (nativo) | NÃO TESTADO (nativo) |
| Tamanho do prompt fixo | ~1,9k tokens | ~4–5k | 4,5k (enxuto) / 19,8k (completo) |

- **Melhor em tarefas simples e intermediárias medidas: Pi.** Tem o menor prompt fixo e o melhor reaproveitamento de cache.
- **Claude Code** tem mais recursos (subagentes, 22 ferramentas), mas é o mais pesado para este hardware. Use `-Enxuto`.
- **Hermes** fica no meio e tem subagentes nativos.
- **Não declaro vencedor geral:** os testes T2–T5 ficaram incompletos (detalhes em `auditoria/harness_comparison.md`).

## 4. Problemas encontrados

| Problema | Evidência | Causa |
|---|---|---|
| Claude Code reprocessava o prompt inteiro em todo turno (5–6k tokens, 2–3 min cada) | log do servidor + corpos capturados (`auditoria/raw/claude-capture`) | O CLI envia um aviso de sistema que muda a cada turno; o adaptador o colocava no início do prompt. Em modelos híbridos como o Bonsai, isso invalida o cache |
| Leitura de textos longos lenta | 33 contra 57 tokens/s com 4k tokens de profundidade | Cache de atenção em 4 bits (q4_0) é caro de descompactar na CPU |
| RAM chegando a 11,9 GB | memória do processo após os testes | Cache de prompts com limite padrão de 8 GB |
| Loops e chamadas repetidas de ferramenta | 1 de 10 tarefas sem concluir | Amostragem "criativa" (temp 0,7 + penalidade de presença 1,5) |
| Prompt do Claude Code muito grande | 19.822 tokens só de instruções e ferramentas | Desenho do CLI (22 ferramentas) |
| Pi informa sucesso mesmo com falha de conexão | exit 0 com "Connection error" | Comportamento do harness |

Lista completa com 15 itens: `auditoria/bottlenecks.md`.

## 5. Melhorias implementadas

1. **Adaptador do Claude Code** mantém os avisos de sistema no lugar certo, e o cache volta a funcionar.
2. **Cache de atenção f16**, em vez de 4 bits, e **contexto de 64k**, em vez de 262k. Os agentes nunca passaram de ~20k; os 262k só existiam à custa do cache lento.
3. **Cache de prompts limitado a 2 GB**.
4. **Perfil "agente"** nos três harnesses: temperatura 0,2 e sem penalidade de presença.
5. Harnesses avisados do novo limite de contexto (Pi, Hermes; Claude Code compacta aos 60k).
6. Opções novas: `-Enxuto` (Claude Code), `-SemVisao`, `-Modelo 2B`, `-Perfil original` (desfaz tudo).
7. Scripts Linux, modelo 2B, manual simples e bateria de testes reproduzível.

**Testado e descartado:**
- converter os pesos para Q4_0 (escrita 48% mais lenta);
- iGPU via Vulkan (2× mais lenta);
- mais threads;
- lotes maiores;
- cache q8_0.

## 6. Antes e depois

| Métrica | Antes | Depois | Ganho |
|---|---|---|---|
| Leitura de prompt, 8,4k tokens | 31,5 t/s | 49,1 t/s | **+56%** |
| Leitura de prompt, 3,1k tokens | 43,6 t/s | 60,8 t/s | **+39%** |
| Prompt de 3k tokens sem cache (até a 1ª palavra) | 51,6 s | 42,2 s | **−18%** |
| RAM do servidor após a bateria de contexto | 11,9 GB | 5,3 GB | **−56%** |
| RAM em repouso | 3,6 GB | 3,3 GB | −9% |
| Escrita (geração curta) | 18,2 t/s | 17,0 t/s | −6% (dentro da variação observada; não confirmado como perda) |
| Acerto cognitivo (32 testes verificáveis) | 56,2% | 75,0% | **+18,8 pontos** |
| Tool calling (10 tarefas com ferramentas reais) | 90% | 100% | +10 pontos |
| Claude Code T1 | 701 s | 235 s | **−66%** |
| Hermes T1 | 209 s | 155 s | −26% |
| Pi T1 | 89 s | 85 s | −4% |

Comprovado: velocidades, memória e tempos dos agentes, medidos em execuções reais. Tendência, com amostra pequena (2 repetições): os ganhos de acerto cognitivo e de ferramentas.

## 7. Capacidades e limitações

**Consegue sozinho (comprovado):**
- usar ferramentas corretamente: 0 chamadas malformadas em todos os testes;
- ler e escrever arquivos e rodar testes;
- escrever funções simples com testes;
- montar um pacote com CLI e tratamento de erro (Pi T2);
- achar o arquivo com bug numa descrição de projeto;
- corrigir uma busca binária quebrada;
- recuperar informações em textos de 8k tokens.

**Tem dificuldade (comprovado):**
- aritmética (37×43 virou 1291; soma de primos errada);
- calendário;
- consistência de nomes (`additional` × `adicional`);
- casos de borda (`HTTPServerError`);
- tarefas sequenciais longas, em que às vezes repete ações.

Tarefas maiores (T2) exigem muitos ciclos: 26 chamadas e ~9 min no Pi. **Sempre revise o resultado.**

## 8. Próximos passos (por impacto × dificuldade)

| Impacto | Dificuldade | Ação |
|---|---|---|
| Alto | Baixa | Usar **Pi** ou **Claude Code `-Enxuto`** no dia a dia |
| Alto | Média (compra) | **GPU NVIDIA dedicada de 4–6 GB** (há builds CUDA oficiais para PQ2_0). Deve acelerar muito a leitura de prompt, mas é **hipótese não medida**; conferir se o gabinete comporta |
| Médio | Baixa | Completar os testes T2–T5 (comandos prontos em `PROGRESSO.md`) |
| Médio | Baixa | Avaliar o modelo 2B (já baixado) para tarefas muito simples |
| Médio | Média | Testar speculative decoding por n-gram para edições de código |
| Baixo | Baixa | Validar os scripts num Linux real |

## Conclusão — melhor configuração encontrada

```
Servidor:   -c 65536  --cache-type-k f16 --cache-type-v f16  --cache-ram 2048
            -t 6 -tb 8  -b 256 -ub 128  -fa on  (CPU; GPU integrada desativada)
Amostragem: temperature 0.2, top_p 0.95, top_k 20, presence_penalty 0
Harness:    Pi para rapidez; Claude Code com -Enxuto quando precisar dos recursos dele
```

Já é o padrão de `iniciar-bonsai.cmd`. Para voltar ao anterior: `.\iniciar-bonsai.ps1 -Perfil original`.

---

**Arquivos:** `MANUAL_SIMPLES.md` (como usar) · `PROGRESSO.md` (o que faltou) · `auditoria/` (inventário, gargalos, otimizações, comparação, JSONs, scripts e dados brutos).

**Reproduzir:**
```powershell
cd auditoria\scripts
python bench_perf.py novo; python bench_cog.py novo agente 2; python bench_tools.py novo agente 2
python bench_ctx.py novo 500,2000,5500; python compare.py baseline novo
python run_agent_test.py pi t1 novo 2400
```
