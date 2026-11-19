# open-app.ps1 - icon "ScanApp" (Windows): MỘT cửa sổ duy nhất.
#   Chưa cài  -> chạy install.ps1 (hỏi quyền Administrator) và báo tiến độ.
#   Đã cài    -> bật server ngầm nếu chưa chạy, rồi hiện QR + link cho điện thoại, nút mở app.
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
try { [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } } catch { }   # chứng chỉ tự ký trên chính máy này
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null
$InstallLog = Join-Path $Root 'logs\install.log'

function Get-Base {
    $ports = @(8000); $pf = Join-Path $Root '.run\port'
    if (Test-Path $pf) { $ports = @([int](Get-Content $pf)) + $ports }
    foreach ($p in ($ports | Select-Object -Unique)) { foreach ($s in 'http', 'https') {
        try { if ((Invoke-WebRequest -Uri "${s}://127.0.0.1:$p/api/health" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { return "${s}://localhost:$p" } } catch { }
    } }
    return $null
}
function Test-Installed {
    (Test-Path (Join-Path $Root '.venv\Scripts\python.exe')) -and [bool](Get-ScheduledTask -TaskName 'ScanApp' -ErrorAction SilentlyContinue)
}
function Get-Mode {   # lấy lại chế độ (-Tunnel / -Https) mà install.ps1 đã đăng ký cho tác vụ
    try { $a = (Get-ScheduledTask -TaskName 'ScanApp' -ErrorAction Stop).Actions[0].Arguments; if ($a -match '-Https') { return '-Https' }; if ($a -match '-Tunnel') { return '-Tunnel' } } catch { }
    if (Get-Command cloudflared -ErrorAction SilentlyContinue) { return '-Tunnel' }
    return $null
}
function Get-LastLine($path) {
    try {
        $fs = [IO.File]::Open($path, 'Open', 'Read', 'ReadWrite'); $sr = New-Object IO.StreamReader($fs)
        $txt = $sr.ReadToEnd(); $sr.Close(); $fs.Close()
        $l = $txt -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -and $_ -notmatch '^\*{5,}|^Transcript|^Windows PowerShell|^Start time|^End time|^Username|^RunAs|^Configuration|^Machine|^Host Application|^Process ID|^PSVersion|^PSEdition|^PSCompatible|^BuildVersion|^CLRVersion|^WSManStack|^SerializationVersion|^PSRemotingProtocol' } | Select-Object -Last 1
        if ($l) { return $l.Substring(0, [Math]::Min(90, $l.Length)) }
    } catch { }
    return ''
}

# ---------- giao diện ----------
$f = New-Object Windows.Forms.Form
$f.Text = 'ScanApp'; $f.ClientSize = New-Object Drawing.Size(480, 700); $f.StartPosition = 'CenterScreen'
$f.FormBorderStyle = 'FixedSingle'; $f.MaximizeBox = $false; $f.Font = New-Object Drawing.Font('Segoe UI', 12)
try { $f.Icon = New-Object Drawing.Icon((Join-Path $Root 'assets\scanapp.ico')) } catch { }
function Add-Label($y, $h, $size, $bold) {
    $l = New-Object Windows.Forms.Label; $l.SetBounds(40, $y, 400, $h); $l.TextAlign = 'MiddleCenter'
    $l.Font = New-Object Drawing.Font('Segoe UI', $size, $(if ($bold) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }))
    $f.Controls.Add($l); return $l
}
function Add-Button($y, $text, $primary) {
    $b = New-Object Windows.Forms.Button; $b.SetBounds(90, $y, 300, 52); $b.Text = $text; $b.Visible = $false
    $b.Font = New-Object Drawing.Font('Segoe UI', 14, [Drawing.FontStyle]::Bold); $b.FlatStyle = 'System'
    $f.Controls.Add($b); return $b
}
$lTitle = Add-Label 16 44 24 $true; $lTitle.Text = 'ScanApp'
$lStatus = Add-Label 66 84 17 $true
$bar = New-Object Windows.Forms.ProgressBar; $bar.Style = 'Marquee'; $bar.SetBounds(90, 160, 300, 18); $f.Controls.Add($bar)
$lDetail = Add-Label 190 70 10 $false; $lDetail.ForeColor = [Drawing.Color]::Gray
$pic = New-Object Windows.Forms.PictureBox; $pic.SetBounds(110, 150, 260, 260); $pic.SizeMode = 'Zoom'; $pic.Visible = $false; $f.Controls.Add($pic)
$lCap = Add-Label 416 64 13 $false; $lCap.Visible = $false
$tLink = New-Object Windows.Forms.TextBox; $tLink.SetBounds(40, 486, 400, 30); $tLink.ReadOnly = $true; $tLink.TextAlign = 'Center'; $tLink.Visible = $false; $f.Controls.Add($tLink)
$bOpen = Add-Button 530 'Mở app trên máy này' $true
$bCopy = Add-Button 592 'Chép link' $false
$bRetry = Add-Button 530 'Thử lại' $true

