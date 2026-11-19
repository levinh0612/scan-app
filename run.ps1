# =============================================================================
# run.ps1 - cài đặt, cập nhật và chạy server quét giấy tờ (Windows 10/11)
#
#   B1. Tải tài nguyên cần thiết (git, Python >= 3.10, VC++ runtime, venv, thư viện)
#   B2. Pull code mới từ GitHub
#   B3. Kiểm tra (cú pháp, test, import) - lỗi thì hoàn tác code, KHÔNG đụng server đang chạy
#   B4. Start nếu chưa chạy, restart nếu đang chạy (kèm health check, lỗi thì quay về bản cũ)
#
# Dùng:  .\run.cmd                 (bấm đúp cũng được)
#        .\run.cmd -NoPull         (bỏ B2)
#        .\run.cmd -Tunnel         (thêm link https công khai cho điện thoại; cần cloudflared)
#        .\run.cmd                 (không tham số: hiện menu chọn)
#        .\run.cmd -Open          (xong thì mở trình duyệt; icon ngoài Desktop dùng cách này)
#        .\run.cmd -Auto           (chế độ tự động: chỉ restart khi có code mới - dùng cho Task Scheduler)
# Dừng:  .\stop.cmd
# =============================================================================
[CmdletBinding()]
param([switch]$NoPull, [switch]$Auto, [switch]$Tunnel, [switch]$Https, [switch]$Open, [int]$Port = 8000)

$ErrorActionPreference = 'Continue'   # lệnh native ghi stderr không làm script chết; ta tự kiểm $LASTEXITCODE
Set-Location -LiteralPath $PSScriptRoot
if ($env:PORT) { $Port = [int]$env:PORT }
# server đang chạy ở cổng đã tự chọn lần trước → dùng lại cổng đó cho kiểm tra sức khoẻ
$pf = Join-Path $PSScriptRoot '.run\port'; $sp = Join-Path $PSScriptRoot '.run\server.pid'
if ((Test-Path $pf) -and (Test-Path $sp) -and (Get-Process -Id ([int](Get-Content $sp)) -ErrorAction SilentlyContinue)) { $Port = [int](Get-Content $pf) }

# ---- Menu chọn (chỉ khi chạy tay, không tham số, có cửa sổ tương tác) ----
if ($PSBoundParameters.Count -eq 0 -and [Environment]::UserInteractive -and -not [Console]::IsInputRedirected) {
    Write-Host ''
    Write-Host '  QUÉT GIẤY TỜ - chọn cách chạy'
    Write-Host '   1) Chạy đầy đủ            (cập nhật code từ GitHub, kiểm tra, chạy)'
    Write-Host '   2) Chạy, không cập nhật   (nhanh, dùng code hiện có)'
    Write-Host '   3) Chạy + link https      (điện thoại dùng được camera; cần cloudflared)'
    Write-Host '   4) Dừng server'
    Write-Host '   0) Thoát'
    $c = Read-Host '  Chọn [1]'
    if (-not $c) { $c = '1' }
    switch ($c) {
        '1' { }
        '2' { $NoPull = [switch]$true }
        '3' { $NoPull = [switch]$true; $Tunnel = [switch]$true }
        '4' { & (Join-Path $PSScriptRoot 'stop.ps1'); exit 0 }
        '0' { exit 0 }
        default { Write-Host 'Lựa chọn không hợp lệ.'; exit 2 }
    }
}

$RunDir  = Join-Path $PSScriptRoot '.run'
$LogDir  = Join-Path $PSScriptRoot 'logs'
$PidFile = Join-Path $RunDir 'server.pid'
$LogOut  = Join-Path $LogDir 'server.log'
$LogErr  = Join-Path $LogDir 'server.err.log'
$VenvPy  = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null

