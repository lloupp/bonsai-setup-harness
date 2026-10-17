$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'logs\monitor.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host 'Nenhum PID do painel salvo.'; exit 0 }
$monitorPid = [int](Get-Content -LiteralPath $pidFile -Raw)
$process = Get-Process -Id $monitorPid -ErrorAction SilentlyContinue
if (-not $process) { Write-Host 'Painel ja encerrado.'; exit 0 }
$state = Invoke-RestMethod 'http://127.0.0.1:8090/api/state' -TimeoutSec 3
if ($state.monitorPid -ne $monitorPid) { throw 'O processo nao corresponde ao painel atual; nada foi encerrado.' }
Stop-Process -Id $monitorPid
Remove-Item -LiteralPath $pidFile
Write-Host 'Painel encerrado. O modelo Bonsai continua rodando.'