# ---------- trạng thái ----------
$st = @{ started = $false; mode = ''; proc = $null; t0 = Get-Date; base = $null; shown = ''; busy = $false }
function Start-Work {
    $st.started = $true; $st.t0 = Get-Date; $st.proc = $null
    try {
        if (-not (Test-Installed)) {
            $st.mode = 'install'; Remove-Item $InstallLog -Force -ErrorAction SilentlyContinue
            $st.proc = Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden -PassThru -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$(Join-Path $PSScriptRoot 'install.ps1')`""
        } else {
            $st.mode = 'start'
            $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$(Join-Path $Root 'scripts\run.ps1')`"", '-Auto'); $m = Get-Mode; if ($m) { $a += $m }
            $st.proc = Start-Process powershell.exe -WindowStyle Hidden -PassThru -ArgumentList $a `
                -RedirectStandardOutput (Join-Path $Root 'logs\launcher.log') -RedirectStandardError (Join-Path $Root 'logs\launcher.err.log')
        }
    } catch { $st.mode = 'denied' }
}
function Show-Ready($base) {
    $bar.Visible = $false; $lDetail.Visible = $false; $bRetry.Visible = $false
    $lStatus.Text = 'ScanApp đã sẵn sàng'
    $items = @(); try { $items = @((Invoke-RestMethod -Uri "$base/api/links" -TimeoutSec 3).items) } catch { }
    $it = $items | Where-Object { $_.url -like 'https*' } | Select-Object -First 1; $https = [bool]$it
    if (-not $it) { $it = $items | Select-Object -First 1 }
    if ($it -and $it.url -ne $st.shown) {
        try {
            $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 4 -Uri ("$base/api/qr.png?u=" + [uri]::EscapeDataString($it.url))
            $ms = New-Object IO.MemoryStream(, $r.Content); $pic.Image = [Drawing.Image]::FromStream($ms)
        } catch { }
        $st.shown = $it.url; $tLink.Text = $it.url
    }
    $lCap.Text = if ($https) { 'Dùng camera điện thoại quét mã này để mở app' } else { "Đang tạo link https cho camera điện thoại (vài giây)...`nTạm thời quét mã này (cùng wifi)" }
    foreach ($c in $pic, $lCap, $tLink, $bOpen, $bCopy) { $c.Visible = $true }
}
function Tick {
    if ($st.busy) { return }; $st.busy = $true
    try {
        $b = Get-Base; $st.base = $b
        if ($b) { Show-Ready $b; return }
        foreach ($c in $pic, $lCap, $tLink, $bOpen, $bCopy) { $c.Visible = $false }; $st.shown = ''
        if (-not $st.started) { Start-Work }
        $exited = $false; try { if ($st.proc -and $st.proc.HasExited) { $exited = $true } } catch { }
        $secs = ((Get-Date) - $st.t0).TotalSeconds
        if ($st.mode -eq 'denied' -or ($exited -and $secs -gt 20) -or ($st.mode -eq 'start' -and $secs -gt 240)) {
            $bar.Visible = $false; $bRetry.Visible = $true; $lDetail.Visible = $true
            $lStatus.Text = if ($st.mode -eq 'denied') { 'Cần bấm "Yes" khi Windows hỏi quyền để cài đặt' } else { 'Chưa bật được ScanApp' }
            $lDetail.Text = "Xem file logs\install.log hoặc logs\launcher.log trong thư mục scan-app.`n" + (Get-LastLine $InstallLog)
            return
        }
        $bar.Visible = $true; $lDetail.Visible = $true
        if ($st.mode -eq 'install') { $lStatus.Text = "Đang cài đặt lần đầu...`nCó thể mất vài phút, xin đừng tắt máy"; $lDetail.Text = Get-LastLine $InstallLog }
        else { $lStatus.Text = 'Đang bật ScanApp...'; $lDetail.Text = '' }
    } finally { $st.busy = $false }
}
$bOpen.Add_Click({ if ($st.base) { Start-Process "$($st.base)/" } })
$bCopy.Add_Click({ [Windows.Forms.Clipboard]::SetText($tLink.Text); $bCopy.Text = 'Đã chép ✓'; $script:cpT = Get-Date })
$bRetry.Add_Click({ $bRetry.Visible = $false; $st.started = $false; $lStatus.Text = 'Đang thử lại...'; Tick })
$timer = New-Object Windows.Forms.Timer; $timer.Interval = 2500
$timer.Add_Tick({ if ($bCopy.Text -ne 'Chép link' -and ((Get-Date) - $script:cpT).TotalSeconds -gt 2) { $bCopy.Text = 'Chép link' }; Tick })
$f.Add_Shown({ $f.Activate(); $lStatus.Text = 'Đang kiểm tra...'; $timer.Start(); Tick })
[void]$f.ShowDialog()
