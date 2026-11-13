$ErrorActionPreference = 'Stop'
$easelRoot = $PSScriptRoot
$easelUrl = 'http://127.0.0.1:7860'
$env:PYTHONUTF8 = '1'
$env:EASEL_PORT = '7860'
# Prefer the CLI shipped with the desktop app over an older global npm shim.
# This changes PATH for xh and its children only.
$easelCodexBin = Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin'
$easelBundledCodex = Get-ChildItem -LiteralPath $easelCodexBin -Filter 'codex.exe' -Recurse -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($easelBundledCodex) { $env:Path = $easelBundledCodex.DirectoryName + ';' + $env:Path }
function Test-EaselReady {
    try {
        $response = Invoke-WebRequest -Uri ($easelUrl + '/api/status') -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -eq 200 -and ($response.Content | ConvertFrom-Json).runtime)
    } catch { return $false }
}
if (-not (Test-EaselReady)) {
    $easelPython = Join-Path $easelRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $easelPython)) { throw 'xh 运行环境缺失。' }
    $easelLogs = Join-Path $easelRoot 'outputs\_local'
    New-Item -ItemType Directory -Path $easelLogs -Force | Out-Null
    $easelProcess = Start-Process -FilePath $easelPython -ArgumentList @(
        '-m', 'uvicorn', 'web.app:app', '--host', '127.0.0.1', '--port', '7860'
    ) -WorkingDirectory $easelRoot -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $easelLogs 'web.log') `
        -RedirectStandardError (Join-Path $easelLogs 'web.err.log')
    $easelProcess.Id | Set-Content -LiteralPath (Join-Path $easelLogs 'web.pid')
    $easelReady = $false
    for ($easelAttempt = 0; $easelAttempt -lt 30; $easelAttempt++) {
        if (Test-EaselReady) { $easelReady = $true; break }
        if ($easelProcess.HasExited) { break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $easelReady) { throw ('xh 未能启动，请检查日志：' + $easelLogs) }
}
Start-Process $easelUrl
