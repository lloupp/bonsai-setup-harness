# Bonsai como servidor para outros harnesses

O Bonsai roda separado dos clientes. Inicie com `iniciar-bonsai.cmd` e deixe esse servidor ativo. Depois abra qualquer cliente/harness que aceite a API OpenAI Chat Completions e modelos personalizados.

| Campo | Valor |
|---|---|
| URL base OpenAI | `http://127.0.0.1:8080/v1` |
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

O contexto atual do servidor e 262144 tokens. A entrada, o historico, as descricoes de ferramentas e a resposta compartilham essa janela. Consulte `/props` ou o painel para o limite efetivamente ativo. Apenas uma geracao e atendida por vez; outros clientes aguardam na fila. Prompts grandes, como o prompt completo do Claude Code, podem levar varios minutos nesta CPU.

`127.0.0.1` permite uso neste computador. O servidor nao foi exposto para outros computadores da rede.
