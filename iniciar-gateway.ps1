$ErrorActionPreference = 'Stop'
$url = 'http://127.0.0.1:8083/health'
try {
    $health = Invoke-RestMethod $url -TimeoutSec 2
    if ($health.service -ne 'bonsai-client-gateway') { throw 'Porta 8083 ocupada por outro servidor.' }
    return
} catch { if ($_.Exception.Message -like '*ocupada*') { throw } }
$node = (Get-Command node.exe -ErrorAction Stop).Source
$process = Start-Process -FilePath $node -ArgumentList ('"' + (Join-Path $PSScriptRoot 'monitor\gateway.mjs') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'logs\gateway.out.log') -RedirectStandardError (Join-Path $PSScriptRoot 'logs\gateway.err.log') -PassThru
$process.Id | Set-Content (Join-Path $PSScriptRoot 'logs\gateway.pid')
for ($attempt=0; $attempt -lt 20; $attempt++) {
    try { $health = Invoke-RestMethod $url -TimeoutSec 1; if ($health.service -eq 'bonsai-client-gateway') { return } } catch { }
    Start-Sleep -Milliseconds 250
}
throw 'Gateway nao iniciou. Consulte logs/gateway.err.log.'
