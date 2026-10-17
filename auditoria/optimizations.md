# Otimizações — hipóteses, experimentos e decisão

Cada hipótese foi testada isoladamente contra o baseline. Backups dos arquivos originais: `auditoria/backups/`.

## Aceitas (implementadas)

| # | Mudança | Arquivo | Experimento | Resultado | Decisão |
|---|---|---|---|---|---|
| A1 | Adaptador Claude: mensagens `role:system` no meio da conversa ficam **na posição original** (como `<system-reminder>` no turno do usuário), em vez de irem para o system prompt inicial | `claude-test/adapter.mjs` | Claude Code T1 antes × depois; contagem de tokens reprocessados no log do servidor | Tokens reprocessados por chamada: 5.680 → 1.036 (**−82%**); tempo por chamada ao modelo: 175 s → 73 s (**−58%**) | Aceita |
| A2 | KV cache `q4_0` → `f16` | `iniciar-bonsai.ps1` (perfil otimizado) | `llama-bench -ctk/-ctv` (9 combinações × 2 profundidades) + API | Prompt @ 8,4k tokens: 31,5 → 49,1 t/s (**+56%**); @ 3,1k: +39%; recuperação de fatos inalterada (100%) | Aceita |
| A3 | Contexto 262.144 → **65.536** | idem + `pi-profile/models.json`, `hermes-profile/config.yaml`, env do Claude Code (`CLAUDE_CODE_MAX_CONTEXT_TOKENS`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`) | Necessário para o f16 caber (2 GB de KV contra 8,6 GB) | Os agentes usam no máximo ~20k; os harnesses foram ajustados para compactar antes do limite | Aceita |
| A4 | `--cache-ram 2048` (padrão era 8192) | `iniciar-bonsai.ps1` | Memória privada após a mesma bateria de contexto | 11,9 GB → 5,3 GB (**−56%**) | Aceita |
| A5 | Perfil de amostragem "agente" (temp 0,2, top_p 0,95, presence_penalty 0) nos harnesses | `pi-profile/models.json`, `hermes-profile/config.yaml`, `claude-test/adapter.mjs` (`BONSAI_SAMPLING=original` desativa) | Bateria cognitiva com o mesmo servidor e as mesmas seeds; tool calling | Cognitivo 68,8% → **75,0%**; ferramentas 90% → **100%** | Aceita (tendência, amostra pequena) |
| A6 | Opção `-Enxuto` no Claude Code (6 ferramentas) | `iniciar-claude-bonsai.ps1` | Tokens do 1º prompt | 19.822 → ~4.500 tokens | Opcional (o padrão completo foi mantido a pedido do usuário) |
| A7 | Visão opcional (`-SemVisao`) | `iniciar-bonsai.ps1` | Memória do mmproj (367 MB em disco) | ~0,3–0,4 GB a menos | Opcional |

## Rejeitadas (testadas e revertidas)

| # | Hipótese | Resultado medido | Motivo |
|---|---|---|---|
| R1 | Converter os pesos PQ2_0 para Q4_0 (kernels de CPU mais maduros) | Prompt 56 t/s (≈ igual), geração **10,4 t/s (−48%)**, arquivo 2,4 GB | Mais lento; o arquivo foi apagado |
| R2 | iGPU Intel UHD 770 via build oficial Vulkan | Prompt 31 t/s (−57%), geração 8,6 t/s (−57%) | Mais lento; a build fica em `bin-vulkan/` apenas como evidência |
| R3 | ubatch 512 | 37 t/s contra 70 t/s com 128 | Pior; mantido 128 (64 ficou no ruído: 73 ± 2) |
| R4 | Mais threads (12/14) | Prompt 53/51 t/s contra 59 com 8; geração 18 contra 20 com 6 | Pior; mantido `-t 6 -tb 8` |
| R5 | Flash attention desligado | 55,5 contra 57,1 t/s | Indiferente; mantido `on` |
| R6 | KV q8_0 (meio-termo) | pp @ 4096: 37,6 t/s contra 57,2 com f16 | Pior que f16 e cabe a mesma janela útil |

## Não testadas (motivo)

- **Speculative decoding** (`--spec-type ngram-*`): pode acelerar a geração em edições de código repetitivas, mas a geração não é o gargalo (o prompt é). Fica como próximo passo.
- **mlock / `--load-mode`**: o modelo tem 1,1 GB e não houve paginação observável; o efeito esperado é nulo.
- **Placa de vídeo dedicada (CUDA)**: hardware ausente.

## Como reverter

```powershell
.\parar-bonsai.ps1; .\iniciar-bonsai.ps1 -Perfil original     # servidor como antes
Copy-Item auditoria\backups\pi-models.json pi-profile\models.json
Copy-Item auditoria\backups\hermes-config.yaml hermes-profile\config.yaml
Copy-Item auditoria\backups\adapter.mjs claude-test\adapter.mjs
Copy-Item auditoria\backups\iniciar-claude-bonsai.ps1 .\iniciar-claude-bonsai.ps1
Copy-Item auditoria\backups\iniciar-bonsai.ps1 .\iniciar-bonsai.ps1
```
