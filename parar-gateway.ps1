$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'logs\gateway.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'Sem PID de gateway registrado.'; return }
$savedPid = [int](Get-Content -LiteralPath $pidFile -Raw)
$health = Invoke-RestMethod http://127.0.0.1:8083/health -TimeoutSec 2
if ($health.service -ne 'bonsai-client-gateway' -or $health.pid -ne $savedPid) { throw 'PID nao corresponde ao gateway Bonsai.' }
Stop-Process -Id $savedPid
Remove-Item -LiteralPath $pidFile
Write-Host 'Gateway encerrado. Agentes identificados precisam dele para fazer novas chamadas.'
