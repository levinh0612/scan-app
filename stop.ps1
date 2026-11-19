# stop.ps1 - dừng server (Windows)
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot
$Port = 8000; if ($env:PORT) { $Port = [int]$env:PORT }
if (Test-Path (Join-Path $PSScriptRoot '.run\port')) { $Port = [int](Get-Content (Join-Path $PSScriptRoot '.run\port')) }
$PidFile = Join-Path $PSScriptRoot '.run\server.pid'
$stopped = $false

function Kill-Tree($id) {
    if (Get-Process -Id $id -ErrorAction SilentlyContinue) {
        Write-Host "Dừng server (PID $id)..."
        & taskkill.exe /PID $id /T /F *> $null
        Start-Sleep -Milliseconds 500
        return $true
    }
    return $false
}

$TunPid = Join-Path $PSScriptRoot '.run\tunnel.pid'   # tắt tunnel https (nếu run -Tunnel đã mở)
if (Test-Path $TunPid) {
    $tid = [int](Get-Content $TunPid -ErrorAction SilentlyContinue)
    if ($tid) { & taskkill.exe /PID $tid /T /F *> $null }
    Remove-Item $TunPid -Force -ErrorAction SilentlyContinue
}

if (Test-Path $PidFile) {
    $id = [int](Get-Content $PidFile -ErrorAction SilentlyContinue)
    if ($id -and (Kill-Tree $id)) { $stopped = $true }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

# Dự phòng: tiến trình uvicorn của app này vẫn giữ cổng (vd mất pid file)
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmd -match 'uvicorn') { if (Kill-Tree $_.OwningProcess) { $stopped = $true } }
}

if ($stopped) { Write-Host 'Đã dừng.' } else { Write-Host 'Server không chạy.' }
exit 0
