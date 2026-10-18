# Bonsai como servidor para outros harnesses

O Bonsai roda separado dos clientes. Por padrão, o servidor escuta
em `0.0.0.0:8080`, aceitando conexões da LAN; clientes no próprio PC
continuam acessando `127.0.0.1:8080`. Em outros computadores, use o IP
privado do servidor, por exemplo `http://192.168.1.100:8080/v1`.
A chave `local` **não implementa autenticação**. Restrinja a porta
no firewall somente para a rede privada confiável, conforme
[REDE_LOCAL.md](REDE_LOCAL.md).

| Campo | Valor |
|---|---|
| URL base OpenAI (PC servidor) | `http://127.0.0.1:8080/v1` |
| URL base OpenAI (outro PC) | `http://<IP-PRIVADO>:8080/v1` |
| Modelo | `bonsai-2-4b` |
| Chave, se o cliente exigir | `local` |
| Chat | `POST /v1/chat/completions` |
| Lista de modelos | `GET /v1/models` |
| Saude | `GET http://127.0.0.1:8080/health` |
| Painel | `http://127.0.0.1:8090` |

Fechar um harness nao encerra o servidor. As ferramentas pertencem ao harness: ele envia suas definicoes, recebe os pedidos do modelo, executa as acoes conforme suas permissoes e devolve os resultados ao Bonsai. O servidor nao instala ferramentas por conta propria.

Para o painel identificar a origem, use uma das URLs base abaixo. Sao caminhos alternativos para o mesmo modelo, nao modelos ou servidores de inferencia separados:

- Pi: `http://127.0.0.1:8083/pi/v1`
- Hermes: `http://127.0.0.1:8083/hermes/v1`
- Cliente rotulado DeepSeek: `http://127.0.0.1:8083/deepseek/v1`
- Outros: `http://127.0.0.1:8083/outro/v1`

O gateway deve estar ativo: `iniciar-gateway.ps1`. Os inicializadores dos agentes e do painel o iniciam automaticamente. A API direta da porta 8080 funciona independentemente do gateway e do painel.

Claude Code usa protocolo Anthropic e o adaptador em `http://127.0.0.1:8082`, iniciado pelo seu launcher. Veja `CLAUDE_CODE_BONSAI.md`. Um cliente que exija especificamente recursos da API Responses ou modelos Anthropic pode precisar de adaptacao; compatibilidade OpenAI aqui significa Chat Completions.

## Exemplo em Python

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8080/v1", api_key="local")
response = client.chat.completions.create(
    model="bonsai-2-4b",
    messages=[{"role": "user", "content": "Ola, responda em portugues."}],
    max_tokens=512,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
print(response.choices[0].message.content)
```

O perfil `otimizado` inicia com contexto padrao de 65536 tokens (o perfil `original` usa 262144). A entrada, o historico, as descricoes de ferramentas e a resposta compartilham essa janela. Consulte `/props` ou o painel para o limite efetivamente ativo. Apenas uma geracao e atendida por vez; outros clientes aguardam na fila. Prompts grandes, como o prompt completo do Claude Code, podem levar varios minutos nesta CPU.

Por padrão, o servidor também recebe requisições de outros dispositivos da LAN, sujeito ao firewall. O gateway (8083), o painel (8090) e o adaptador Anthropic local (8082) **não são automaticamente expostos** para a rede.


## Selecao do 2B nos benchmarks

O modelo ativo e definido no inicializador do servidor, mas o cliente de benchmark
precisa usar o mesmo alias. No Windows:

```powershell
.\parar-bonsai.ps1
.\iniciar-bonsai.ps1 -Modelo 2B -SemNavegador
$env:BONSAI_MODEL = 'bonsai-2-2b'
python auditoria\scripts\bench_perf.py 2b
```

No Linux:

```bash
./linux/setup-linux.sh --com-2b
./linux/parar-bonsai.sh
./linux/iniciar-bonsai.sh --modelo 2B --sem-visao
BONSAI_MODEL=bonsai-2-2b python3 auditoria/scripts/bench_perf.py 2b
```

O benchmark interrompe com erro explicito se `/v1/models` nao disponibilizar o alias
solicitado. `BONSAI_URL` permite escolher outra porta/base para o servidor.

A coleta de RAM dos benchmarks utiliza memoria residente (RSS, `ws_mb`) no Linux;
`priv_mb` e uma metrica de memoria privada do Windows e nao tem equivalente direto
nesta implementacao. Compare valores dentro do mesmo sistema, nunca RSS Linux
contra private commit Windows.

**Atencao:** a referencia a `CLAUDE_CODE_BONSAI.md` e a launchers de agentes diz
respeito a arquivos da instalacao local, nao distribuidos neste repositorio publico.
