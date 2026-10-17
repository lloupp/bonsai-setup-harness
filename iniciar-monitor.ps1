param([int]$Porta = 8090, [switch]$SemNavegador)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'iniciar-gateway.ps1')
$url = "http://127.0.0.1:$Porta"
try {
    $state = Invoke-RestMethod "$url/api/state" -TimeoutSec 2
    if ($state.serverUrl -ne 'http://127.0.0.1:8080') { throw 'A porta esta ocupada por outro servidor.' }
    Write-Host "Painel ja esta rodando: $url"
    if (-not $SemNavegador) { Start-Process $url }
    exit 0
} catch {
    if ($_.Exception.Message -like '*ocupada*') { throw }
}
$node = (Get-Command node.exe -ErrorAction Stop).Source
$oldPort = $env:BONSAI_MONITOR_PORT
try {
    $env:BONSAI_MONITOR_PORT = "$Porta"
    $p = Start-Process -FilePath $node -ArgumentList ('"' + (Join-Path $PSScriptRoot 'monitor\server.mjs') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'logs\monitor.out.log') -RedirectStandardError (Join-Path $PSScriptRoot 'logs\monitor.err.log') -PassThru
    $p.Id | Set-Content (Join-Path $PSScriptRoot 'logs\monitor.pid')
} finally { $env:BONSAI_MONITOR_PORT = $oldPort }
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if ($p.HasExited) { throw 'Falha ao iniciar painel. Consulte logs\monitor.err.log.' }
    try {
        $state = Invoke-RestMethod "$url/api/state" -TimeoutSec 2
        Write-Host "Painel Bonsai pronto: $url"
        if (-not $SemNavegador) { Start-Process $url }
        exit 0
    } catch { }
    Start-Sleep -Seconds 1
}
throw 'Painel nao ficou pronto. Consulte logs\monitor.err.log.'
