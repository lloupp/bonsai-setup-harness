# bonsai-setup-harness

Setup reproduzível do **Ternary Bonsai 2 (4B/2B)** da PrismML rodando localmente na CPU (Windows e Linux), com API compatível com OpenAI, painel de monitoramento, gateway de identificação de clientes e uma **bateria de benchmarks e testes de agentes** com resultados reais.

> Este repositório **não inclui** pesos, binários do runtime nem os agentes (Pi, Hermes, Claude Code). Os scripts de setup baixam o runtime e os modelos das fontes oficiais e conferem o SHA256.

## Início rápido

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1      # -Com2B para baixar também o 2B
.\iniciar-bonsai.cmd                                             # http://127.0.0.1:8080
```

**Linux x64:**
```bash
chmod +x linux/*.sh
./linux/setup-linux.sh          # --com-2b para baixar também o 2B
./linux/iniciar-bonsai.sh       # http://127.0.0.1:8080
```

API: `http://127.0.0.1:8080/v1`, modelo `bonsai-2-4b`, chave `local`. Mais detalhes em [MANUAL_SIMPLES.md](MANUAL_SIMPLES.md) e [docs/API_LOCAL.md](docs/API_LOCAL.md).

## Configuração padrão (perfil `otimizado`)

`-c 65536 --cache-type-k f16 --cache-type-v f16 --cache-ram 2048 -t 6 -tb 8 -b 256 -ub 128 -fa on`, CPU.
Para agentes, use `temperature 0.2` e `presence_penalty 0`. O perfil `original` (`-Perfil original` / `--perfil original`) reproduz a configuração anterior (262k, KV q4_0).

## Resultados (i5-14500T, 16 GB)

| Métrica | Antes | Depois |
|---|---|---|
| Leitura de prompt, 8,4k tokens | 31,5 t/s | 49,1 t/s (+56%) |
| RAM do servidor após a bateria | 11,9 GB | 5,3 GB (−56%) |
| Acerto cognitivo verificável | 56,2% | 75,0% |
| Tool calling real | 90% | 100% |
| Claude Code, tarefa T1 | 701 s | 235 s (−66%) |

Relatório completo: [RELATORIO_FINAL_BONSAI.md](RELATORIO_FINAL_BONSAI.md) ([HTML](RELATORIO_FINAL_BONSAI.html)) · O que falta testar: [PROGRESSO.md](PROGRESSO.md)

## Validacao e testes pendentes

O pipeline GitHub Actions executa testes **offline** de Python, Bash e Node, sem baixar ou
iniciar os modelos. A inferencia real de 2B/4B em CPU no Ubuntu passou em 18/10/2026:
[resultado verificado](docs/RESULTADO_LINUX_REAL_2026-10-18.md).
Para benchmarks completos no Windows/Linux e configuracao correta do 2B,
consulte [docs/TESTES_PENDENTES.md](docs/TESTES_PENDENTES.md).

Para selecionar o modelo nos benchmarks Python, ajuste `BONSAI_MODEL` para
`bonsai-2-2b` ou `bonsai-2-4b`; a bateria confirma o alias ativo em
`/v1/models` antes de enviar a primeira solicitacao. No Linux, a memoria do processo
e medida em RSS (`ws_mb`), nao em private commit (`priv_mb`) como no Windows;
nao compare esses dois indicadores diretamente entre sistemas.

**Limite de reproducibilidade:** os pesos e as instalacoes dos tres harnesses nao
estao neste repositorio. Os scripts `run_agent_test.py` exigem os perfis e
instalacoes locais descritos no relatorio. O CI nao comprova ganhos de performance
nem executa os agentes.

## Estrutura

| Pasta/arquivo | Conteúdo |
|---|---|
| `setup-windows.ps1`, `linux/setup-linux.sh` | Download verificado do runtime (`prism-b10777-e3de715`) e dos modelos |
| `iniciar-bonsai.*`, `parar-bonsai.*`, `linux/*.sh` | Servidor (perfis `otimizado`/`original`, `-Modelo 2B`, `-SemVisao`) |
| `iniciar-gateway.ps1`, `monitor/` | Gateway de identificação (8083) e painel (8090) |
| `auditoria/` | Inventário, gargalos, otimizações, comparação de harnesses, JSONs de resultados |
| `auditoria/scripts/` | Bateria reproduzível: `bench_perf.py`, `bench_cog.py`, `bench_tools.py`, `bench_ctx.py`, `bench_divergence.py`, `run_agent_test.py`, `compare.py` |
| `auditoria/agent-tests/` | Projetos de teste e verificadores ocultos dos agentes |

## Fontes

- Modelos: https://huggingface.co/prism-ml/Ternary-Bonsai-2-4B-gguf · https://huggingface.co/prism-ml/Ternary-Bonsai-2-2B-gguf (Apache 2.0)
- Runtime: https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b10777-e3de715
- Documentação PrismML: https://docs.prismml.com/models/bonsai-2-4b
