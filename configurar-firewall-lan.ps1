# Execute UMA vez em PowerShell como Administrador no PC servidor.
# Autoriza somente dispositivos da sub-rede local em perfil de rede Privado.
param([ValidateRange(1,65535)][int]$Porta = 8080)
$ErrorActionPreference = 'Stop'
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Abra o PowerShell como Administrador para configurar o firewall.'
}
$exe = Join-Path $PSScriptRoot 'bin\llama-server.exe'
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Runtime nao encontrado: $exe. Execute setup-windows.ps1 antes."
}
$ruleName = "Bonsai-LAN-TCP-$Porta"
$existing = Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Remove-NetFirewallRule -Name $ruleName
}
New-NetFirewallRule -Name $ruleName -DisplayName "Bonsai - LAN privada ($Porta)" `
    -Direction Inbound -Action Allow -Enabled True -Profile Private `
    -Protocol TCP -LocalPort $Porta -Program $exe -RemoteAddress LocalSubnet | Out-Null
Write-Host "Regra criada: TCP $Porta, somente perfil Privado, origem LocalSubnet e programa $exe"
Write-Host 'Nao configure redirecionamento de portas no roteador. Confirme que a rede Windows esta como Privada.'
Write-Warning 'Esta regra NAO revoga outras regras mais permissivas ja existentes para o mesmo processo/porta.'
