param(
    [int]$Porta = 8080,
    [ValidateRange(0,262144)][int]$Contexto = 0,
    [ValidateSet('4B','2B')][string]$Modelo = '4B',
    [ValidateSet('','f16','q8_0','q4_0')][string]$Cache = '',
    # otimizado (auditoria 17/10/2026): KV f16 + 64k + cache de prompts limitado a 2 GB.
    # original: configuracao anterior (262k, KV q4_0, cache de prompts padrao de 8 GB).
    [ValidateSet('otimizado','original')][string]$Perfil = 'otimizado',
    [int]$CacheRamMB = 2048,
    [switch]$SemVisao,
    [switch]$SemNavegador
)
if ($Perfil -eq 'original') { if (-not $Contexto) { $Contexto = 262144 }; if (-not $Cache) { $Cache = 'q4_0' } }
else { if (-not $Contexto) { $Contexto = 65536 }; if (-not $Cache) { $Cache = 'f16' } }
$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$url = "http://127.0.0.1:$Porta"
$pidFile = Join-Path $base 'logs\server.pid'
$modelId = 'bonsai-2-' + $Modelo.ToLowerInvariant()
New-Item -ItemType Directory -Force (Join-Path $base 'logs') | Out-Null
try {
    $health = Invoke-RestMethod "$url/health" -TimeoutSec 2
    $models = Invoke-RestMethod "$url/v1/models" -TimeoutSec 2
    if ($health.status -eq 'ok' -and $modelId -in $models.data.id) {
        $props = Invoke-RestMethod "$url/props" -TimeoutSec 2
        Write-Host "Bonsai ja esta rodando em $url; contexto ativo: $($props.default_generation_settings.n_ctx). Para alterar, execute parar-bonsai.ps1 antes."
        if (-not $SemNavegador) { Start-Process $url }
        exit 0
    }
    throw "A porta $Porta esta ocupada por outro servidor."
} catch {
    if ($_.Exception.Message -like '*ocupada*') { throw }
}
$serverArgs = @(
    '-m', ('"' + (Join-Path $base "models\Ternary-Bonsai-2-$Modelo-PQ2_0.gguf") + '"'),
    '--host', '127.0.0.1', '--port', "$Porta", '--alias', $modelId,
    '-ngl', '0', '-c', "$Contexto", '-np', '1', '-t', '6', '-tb', '8',
    '-b', '256', '-ub', '128', '--cache-type-k', $Cache, '--cache-type-v', $Cache,
    '-fa', 'on', '--jinja', '--temp', '0.7', '--top-p', '0.8', '--top-k', '20',
    '--min-p', '0', '--presence-penalty', '1.5', '--repeat-penalty', '1.0',
    '--repeat-last-n', '64', '--reasoning-budget', '0'
)
if (-not $SemVisao) { $serverArgs += @('--mmproj', ('"' + (Join-Path $base "models\Ternary-Bonsai-2-$Modelo-mmproj-Q8_0.gguf") + '"')) }
if ($Perfil -eq 'otimizado') { $serverArgs += @('--cache-ram', "$CacheRamMB") }
$process = Start-Process -FilePath (Join-Path $base 'bin\llama-server.exe') -ArgumentList $serverArgs -WorkingDirectory $base -WindowStyle Hidden -RedirectStandardOutput (Join-Path $base 'logs\server.out.log') -RedirectStandardError (Join-Path $base 'logs\server.err.log') -PassThru
$process.Id | Set-Content $pidFile
@{
    pid = $process.Id
    context = $Contexto
    model = $modelId
    backend = 'CPU'
    contextCache = $Cache
    cpuThreads = 6
    batchThreads = 8
    batchSize = 256
    microBatchSize = 128
    perfil = $Perfil
    cacheRamMB = $(if ($Perfil -eq 'otimizado') { $CacheRamMB } else { 'padrao (8192)' })
    visao = (-not $SemVisao)
} | ConvertTo-Json | Set-Content (Join-Path $base 'logs\server-config.json')
for ($attempt = 0; $attempt -lt 90; $attempt++) {
    if ($process.HasExited) { throw "Falha ao iniciar. Consulte logs\server.err.log." }
    try {
        $health = Invoke-RestMethod "$url/health" -TimeoutSec 2
        if ($health.status -eq 'ok') {
            Write-Host "Bonsai 2 $Modelo pronto: $url; contexto: $Contexto tokens; cache: $Cache"
            if (-not $SemNavegador) { Start-Process $url }
            exit 0
        }
    } catch { }
    Start-Sleep -Seconds 2
}
throw 'O carregamento demorou mais de 3 minutos. Consulte logs\server.err.log.'
