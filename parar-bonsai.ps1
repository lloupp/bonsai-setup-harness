$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'logs\server.pid'
if (-not (Test-Path $pidFile)) { Write-Host 'Nenhum PID salvo.'; exit 0 }
$serverPid = [int](Get-Content $pidFile -Raw)
$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
$expected = Join-Path $PSScriptRoot 'bin\llama-server.exe'
if ($process -and $process.Path -eq $expected) {
    Stop-Process -Id $serverPid
    Write-Host 'Bonsai encerrado.'
} elseif ($process) {
    throw 'O PID salvo pertence a outro programa; nenhum processo foi encerrado.'
}
Remove-Item -LiteralPath $pidFile -Force
