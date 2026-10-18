# Bonsai local — manual simples

Este pacote roda o modelo de IA **Bonsai 2 (4B ou 2B)** no seu computador, sem internet e sem conta paga, e o conecta a três agentes de programação: **Pi**, **Hermes** e **Claude Code**.

O processamento acontece na máquina que hospeda o Bonsai. Por padrão,
o servidor aceita conexões da **rede local** (`0.0.0.0:8080`), sem
autenticação: restrinja o acesso no firewall a dispositivos confiáveis.
O próprio PC continua acessando `127.0.0.1`. Para desativar acesso
pela rede, use `-SomenteLocal` no Windows ou `--somente-local` no Linux.
Veja [instruções de rede e firewall](docs/REDE_LOCAL.md).

---

## 1. O que você precisa

| | Windows 10/11 x64 | Linux x64 (Ubuntu/Mint/Debian) |
|---|---|---|
| RAM | 8 GB no mínimo; 16 GB recomendados | igual |
| Disco | ~5 GB livres | igual |
| Programas | **Node.js 20+** (para Pi, Claude Code, gateway e painel) | `curl`, `tar`, `sha256sum` (já vêm), **Node.js 20+** |
| Placa de vídeo | Não precisa (roda na CPU) | igual |

---

## 2. Copiar do pendrive

Copie a pasta inteira `E:\Bonsai` para o disco do computador (ex.: `C:\Bonsai` ou `~/Bonsai`).

> Rodar direto do pendrive funciona, mas é bem mais lento para carregar.

---

## 3. Windows — usar

Abra a pasta e dê **dois cliques**:

| Quero… | Clique em |
|---|---|
| Ligar o modelo e conversar no navegador | `iniciar-bonsai.cmd` → abre http://127.0.0.1:8080 |
| Agente **Pi** (mais rápido e leve) | `iniciar-pi-bonsai.cmd` |
| Agente **Hermes** | `iniciar-hermes-bonsai.cmd` |
| Agente **Claude Code** | `iniciar-claude-bonsai.cmd` |
| Painel de monitoramento | `iniciar-monitor.cmd` → http://127.0.0.1:8090 |
| Desligar o modelo | `parar-bonsai.cmd` |

Os agentes ligam o modelo sozinhos, se ele estiver desligado.

**Primeira vez em outro PC:** o Hermes precisa recriar o ambiente Python dele. Abra o PowerShell na pasta e rode, uma única vez (precisa de internet):

```powershell
powershell -ExecutionPolicy Bypass -File .\preparar-hermes.ps1
```

O Claude Code precisa estar instalado no PC (instalador oficial: https://code.claude.com/docs). Pi e Hermes já vão na pasta.

### Opções úteis (PowerShell, na pasta)

```powershell
.\iniciar-bonsai.ps1 -Modelo 2B           # modelo menor e mais rápido, porém menos capaz
.\iniciar-bonsai.ps1 -SemVisao            # economiza ~0,4 GB de RAM (sem leitura de imagens)
.\iniciar-bonsai.ps1 -SomenteLocal        # sem acesso remoto pela rede
.\iniciar-bonsai.ps1 -Perfil original     # volta exatamente à configuração antiga
.\iniciar-claude-bonsai.ps1 -Enxuto       # Claude Code com 6 ferramentas: 1ª resposta ~4x mais rápida
.\iniciar-pi-bonsai.ps1 -Pasta 'C:\meu\projeto'   # trabalhar em outra pasta
```

Antes de trocar de modelo ou perfil, rode `parar-bonsai.cmd`.

---

## 4. Linux — usar

No terminal, dentro da pasta:

```bash
chmod +x linux/*.sh
./linux/setup-linux.sh --com-2b     # uma vez: confere o runtime e os modelos (SHA256)
./linux/iniciar-bonsai.sh           # liga o modelo → http://127.0.0.1:8080
```

O runtime Linux e os modelos já vão no pendrive. O setup só baixa algo se estiver faltando.

| Quero… | Comando |
|---|---|
| Agente Pi | `./linux/iniciar-pi-bonsai.sh ~/meu-projeto` (na 1ª vez roda `npm ci`) |
| Agente Hermes | `./linux/preparar-hermes.sh` (uma vez, precisa de internet) e depois `./linux/iniciar-hermes-bonsai.sh ~/meu-projeto` |
| Agente Claude Code | instale o Claude Code oficial e depois `./linux/iniciar-claude-bonsai.sh ~/meu-projeto` |
| Modelo 2B | `./linux/iniciar-bonsai.sh --modelo 2B` |
| Somente PC local | `./linux/iniciar-bonsai.sh --somente-local` |
| Configuração antiga | `./linux/iniciar-bonsai.sh --perfil original` |
| Desligar | `./linux/parar-bonsai.sh` |

> Em outra CPU, você pode ajustar as threads: `BONSAI_THREADS=4 BONSAI_THREADS_BATCH=6 ./linux/iniciar-bonsai.sh`.

---

## 5. Usar com outros programas (API)

| Campo | Valor |
|---|---|
| URL base (OpenAI) | `http://127.0.0.1:8080/v1` |
| Modelo | `bonsai-2-4b` (ou `bonsai-2-2b`) |
| Chave | `local` (qualquer texto) |

Em outro PC, troque `127.0.0.1` pelo **IP privado do servidor**
(ex.: `192.168.1.100`) e configure o firewall. No Windows, execute
`.\configurar-firewall-lan.ps1` uma vez como Administrador após instalar
o runtime. Essa regra permite TCP/8080 somente para `LocalSubnet`
em rede `Privada`. Consulte [docs/REDE_LOCAL.md](docs/REDE_LOCAL.md).

Para melhores resultados em código e ferramentas, envie `temperature: 0.2` e `presence_penalty: 0`.

---

## 6. O que esperar (medido neste PC: i5-14500T, 16 GB)

- Respostas curtas: começam em menos de 1 segundo e saem a ~18 palavras-token por segundo.
- Ler textos longos é a parte lenta: ~60 tokens/s em textos curtos, ~49 tokens/s com 8 mil tokens.
- O **Pi** é o agente mais rápido: tarefas simples em ~1,5 min. O Claude Code é o mais pesado.
- O Bonsai 4B é um modelo pequeno. Ele resolve bem tarefas pequenas e bem descritas, mas erra contas e lógica com frequência. **Sempre confira o resultado.**

Detalhes e números completos: `RELATORIO_FINAL_BONSAI.md` (ou `.html`).

---

## 7. Problemas comuns

| Sintoma | Solução |
|---|---|
| "porta 8080 ocupada" | Rode `parar-bonsai` e tente de novo. |
| Agente diz "Connection error" | O gateway caiu: rode `iniciar-gateway.ps1` ou `./linux/iniciar-gateway.sh`. |
| PC muito lento ou sem memória | Use `-SemVisao` ou `-Modelo 2B`; feche outros programas. |
| Claude Code demora muitos minutos no 1º passo | Use `-Enxuto`. |
| Ver o que aconteceu | Leia `logs/server.err.log`. |
