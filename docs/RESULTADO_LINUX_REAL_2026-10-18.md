# Bonsai 2B e 4B — teste de inferencia real (18/10/2026)

## Evidencia verificavel

- Execucao: [GitHub Actions #39096818991](https://github.com/lloupp/bonsai-setup-harness/actions/runs/39096818991)
- Workflow: `.github/workflows/model-smoke.yml`
- Runner: `ubuntu-latest` (Linux GitHub-hosted), **CPU**; nao foi Linux Mint no computador do usuario
- Commit testado: `8fbcc521dc0070adaa22b49bdf91e54d7f65123b`
- Conclusao da execucao: **success**, inclusive etapa de inferencia 2B/4B
- Runtime: release `prism-b10777-e3de715`
- Downloads concluídos e SHA256 checados: runtime Ubuntu x64, GGUF 2B/4B PQ2_0 e os respectivos mmproj Q8_0
- Parametros: perfil otimizado, `--sem-visao`, contexto 2048, KV f16, cache RAM 128 MB, CPU
- API: `/v1/models` validou o alias antes de cada chamada; `/v1/chat/completions` respondeu com sucesso

## Resultado observado (uma solicitacao por modelo)

| Metrica | Bonsai 2B | Bonsai 4B |
|---|---:|---:|
| Alias | `bonsai-2-2b` | `bonsai-2-4b` |
| Prompt | `Diga apenas a palavra OK.` | mesmo |
| Saida | `OK` | `OK` |
| Tokens de entrada | 19 | 19 |
| Tokens de saida | 2 | 2 |
| Tempo wall de resposta | 0,4611 s | 0,9842 s |
| Validador | PASS | PASS |

**Importante:** tempo wall nao inclui download nem inicializacao. Com apenas
uma resposta de 2 tokens por modelo, **nao e valido concluir superioridade
de desempenho em tarefas reais, tokens/s ou qualidade cognitiva**.
Nao houve medicao de uso de RAM final, subagentes ou edicao real de codigo.

## Limites desta execucao

1. O setup e o boot Linux foram comprovados em `ubuntu-latest`, mas nao no Linux Mint instalado no PC do usuario.
2. Nao houve benchmark de contexto longo, velocidade sustentada, carga concorrente ou testes de ferramentas.
3. Os tres harnesses locais (Pi Agent, Hermes e Claude Code) nao foram
   instalados nesta execucao. A sua configuracao/adapter privado nao esta
   disponivel no repositorio publico e nao se deve atribuir sucesso a eles.
4. Os logs e `smoke_*.json` foram anexados como artefato do workflow, com
   retencao de 7 dias. Este documento registra os resultados apos esse prazo.

## Proximas validacoes recomendadas

- Executar `bench_perf.py` e `bench_cog.py` para 2B/4B na **mesma**
  maquina, sem outros aplicativos interferindo, registrando multiplas repeticoes.
- Executar Linux Mint e testes reais dos harnesses apenas com suas
  instalacoes/credenciais locais, preferencialmente num usuario/VM isolado.
