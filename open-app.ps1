# open-app.ps1 - icon "ScanApp" (cho người dùng): chưa chạy thì bật server ngầm, rồi mở app trên trình duyệt. Không hiện cửa sổ lệnh.
Set-Location -LiteralPath $PSScriptRoot
Add-Type -AssemblyName System.Windows.Forms
try { [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } } catch { }   # chứng chỉ tự ký trên chính máy này
function Get-Url {
    $p = 8000; $pf = Join-Path $PSScriptRoot '.run\port'
    if (Test-Path $pf) { $p = [int](Get-Content $pf) }
    foreach ($s in 'http', 'https') {
        try { if ((Invoke-WebRequest -Uri "${s}://127.0.0.1:$p/api/health" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200) { return "${s}://localhost:$p/" } } catch { }
    }
    return $null
}
$url = Get-Url
if (-not $url) {
    New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'logs') | Out-Null
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'run.ps1'), '-Auto' `
        -RedirectStandardOutput (Join-Path $PSScriptRoot 'logs\launcher.log') -RedirectStandardError (Join-Path $PSScriptRoot 'logs\launcher.err.log')
    for ($i = 0; $i -lt 90 -and -not $url; $i++) { Start-Sleep -Seconds 2; $url = Get-Url }
}
if ($url) { Start-Process $url }
else { [void][System.Windows.Forms.MessageBox]::Show("ScanApp chưa chạy được.`nMở 'ScanApp - Cài đặt' để xem lỗi (hoặc logs\launcher.log).", 'ScanApp') }
