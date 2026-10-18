# Acesso ao Bonsai pela rede local (padrao)

Por padrao, **Windows** (`iniciar-bonsai.ps1` e `iniciar-bonsai.cmd`)
e **Linux** (`./linux/iniciar-bonsai.sh`) iniciam o `llama-server`
com `--host 0.0.0.0 --port 8080`. O endereco 0.0.0.0 significa
escuta em todas as interfaces IPv4; **nao** e o endereco a configurar no cliente.

A API **nao exige autenticacao** neste projeto; o valor `local`
e apenas uma chave ficticia aceita por alguns clientes. **Nao use em
Wi-Fi publico, redes nao confiaveis, nem publique a porta na Internet.**
O firewall precisa limitar o acesso a dispositivos de confianca na LAN.
Se preferir nao expor, inicie com `-SomenteLocal` (Windows) ou
`--somente-local` (Linux) para voltar a `127.0.0.1`.

## Windows (PC servidor)

```powershell
.\iniciar-bonsai.ps1 -SemNavegador
ipconfig
```

**Uma vez, com PowerShell como administrador**, execute, depois do
`setup-windows.ps1`:

```powershell
.\configurar-firewall-lan.ps1
```

O auxiliar cria uma regra de **entrada TCP/8080** limitada a perfil de
rede **Privado**, origem **LocalSubnet** e ao executavel
`bin\llama-server.exe`. Redes marcadas `Publico` nao recebem
permissao desta regra. Se usar `-Porta 8081` no servidor, passe
`-Porta 8081` ao auxiliar. Revise regras existentes que possam
permitir acesso mais amplo; o auxiliar nao as revoga.

Se a rede Windows estiver marcada como Publica, ajuste-a para Privada
**somente se for uma rede de confianca**. Nao abra regra de perfil Publico.

## Linux Mint (PC servidor)

```bash
./linux/iniciar-bonsai.sh
hostname -I
```

Se o UFW estiver ativo, libere **somente a faixa real da sua LAN**;
exemplo ilustrativo para uma rede 192.168.1.0/24:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8080 proto tcp
sudo ufw status
```

Substitua a faixa ilustrativa pela sub-rede correta; nao use
`sudo ufw allow 8080` indiscriminadamente. Mantenha outras
interfaces/regras externas bloqueadas. Se o UFW estiver desativado,
verifique as politicas reais de firewall antes de habilitar acesso.

## Outro PC (cliente)

Use **o IP privado do PC servidor**, obtido nos comandos anteriores.
Exemplo com IP ficticio `192.168.1.100`:

| Campo | Valor |
|---|---|
| OpenAI Base URL | `http://192.168.1.100:8080/v1` |
| Modelo | `bonsai-2-4b` ou `bonsai-2-2b` (o que esta ativo) |
| API Key | `local` (nao protege o servidor) |

Testes de conectividade:

```bash
curl http://192.168.1.100:8080/health
curl http://192.168.1.100:8080/v1/models
```

No Windows cliente, tambem pode usar `Invoke-RestMethod` nos mesmos
enderecos. Se nao conectar: teste ping/conectividade entre os PCs,
verifique IP, perfil de rede, isolamento Wi-Fi de clientes, firewall
e se o Bonsai foi **reiniciado** apos esta alteracao.

No proprio PC servidor, os clientes locais continuam usando
`http://127.0.0.1:8080/v1`. O gateway de identificacao (porta 8083)
e o painel (porta 8090) continuam **somente locais**; este modo de
rede nao compartilha essas interfaces nem adapta automaticamente
o protocolo Anthropic do Claude Code.

## Reverter (modo somente local)

```powershell
.\parar-bonsai.ps1
.\iniciar-bonsai.ps1 -SomenteLocal
```

```bash
./linux/parar-bonsai.sh
./linux/iniciar-bonsai.sh --somente-local
```

A escuta na rede nao cria autenticação, criptografia, quotas ou
isolamento de clientes. Cada requisicao remota consome CPU e memoria
do PC servidor. Utilize somente em uma LAN privada e confiavel.
