# Prepara o Bonsai no Windows x64: baixa o runtime oficial PrismML (CPU) e os modelos que faltarem, conferindo SHA256.
# Uso: powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1 [-Com2B]
param([switch]$Com2B)
$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$tag = 'prism-b10777-e3de715'
$asset = "llama-$tag-bin-win-cpu-x64.zip"
$assetSha = 'cff7eeff19163e6263720618cf98023715b8dac14d0873f5be0918765de323c4'
$models = @(
    @{f='Ternary-Bonsai-2-4B-PQ2_0.gguf'; r='Ternary-Bonsai-2-4B-gguf'; s='d406b1e912c0d2a4c124ad10bf38a76ae662fdc4d24b176451403dc7b7f30409'},
    @{f='Ternary-Bonsai-2-4B-mmproj-Q8_0.gguf'; r='Ternary-Bonsai-2-4B-gguf'; s='db939d5f9b7014137810205e91d05e5f54afd72b0b3af9d33bd7d82f7906a55d'},
    @{f='Ternary-Bonsai-2-2B-PQ2_0.gguf'; r='Ternary-Bonsai-2-2B-gguf'; s='d5f01a4ecaf49239653308ee732ad1a0c5f802c0ddb997549fc7b694c8b45928'},
    @{f='Ternary-Bonsai-2-2B-mmproj-Q8_0.gguf'; r='Ternary-Bonsai-2-2B-gguf'; s='ac9934e8d7966d0d62442c202ec8fdad99a045dea79366c1a4a246a46f5c0533'}
)
function Test-Sha($path, $sha) { (Test-Path -LiteralPath $path) -and ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -eq $sha) }
$ProgressPreference = 'SilentlyContinue'
New-Item -ItemType Directory -Force (Join-Path $base 'bin'), (Join-Path $base 'models'), (Join-Path $base 'logs') | Out-Null
$server = Join-Path $base 'bin\llama-server.exe'
if (-not (Test-Path $server)) {
    $zip = Join-Path $base "bin\$asset"
    if (-not (Test-Sha $zip $assetSha)) {
        Write-Host "Baixando runtime $asset ..."
        Invoke-WebRequest "https://github.com/PrismML-Eng/llama.cpp/releases/download/$tag/$asset" -OutFile $zip
    }
    if (-not (Test-Sha $zip $assetSha)) { throw "SHA256 do runtime nao confere: $zip" }
    Expand-Archive -LiteralPath $zip -DestinationPath (Join-Path $base 'bin') -Force
    $found = Get-ChildItem (Join-Path $base 'bin') -Recurse -Filter llama-server.exe | Select-Object -First 1
    if ($found.DirectoryName -ne (Join-Path $base 'bin')) { Copy-Item (Join-Path $found.DirectoryName '*') (Join-Path $base 'bin') -Recurse -Force }
}
foreach ($m in $models) {
    if ($m.f -like '*2B*' -and -not $Com2B) { continue }
    $dest = Join-Path $base "models\$($m.f)"
    if (Test-Sha $dest $m.s) { Write-Host "OK $($m.f)"; continue }
    Write-Host "Baixando $($m.f) ..."
    Invoke-WebRequest "https://huggingface.co/prism-ml/$($m.r)/resolve/main/$($m.f)" -OutFile "$dest.part"
    if (-not (Test-Sha "$dest.part" $m.s)) { Remove-Item "$dest.part"; throw "SHA256 nao confere: $($m.f)" }
    Move-Item -Force "$dest.part" $dest
}
$ErrorActionPreference = 'Continue'
& cmd.exe /c "`"$server`" --version 2>&1" | Select-Object -Last 2
Write-Host 'Pronto. Inicie com iniciar-bonsai.cmd'