function Log($m)  { Write-Host ('[{0}] {1}' -f (Get-Date -Format HH:mm:ss), $m) -ForegroundColor Cyan }
function Warn($m) { Write-Host "[CẢNH BÁO] $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "[LỖI] $m" -ForegroundColor Red; exit 1 }
function Have($n) { [bool](Get-Command $n -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Winget-Install($id) {
    if (-not (Have 'winget')) {
        Die "Máy chưa có winget. Hãy cài tay '$id' (git: https://git-scm.com, Python: https://www.python.org/downloads) rồi chạy lại."
    }
    Log "winget cài $id ..."
    winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
}
function Find-Python {
    $cands = @(@('py', '-3.13'), @('py', '-3.12'), @('py', '-3.11'), @('py', '-3.10'), @('python'), @('python3'))
    foreach ($c in $cands) {
        if (-not (Have $c[0])) { continue }
        $extra = @(); if ($c.Count -gt 1) { $extra += $c[1] }
        try {
            $out = & $c[0] @extra -c "import sys; sys.exit(1) if sys.version_info<(3,10) else print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) { return ($out | Select-Object -First 1) }
        } catch { }
    }
    return $null
}
function Has-VcRuntime {
    $k = 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64'
    (Test-Path $k) -and ((Get-ItemProperty $k -ErrorAction SilentlyContinue).Installed -eq 1)
}
function Is-Admin {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}
function Ensure-Firewall {
    $name = "ScanApp $Port"
    if (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue) { return }
    if (Is-Admin) {
        New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow -Profile Private, Domain | Out-Null
        Log "Đã mở cổng $Port trong Windows Firewall (mạng Private)."
    } else {
        Warn "Chưa mở firewall nên điện thoại có thể không vào được. Chạy PowerShell bằng quyền Administrator và chạy lại .\run.cmd một lần."
    }
}
function Sync-Deps {
    $want = (Get-FileHash -Path (Join-Path $PSScriptRoot 'requirements.txt') -Algorithm SHA256).Hash
    $shaFile = Join-Path $PSScriptRoot '.venv\.req.sha'
    $have = ''; if (Test-Path $shaFile) { $have = (Get-Content $shaFile -Raw).Trim() }
    if ($want -eq $have) { Log 'Thư viện đã đủ, bỏ qua.'; return }
    Log 'Cài thư viện (lần đầu có thể mất vài phút nếu mạng chậm)...'
    & $VenvPy -m pip install --default-timeout 60 --retries 5 -q -r (Join-Path $PSScriptRoot 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { Die 'Cài thư viện thất bại (kiểm tra mạng rồi chạy lại).' }
    Set-Content -Path $shaFile -Value $want -NoNewline
}
function Is-Running {
    if (-not (Test-Path $PidFile)) { return $false }
    $id = [int](Get-Content $PidFile -ErrorAction SilentlyContinue)
    [bool](Get-Process -Id $id -ErrorAction SilentlyContinue)
}
$Scheme = if ($Https) { 'https' } else { 'http' }
if ($Https) { [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } }   # chỉ để tự kiểm tra cert tự ký của chính mình
function Health-Ok {
    try { (Invoke-WebRequest -Uri "${Scheme}://127.0.0.1:$Port/api/health" -UseBasicParsing -TimeoutSec 3).StatusCode -eq 200 }
    catch { $false }
}
function Start-Server {
    if (-not (Is-Running)) {   # cổng bận bởi chương trình khác → tự chọn cổng trống kế tiếp (tối đa 30 cổng)
        $want = $script:Port; $n = 0
        while ((Get-NetTCPConnection -LocalPort $script:Port -State Listen -ErrorAction SilentlyContinue) -and $n -lt 30) { $script:Port++; $n++ }
        if (Get-NetTCPConnection -LocalPort $script:Port -State Listen -ErrorAction SilentlyContinue) { Die "Không tìm được cổng trống từ $want." }
        if ($script:Port -ne $want) { Warn "Cổng $want đang bị chương trình khác dùng → dùng cổng $($script:Port)."; Ensure-Firewall }
    }
    Set-Content -Path (Join-Path $RunDir 'port') -Value $script:Port -NoNewline
    $args2 = @('-m', 'uvicorn', 'app:app', '--app-dir', 'backend', '--host', '0.0.0.0', '--port', "$Port")
    if ($Https) {
        $ipc = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
               Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|Virtual|VMware|Bluetooth' -and $_.IPAddress -notlike '169.254.*' } |
               Select-Object -First 1 -ExpandProperty IPAddress
        $cert = & $VenvPy (Join-Path $PSScriptRoot 'backend\make_cert.py') "$ipc"
        if ($LASTEXITCODE -ne 0 -or $cert.Count -lt 2) { Die 'Không tạo được chứng chỉ https (thiếu thư viện cryptography?)' }
        $args2 += @('--ssl-certfile', $cert[0], '--ssl-keyfile', $cert[1])
    }
    $p = Start-Process -FilePath $VenvPy -ArgumentList $args2 -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru `
         -RedirectStandardOutput $LogOut -RedirectStandardError $LogErr
    Set-Content -Path $PidFile -Value $p.Id
    for ($i = 0; $i -lt 30; $i++) {
        if (Health-Ok) { return $true }
        if ($p.HasExited) { return $false }
        Start-Sleep -Seconds 1
    }
    return $false
}
function Stop-Server { & (Join-Path $PSScriptRoot 'stop.ps1') | Out-Null }

# =============================================================================
Log 'B1. Chuẩn bị tài nguyên'
# =============================================================================
if (-not (Have 'git')) { Winget-Install 'Git.Git'; if (-not (Have 'git')) { Die 'Đã cài git nhưng chưa nhận ra. Đóng cửa sổ này, mở lại và chạy lại.' } }
if (-not (Has-VcRuntime)) { Winget-Install 'Microsoft.VCRedist.2015+.x64' }   # onnxruntime/opencv cần

$Py = Find-Python
if (-not $Py) {
    Log 'Chưa có Python >= 3.10, đang cài...'
    Winget-Install 'Python.Python.3.13'
    $Py = Find-Python
    if (-not $Py) { Die 'Đã cài Python nhưng chưa nhận ra. Đóng cửa sổ này, mở lại và chạy lại.' }
}
Log ("Python: " + (& $Py --version) + " ($Py)")

if (-not (Test-Path $VenvPy)) {
    Log 'Tạo môi trường ảo .venv'
    & $Py -m venv (Join-Path $PSScriptRoot '.venv')
    if (-not (Test-Path $VenvPy)) { Die 'Không tạo được .venv' }
}
Sync-Deps
Ensure-Firewall

# =============================================================================
Log 'B2. Pull code'
# =============================================================================
$PrevCommit = ''; $Pulled = $false
git remote get-url origin *> $null
$HasRemote = ($LASTEXITCODE -eq 0) -and (Test-Path (Join-Path $PSScriptRoot '.git'))
if ($NoPull) {
    Log 'Bỏ qua pull (-NoPull).'
} elseif (-not $HasRemote) {
    Warn "Thư mục chưa phải git repo hoặc chưa có remote 'origin' → bỏ qua pull."
} elseif (git status --porcelain --untracked-files=no) {
    Warn 'Có thay đổi chưa commit trong thư mục → bỏ qua pull để không ghi đè.'
} else {
    $PrevCommit = (git rev-parse HEAD).Trim()
    $Branch = (git branch --show-current).Trim()
    git fetch --quiet origin
    if ($LASTEXITCODE -ne 0) { Warn 'Không fetch được từ GitHub (mạng/đăng nhập?) → dùng code hiện có.' }
    else {
        git rev-parse --abbrev-ref '@{u}' *> $null
        if ($LASTEXITCODE -eq 0) { git pull --ff-only --quiet } else { git pull --ff-only --quiet origin $Branch }
        if ($LASTEXITCODE -ne 0) { Die 'git pull thất bại (nhánh bị lệch?). Hãy báo người phát triển.' }
        $NewCommit = (git rev-parse HEAD).Trim()
        if ($PrevCommit -eq $NewCommit) { Log ('Đã là bản mới nhất (' + (git rev-parse --short HEAD).Trim() + ').') }
        else {
            $Pulled = $true
            Log ('Cập nhật ' + (git rev-parse --short $PrevCommit).Trim() + ' → ' + (git rev-parse --short $NewCommit).Trim())
            Sync-Deps
        }
    }
}
function Rollback-Code {
    if ($Pulled -and $PrevCommit) {
        Warn ('Hoàn tác code về ' + (git rev-parse --short $PrevCommit).Trim())
        git reset --hard --quiet $PrevCommit
        $script:Pulled = $false
        Sync-Deps
    }
}

# Chế độ tự động (Task Scheduler): không có gì mới và server khỏe thì thôi, không restart vô ích
$CommitFile = Join-Path $RunDir 'server.commit'
$Head = if (Test-Path (Join-Path $PSScriptRoot '.git')) { (git rev-parse HEAD 2>$null | Out-String).Trim() } else { '' }
$Stale = $Head -and (Test-Path $CommitFile) -and ((Get-Content $CommitFile -Raw).Trim() -ne $Head)   # code trên đĩa mới hơn code đang chạy
if ($Auto -and -not $Pulled -and -not $Stale -and (Is-Running) -and (Health-Ok)) { Log 'Auto: không có thay đổi, server đang chạy tốt.'; exit 0 }
# Hàng đợi lệnh in nằm trong RAM: restart sẽ mất. Còn lệnh Chờ in / Đang in thì hoãn, lần chạy sau thử lại.
if ($Auto -and (Is-Running) -and (Health-Ok)) {
    try {
        $busy = @((Invoke-RestMethod -Uri "${Scheme}://127.0.0.1:$Port/api/jobs" -TimeoutSec 5) | Where-Object { $_.status -in 'cho_in', 'dang_in' }).Count
        if ($busy -gt 0) { Warn "Có $busy lệnh in chưa xong → hoãn cập nhật, thử lại sau."; exit 0 }
    } catch { }
}

# =============================================================================
Log 'B3. Kiểm tra'
# =============================================================================
& $VenvPy (Join-Path $PSScriptRoot 'backend\selfcheck.py')
if ($LASTEXITCODE -ne 0) {
    Rollback-Code
    Die 'Kiểm tra thất bại. Server đang chạy (nếu có) KHÔNG bị thay đổi.'
}
Log 'Kiểm tra đạt.'

# =============================================================================
Log 'B4. Khởi động'
# =============================================================================
if (Is-Running) { Log ('Server đang chạy (PID ' + (Get-Content $PidFile) + ') → restart'); Stop-Server }
else { Log 'Server chưa chạy → start' }

if (-not (Start-Server)) {
    Warn 'Server không lên được. Log lỗi cuối:'
    if (Test-Path $LogErr) { Get-Content $LogErr -Tail 20 }
    Stop-Server
    if ($Pulled) {
        Rollback-Code
        Log 'Thử chạy lại bản cũ...'
        if (Start-Server) { Die 'Bản mới lỗi, đã quay về bản cũ và đang chạy. Xem logs\server.err.log' }
        Die 'Cả bản cũ cũng không chạy. Xem logs\server.err.log'
    }
    Die 'Không khởi động được. Xem logs\server.err.log'
}

if ($Head) { Set-Content -Path $CommitFile -Value $Head -NoNewline }
$ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
      Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|Virtual|VMware|Bluetooth' -and $_.IPAddress -notlike '169.254.*' } |
      Select-Object -First 1 -ExpandProperty IPAddress
Log ('Server đang chạy (PID ' + (Get-Content $PidFile) + ')')
Write-Host "   Máy này     : ${Scheme}://localhost:$Port"
$QrArgs = @()
if ($ip) { Write-Host "   Điện thoại  : ${Scheme}://${ip}:$Port   (cùng wifi)"; $QrArgs += "Cùng wifi=${Scheme}://${ip}:$Port"; if ($Https) { Write-Host "   (lần đầu điện thoại báo `"không an toàn`": bấm Nâng cao → Tiếp tục)" } }
if ($Tunnel) {
    if (-not (Have 'cloudflared')) {
        Warn 'Chưa có cloudflared nên không tạo được link https. Cài: winget install Cloudflare.cloudflared'
    } else {
        $TunLog = Join-Path $LogDir 'tunnel.log'
        Remove-Item $TunLog -Force -ErrorAction SilentlyContinue
        $tp = Start-Process cloudflared -ArgumentList $(if ($Https) { @('tunnel', '--no-tls-verify', '--url', "https://localhost:$Port") } else { @('tunnel', '--url', "http://localhost:$Port") }) -WindowStyle Hidden -PassThru -RedirectStandardError $TunLog
        $tp.Id | Set-Content (Join-Path $RunDir 'tunnel.pid')
        $url = $null
        for ($i = 0; $i -lt 30 -and -not $url; $i++) {
            Start-Sleep -Seconds 1
            if (Test-Path $TunLog) { $m = Select-String -Path $TunLog -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1; if ($m) { $url = $m.Matches[0].Value } }
        }
        if ($url) {   # tên miền hiện trong log trước khi truy cập được -> chờ tới khi thật sự trả lời
            for ($i = 0; $i -lt 60; $i++) {
                try { Invoke-WebRequest -Uri "$url/api/health" -UseBasicParsing -TimeoutSec 4 | Out-Null; break } catch { Start-Sleep -Seconds 1 }
            }
        }
        if ($url) { Write-Host "   Điện thoại  : $url   (https, dùng được camera, mở bằng Safari/Chrome - KHÔNG có mật khẩu, chỉ gửi người tin cậy)"; $QrArgs += "Link https=$url" }
        else { Warn 'Chưa lấy được link https, xem logs\tunnel.log' }
    }
}
if ($QrArgs.Count -gt 0) { try { Write-Host ''; & $VenvPy (Join-Path $PSScriptRoot 'backend\qr_print.py') @QrArgs; Write-Host '' } catch { } }   # QR quét bằng điện thoại, xếp cạnh nhau
Write-Host '   Log         : logs\server.log, logs\server.err.log      Dừng: .\stop.cmd'
if ($Open) { Start-Process $(if ($Https) { "https://localhost:$Port/" } else { "http://localhost:$Port/" }) }   # icon Desktop: mở giao diện (đầu trang có QR cho điện thoại)
