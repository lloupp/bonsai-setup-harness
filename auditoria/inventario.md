# Inventário técnico — Bonsai 4B local (verificado em 17/10/2026)

Todos os itens abaixo foram verificados por execução ou leitura direta neste computador. Script de metadados: `scripts/gguf_meta.py`.

## Hardware

| Item | Valor verificado | Como |
|---|---|---|
| CPU | Intel Core i5-14500T (Raptor Lake, 35 W "T"), 14 núcleos (6P + 8E), 20 threads, base 1,7 GHz, L2 11,5 MB, L3 24 MB | `Win32_Processor` |
| RAM | 15,69 GB visíveis; 3,2 GB livres com o servidor original carregado | `Win32_OperatingSystem` |
| Swap | pagefile 16 GB, ~1,9 GB em uso | `Win32_PageFileUsage` |
| GPU | Intel UHD Graphics 770 (integrada, memória compartilhada, Vulkan: 8 GB visíveis) | `Win32_VideoController`, `llama-bench --list-devices` |
| Disco | C: 238 GB, 28 GB livres (89 % usado) | `df` |
| Temperatura | **Não disponível**: sensores exigem privilégios de administrador (WMI negou acesso) | — |
| Plano de energia | **Não disponível** (WMI `Win32_PowerPlan` exige administrador) | — |

## Modelo

| Item | Valor | Evidência |
|---|---|---|
| Variante | **Ternary Bonsai 2 4B** (PrismML) — não o Bonsai 4B original | `general.name = Ternary-Bonsai-2-4B` |
| Arquivo | `models/Ternary-Bonsai-2-4B-PQ2_0.gguf` (1,146 GB) + `mmproj-Q8_0` (367 MB, visão) | `ls`, `manifest.json` (SHA256 conferidos na instalação) |
| Quantização | `PQ2_0` — 2,13 bpw, grupo 128, formato próprio da Prism (pesos ternários) | `/props model_ftype` |
| Arquitetura | `qwen35` híbrida: 32 blocos, **8 de atenção completa** (1 a cada 4) + **24 Gated DeltaNet** (recorrentes), 2560 dim, 16 heads / 4 KV heads, head 256 | metadados GGUF |
| Particularidade | Pesos em domínio **Hadamard** (`prism.hadamard.*`, bloco 512): o runtime aplica transformadas Walsh-Hadamard nas ativações | metadados GGUF |
| Contexto nativo | 262 144 tokens | `qwen35.context_length` |
| Chat template | Jinja Qwen3.5 (visão, `<tool_call>`, `enable_thinking`) embutido no GGUF; servidor com `--jinja` | `/props chat_template` |

## Runtime

| Item | Valor |
|---|---|
| Backend | Fork PrismML do llama.cpp, `prism-b10777-e3de715` (build 10777), CPU x64, Clang 20.1.8 — **é a versão mais recente publicada** (release de 14/10/2026) e a única com kernels PQ2_0 |
| Compatibilidade PQ2_0 | O llama.cpp oficial não tem o tipo PQ2_0; somente o fork da Prism. Uma conversão para formato convencional (Q4_0) foi testada: mesma velocidade de prompt e **metade** da velocidade de geração (ver `optimizations.md`) — o backend Prism é o apropriado |
| GPU alternativa | Build oficial Vulkan da mesma versão instalada em `bin-vulkan/` (SHA256 conferido) — mais lenta na UHD 770 (ver benchmarks) |
| Endpoint | `http://127.0.0.1:8080` (OpenAI `/v1/chat/completions`, Anthropic `/v1/messages`, `/health`, `/props`, `/slots`) |
| Gateway de identificação | `127.0.0.1:8083` (Node, roteia `/pi`, `/hermes`, `/claude`), não altera conteúdo |
| Adaptador Claude | `127.0.0.1:8082` (`claude-test/adapter.mjs`): une blocos de system prompt em um só (o template exige uma única mensagem de sistema) |
| Streaming | Suportado e validado (SSE, medição de TTFT em `scripts/common.py`) |
| Tool calling | Suportado e validado: `tool_calls` estruturados no formato OpenAI, 0 argumentos inválidos e 0 chamadas "vazadas" como texto em 10 execuções (`raw/tools_baseline_padrao.json`) |

## Configuração original do servidor (`iniciar-bonsai.ps1`)

`-c 262144 -np 1 -t 6 -tb 8 -b 256 -ub 128 --cache-type-k q4_0 --cache-type-v q4_0 -fa on --jinja --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --presence-penalty 1.5 --reasoning-budget 0`, com `--mmproj`. Padrões implícitos relevantes: `--cache-ram 8192` (cache de prompts em RAM de até 8 GB), `--ctx-checkpoints 32`, `--checkpoint-min-step 8192`.

## Memória medida

| Situação | Working set | Memória privada |
|---|---|---|
| Logo após carregar (262k, KV q4_0, visão) | 3,9 GB | 3,6 GB |
| Após ~20 requisições variadas (teste de contexto) | — | **11,9 GB** (cache de prompts em RAM crescendo até o limite padrão de 8 GB), RAM livre caiu para 1–2 GB |

## Harnesses (três instalações independentes)

| Harness | Versão | Local | Integração | Ferramentas | Subagentes |
|---|---|---|---|---|---|
| Hermes Agent | v0.22.2 (`d923a5eb48`) | `hermes-runtime/`, perfil `hermes-profile/`, Python gerenciado em `hermes-profile/tools` | OpenAI Chat Completions via `8083/hermes/v1` | terminal, file (read/write/patch/search), todo, memory; toolsets extras disponíveis (`delegation`, `execute_code`…) | **Nativo**: toolset `delegation` → `delegate_task` |
| Pi Agent | 1.3.0 (`@earendil-works/pi-coding-agent`) | `pi-runtime/`, perfil `pi-profile/` | OpenAI Completions via `8083/pi/v1` (`models.json`) | read, bash, write, edit, grep, find, ls | **Não nativo**: só a extensão de exemplo `examples/extensions/subagent` (subprocesso `pi`) |
| Claude Code CLI | 2.1.302 | `%USERPROFILE%\.local\bin\claude.exe`, perfil `claude-test/profile` | **Protocolo Anthropic Messages** → adaptador 8082 → gateway → `/v1/messages` do llama.cpp | Read, Write, Edit, Bash, Glob, Grep, Task, Skill… (22 padrão) | **Nativo**: ferramenta Task/Agent |

Isolamento verificado: cada launcher define variáveis só no processo; perfis em pastas próprias; `~/.pi`, `~/.claude` e credenciais globais não são usados.
