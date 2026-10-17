# Inicia o llama-server com argumentos de experimento na porta 8080 (para comparacao com o baseline).
# Uso: .\srv-experimento.ps1 -Rotulo nome -Extra '-c 65536 --cache-type-k f16 ...'
param([Parameter(Mandatory)][string]$Rotulo, [string]$Extra = '', [switch]$SemVisao)
$ErrorActionPreference = 'Stop'
$base = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$pidFile = Join-Path $base 'logs\server.pid'
if (Test-Path $pidFile) { & (Join-Path $base 'parar-bonsai.ps1') | Out-Null; Start-Sleep 2 }
$args0 = @('-m', ('"' + (Join-Path $base 'models\Ternary-Bonsai-2-4B-PQ2_0.gguf') + '"'))
if (-not $SemVisao) { $args0 += @('--mmproj', ('"' + (Join-Path $base 'models\Ternary-Bonsai-2-4B-mmproj-Q8_0.gguf') + '"')) }
$args0 += @('--host','127.0.0.1','--port','8080','--alias','bonsai-2-4b','-ngl','0','-np','1','-fa','on','--jinja',
            '--temp','0.7','--top-p','0.8','--top-k','20','--min-p','0','--presence-penalty','1.5','--reasoning-budget','0')
$args0 += ($Extra -split '\s+' | Where-Object { $_ })
$log = Join-Path $base "logs\server.err.log"
$p = Start-Process -FilePath (Join-Path $base 'bin\llama-server.exe') -ArgumentList $args0 -WorkingDirectory $base -WindowStyle Hidden -RedirectStandardOutput (Join-Path $base 'logs\server.out.log') -RedirectStandardError $log -PassThru
$p.Id | Set-Content $pidFile
$sw = [Diagnostics.Stopwatch]::StartNew()
for ($i = 0; $i -lt 90; $i++) {
    if ($p.HasExited) { throw 'Falha ao iniciar; veja logs\server.err.log' }
    try { if ((Invoke-RestMethod 'http://127.0.0.1:8080/health' -TimeoutSec 2).status -eq 'ok') { break } } catch { }
    Start-Sleep -Milliseconds 500
}
Write-Host "Experimento $Rotulo pronto em $([int]$sw.Elapsed.TotalSeconds)s. Args: $($args0 -join ' ')"
