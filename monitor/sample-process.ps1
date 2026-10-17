param([int]$ServerPid)
$ErrorActionPreference = 'Stop'
$p = Get-Process -Id $ServerPid -ErrorAction SilentlyContinue
$expected = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\bin\llama-server.exe'))
if (-not $p -or $p.Path -ne $expected) { Write-Output 'null'; exit 0 }
[pscustomobject]@{
    pid = $p.Id
    workingSet = $p.WorkingSet64
    privateBytes = $p.PrivateMemorySize64
    cpuSeconds = $p.TotalProcessorTime.TotalSeconds
    startedAt = $p.StartTime.ToUniversalTime().ToString('o')
    threads = $p.Threads.Count
    sampledAt = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
} | ConvertTo-Json -Compress
