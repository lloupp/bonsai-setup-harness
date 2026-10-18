# Progresso da auditoria Bonsai 4B — situação em 17/10/2026

Testes interrompidos a pedido do usuário para iniciar as cópias (pendrive e GitHub).

## Concluído

| Fase | Situação | Onde está |
|---|---|---|
| 1. Inventário | VALIDADO | `auditoria/inventario.md` |
| 2. Benchmark do modelo (desempenho, cognitivo, contexto, tool calling) | VALIDADO (baseline e otimizado) | `auditoria/baseline.json`, `auditoria/benchmarks.json`, `auditoria/raw/` |
| 3. Auditoria dos 3 harnesses | VALIDADO (versões, configuração, protocolo, integração) | `auditoria/inventario.md`, `auditoria/harness_comparison.md` |
| 4. Testes reais dos agentes | **PARCIAL**: T1 nos 3 harnesses (antes e depois); T2 só no Pi | `auditoria/raw/agents/`, `auditoria/agent-tests/runs/` |
| 5. Gargalos | VALIDADO (15 itens, com evidência) | `auditoria/bottlenecks.md` |
| 6. Otimização | VALIDADO (7 aceitas, 6 rejeitadas por medição) | `auditoria/optimizations.md` |
| 8. Configuração ideal implementada | VALIDADO | `iniciar-bonsai.ps1` (perfil `otimizado`), harnesses ajustados |
| Linux | Scripts prontos; setup executado no Git Bash (download, SHA256, extração e modelos OK) | `linux/` |
| Modelo 2B | Baixado com SHA256 conferido | `models/Ternary-Bonsai-2-2B-*` |
| Build Vulkan | Baixada, verificada e testada (mais lenta) | `bin-vulkan/` |
| Manual simples | Pronto | `MANUAL_SIMPLES.md` |
| Relatório final | Pronto com os dados reais obtidos | `RELATORIO_FINAL_BONSAI.md` / `.html` |

## O que faltou (NÃO TESTADO ou interrompido)

| Item | Situação | Como completar |
|---|---|---|
| Hermes T2 e Claude Code T2 | INTERROMPIDO (Hermes estava rodando) | `python auditoria/scripts/run_agent_test.py hermes t2 otimizado 2400` (idem `claude`) |
| T3 (projeto defeituoso) nos 3 harnesses | NÃO TESTADO | `... run_agent_test.py <pi\|hermes\|claude> t3 otimizado 2400` |
| T4 (ciclos do agent loop) | PARCIAL: só métricas de T1/T2 (chamadas ao modelo, iterações) | Sai do T3 acima: chamadas e iterações ficam em `raw/agents/*.json` |
| T5 subagentes (Hermes `delegate_task`, Claude `Task`) | NÃO TESTADO; preparado como `t2sub` | `$env:HERMES_TOOLSETS='terminal,file,delegation'; python run_agent_test.py hermes t2sub sub 2400` / `$env:CLAUDE_TOOLS='Read,Write,Edit,Bash,Glob,Grep,Task'; python run_agent_test.py claude t2sub sub 2400` |
| Subagentes no Pi | NÃO TESTADO: não há suporte nativo, só a extensão de exemplo `examples/extensions/subagent` | Instalar a extensão num perfil de teste |
| Repetir o benchmark final (3ª rodada da validação) | PARCIAL: o antes × depois foi medido uma vez com 3 repetições internas | `python auditoria/scripts/bench_perf.py final` e `compare.py baseline final` |
| Benchmark do modelo 2B | NÃO TESTADO (selecao do cliente corrigida nesta branch) | Veja `docs/TESTES_PENDENTES.md`; configure `BONSAI_MODEL=bonsai-2-2b` |
| Execução em Linux real | NÃO TESTADO (sem WSL/Linux nesta máquina) | `./linux/setup-linux.sh && ./linux/iniciar-bonsai.sh` num Linux |
| Temperatura/throttling | NÃO TESTADO (exige administrador) | Rodar HWiNFO/LibreHardwareMonitor durante `bench_perf.py` |
| Speculative decoding (ngram) | NÃO TESTADO | `--spec-type ngram-mod` no `srv-experimento.ps1` |
| Repositorio GitHub | Publicado; melhorias em branch de manutencao | Consulte o pull request para revisar as correcoes |

## Manutencao de 18/10/2026 (sem reexecutar inferencia)

- Correcoes propostas para selecionar e verificar o modelo nos benchmarks, coletar RSS no Linux e validar opcoes/assets dos inicializadores Linux.
- Testes offline automatizados em GitHub Actions para Python, Bash e Node. Eles nao substituem as baterias reais pendentes.
- Comandos e limitacoes: [docs/TESTES_PENDENTES.md](docs/TESTES_PENDENTES.md).

## Smoke test real no Ubuntu — 18/10/2026

- **PASSOU:** runtime PrismML oficial e GGUF 2B/4B (e mmproj) baixados e SHA256 verificados pelo GitHub Actions.
- **PASSOU:** servidores 2B e 4B iniciados em CPU no Linux Ubuntu com contexto 2048 e perfil otimizado; ambos responderam `OK` a uma requisicao real via API.
- **NAO TESTADO AQUI:** benchmarks completos, Linux Mint no PC, Pi Agent, Hermes, Claude Code, subagentes e agent loops.
- [Resultados e limites de interpretacao](docs/RESULTADO_LINUX_REAL_2026-10-18.md).
