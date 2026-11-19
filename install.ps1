# install.ps1 - cài chạy tự động trên Windows 10/11 (chạy MỘT lần, bằng quyền Administrator)
#   Việc làm:  kiểm tra Windows, cài môi trường + chạy thử, mở firewall (mạng riêng),
#              tạo 2 tác vụ: ScanApp (bật máy là chạy) và ScanApp-Update (30 phút kiểm tra bản mới từ GitHub)
# Dùng:  bấm đúp Cai-Dat.cmd   (chọn Yes khi Windows hỏi quyền)
#        Cai-Dat.cmd -Port 8000 -Https -Token   (-Https: thêm https tự ký thay cho link internet; -Token: mã GitHub chỉ-đọc cho repo private)
# Mặc định: điện thoại vào bằng link https qua internet (cloudflared, tự cài), không cần cùng wifi.
[CmdletBinding()]
param([int]$Port = 8000, [switch]$Https, [switch]$Token)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
function Say($m, $c = 'Cyan') { Write-Host $m -ForegroundColor $c }

# --- 1. Windows 10 (1809) trở lên? ---
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
Say "Hệ điều hành: $($os.Caption) (build $build)"
if ($build -lt 17763) { Say 'Cần Windows 10 bản 1809 trở lên. Dừng.' Red; exit 1 }

# --- 2. Quyền Administrator (tự xin lại nếu thiếu) ---
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Say 'Cần quyền Administrator, đang xin lại...' Yellow
    $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-Port', $Port)
    if ($Https) { $a += '-Https' }; if ($Token) { $a += '-Token' }
    Start-Process powershell -Verb RunAs -ArgumentList $a
    exit 0
}

# --- 3. Mã truy cập GitHub (repo private, chỉ cần quyền đọc) ---
if ($Token -and (Get-Command git -ErrorAction SilentlyContinue)) {
    Say 'Dán mã truy cập GitHub (Fine-grained token, chỉ quyền Contents: Read-only) rồi Enter. Mã không hiện lên màn hình.' Yellow
    $sec = Read-Host -AsSecureString
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
    if ($plain) {
        "protocol=https`nhost=github.com`nusername=x-access-token`npassword=$plain`n" | git credential approve
        $plain = $null
        Say 'Đã lưu vào Windows Credential Manager (không nằm trong thư mục app).'
    }
}

# --- 4. Cài môi trường + chạy thử (không cập nhật, để nhanh) ---
# cloudflared: tạo link https công khai cho điện thoại (cài cho mọi người dùng để tác vụ SYSTEM cũng thấy)
if (-not $Https -and -not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Say 'Cài cloudflared (để điện thoại có link https)...'
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install --id Cloudflare.cloudflared -e --scope machine --silent --accept-package-agreements --accept-source-agreements | Out-Null
        $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    }
    if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) { Say 'Chưa cài được cloudflared: chỉ dùng được qua wifi. Cài tay: winget install Cloudflare.cloudflared rồi chạy lại.' Yellow }
}
$modeArg = if ($Https) { @('-Https') } elseif (Get-Command cloudflared -ErrorAction SilentlyContinue) { @('-Tunnel') } else { @() }
Say 'Cài môi trường và chạy thử lần đầu (có thể vài phút)...'
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run.ps1') -NoPull -Port $Port @modeArg
if ($LASTEXITCODE -ne 0) { Say 'Chạy thử thất bại, chưa tạo tác vụ tự động. Xem thông báo phía trên.' Red; exit 1 }

# --- 5. Tác vụ tự chạy (SYSTEM: không cần ai đăng nhập, chạy ẩn) ---
$flags = "-Auto -Port $Port" + $(if ($modeArg.Count) { ' ' + $modeArg[0] } else { '' })
$cmd = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $PSScriptRoot 'run.ps1')`" $flags"
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $cmd -WorkingDirectory $PSScriptRoot
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$set = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$tStart = New-ScheduledTaskTrigger -AtStartup
$tStart.Delay = 'PT30S'
$tRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 30)
Register-ScheduledTask -TaskName 'ScanApp' -Action $action -Principal $principal -Settings $set -Trigger $tStart -Force | Out-Null
Register-ScheduledTask -TaskName 'ScanApp-Update' -Action $action -Principal $principal -Settings $set -Trigger $tRepeat -Force | Out-Null

try { & (Join-Path $PSScriptRoot 'make-shortcut.ps1') -AllUsers } catch { Say "Chưa tạo được icon Desktop: $_" Yellow }   # icon ScanApp cho mọi người dùng máy

Say ''
Say 'XONG. Từ giờ:' Green
Say '  - Bật máy là app tự chạy (sau ~30 giây), không cần mở gì.'
Say '  - Cứ 30 phút app kiểm tra GitHub; có bản mới thì tự cập nhật + kiểm tra, lỗi thì tự quay về bản cũ.'
Say '    Đang có lệnh in chờ thì hoãn cập nhật.'
Say '  - Xem địa chỉ + QR cho điện thoại: bấm icon ScanApp ngoài Desktop → mở app, QR cho điện thoại ở đầu trang. Icon "ScanApp - Cai dat" hiện QR + link + log.'
Say '  - Gỡ: .\uninstall.cmd'
