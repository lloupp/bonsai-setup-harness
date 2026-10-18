# Validacao pendente — Bonsai 2 (17–18/10/2026)

## O que o CI valida e o que ele nao valida

O workflow `.github/workflows/offline-tests.yml` executa sintaxe Bash e Python,
testes unitarios Python, testes Node do monitor e comparacao dos registros ja
existentes. **Nao carrega GGUF, nao mede tokens/s e nao inicia Pi, Hermes ou Claude Code.**
Os ganhos registrados em `RELATORIO_FINAL_BONSAI.md` permanecem resultados da
maquina original, nao uma nova medicao.

Os scripts de benchmarking usam `BONSAI_URL` (padrao `http://127.0.0.1:8080`)
e `BONSAI_MODEL` (padrao `bonsai-2-4b`). Antes da primeira chamada ao modelo
verificam `GET /v1/models`; se o modelo nao estiver disponivel, falham sem
gerar um resultado para outro modelo.

## Executar comparacao 4B x 2B — Windows (PowerShell)

Na raiz do projeto, com os pesos do 2B ja instalados:

```powershell
.\parar-bonsai.ps1
.\iniciar-bonsai.ps1 -Modelo 4B -SemVisao -SemNavegador
$env:BONSAI_MODEL = 'bonsai-2-4b'
python auditoria\scripts\bench_perf.py repeticao_4b
python auditoria\scripts\bench_cog.py repeticao_4b agente 2

.\parar-bonsai.ps1
.\iniciar-bonsai.ps1 -Modelo 2B -SemVisao -SemNavegador
$env:BONSAI_MODEL = 'bonsai-2-2b'
python auditoria\scripts\bench_perf.py repeticao_2b
python auditoria\scripts\bench_cog.py repeticao_2b agente 2
Remove-Item Env:\BONSAI_MODEL
```

Compare apenas testes com mesmo numero de repeticoes, contexto, amostragem e
condicoes da maquina. O `compare.py` resume desempenho e contexto se os
respectivos arquivos `ctx_*.json` existirem; dados ausentes nao devem ser
interpretados como zero.

## Testar Linux Mint / Ubuntu x64

No Linux Mint real (e nao apenas Git Bash no Windows):

```bash
chmod +x linux/*.sh
./linux/setup-linux.sh --com-2b
./linux/iniciar-bonsai.sh --modelo 2B --sem-visao
curl -fsS http://127.0.0.1:8080/health
curl -fsS http://127.0.0.1:8080/v1/models
BONSAI_MODEL=bonsai-2-2b python3 auditoria/scripts/bench_perf.py linux_2b
BONSAI_MODEL=bonsai-2-2b python3 auditoria/scripts/bench_cog.py linux_2b agente 2
./linux/parar-bonsai.sh
```

No Linux, a memoria residente e medida por `/proc/<pid>/status` e exposta
como `ws_mb` (RSS). No Windows, o relatorio tambem contem `priv_mb`
(private commit). **RSS e private commit nao sao metricas equivalentes.**
Para desempenho, priorize TTFT, tokens/s e RAM medidas com metrica igual
na mesma maquina. Verifique que o PID registrado e do processo Bonsai.

## Testes de agentes ainda nao executados

`auditoria/scripts/run_agent_test.py` foi criado para o ambiente **Windows
original** e depende de instalacoes locais nao incluidas aqui: `pi-runtime/`,
`pi-profile/`, `hermes-test/`, `hermes-profile/` e `claude-test/`, mais
a CLI Claude Code e o adaptador da porta 8082. Portanto ele **nao e portavel
para Linux sem adaptacoes**; nao ha evidencia de execucao dos harnesses no Linux.

Com os harnesses locais instalados e Bonsai 4B pronto:

```powershell
python auditoria\scripts\run_agent_test.py hermes t2 verificacao 2400
python auditoria\scripts\run_agent_test.py claude t2 verificacao 2400
python auditoria\scripts\run_agent_test.py pi t3 verificacao 2400
python auditoria\scripts\run_agent_test.py hermes t3 verificacao 2400
python auditoria\scripts\run_agent_test.py claude t3 verificacao 2400
```

Subagentes (T5) ainda requerem configuracao e validacao das ferramentas de
delegacao de cada harness; `t2sub` sozinho nao prova que houve delegacao.
T4 (agent loop), speculative decoding, throttling e benchmarks repetidos
tambem permanecem pendentes. Nao extrapolar resultados de T1/T2.

## Cuidados de seguranca

As baterias cognitivas e de ferramentas **executam codigo gerado pelo modelo**
em processos locais; uma pasta temporaria **nao e um sandbox de seguranca**.
O runner de harnesses tambem usa permissao ampla (`--yolo` no Hermes).
Execute somente em uma VM/usuario isolado, sem credenciais de producao, sem
arquivos pessoais montados e com permissoes minimas. O CI offline nao executa
as geracoes do modelo.
