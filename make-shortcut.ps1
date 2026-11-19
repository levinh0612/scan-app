# make-shortcut.ps1 - tạo 2 icon ngoài Desktop + Start Menu:
#   "ScanApp"            (người dùng) bấm = mở app trên trình duyệt, tự bật server ngầm nếu chưa chạy
#   "ScanApp - Cài đặt"  (người cài/sửa lỗi) bấm = cửa sổ hiện QR + link + log
# Dùng:  .\make-shortcut.cmd      (không cần quyền Administrator; install.ps1 cũng tự gọi)
param([switch]$AllUsers)
$ErrorActionPreference = 'Stop'
$ico = Join-Path $PSScriptRoot 'assets\scanapp.ico'
if (-not (Test-Path $ico)) { Write-Host 'Thiếu assets\scanapp.ico' -ForegroundColor Red; exit 1 }
$desk = [Environment]::GetFolderPath($(if ($AllUsers) { 'CommonDesktopDirectory' } else { 'Desktop' }))
$menu = [Environment]::GetFolderPath($(if ($AllUsers) { 'CommonPrograms' } else { 'Programs' }))
$run = Join-Path $PSScriptRoot 'run.ps1'; $open = Join-Path $PSScriptRoot 'open-app.ps1'
$sh = New-Object -ComObject WScript.Shell
$defs = @(
    @{ Name = 'ScanApp.lnk'; Args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$open`""; Desc = 'ScanApp - mở app quét giấy tờ'; Win = 7 },
    @{ Name = 'ScanApp - Cai dat.lnk'; Args = "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$run`" -Open"; Desc = 'ScanApp - cài đặt: hiện QR + link + log'; Win = 1 }
)
foreach ($dir in @($desk, $menu)) {
    if (-not $dir -or -not (Test-Path $dir)) { continue }
    foreach ($d in $defs) {
        $lnk = $sh.CreateShortcut((Join-Path $dir $d.Name))
        $lnk.TargetPath = 'powershell.exe'
        $lnk.Arguments = $d.Args
        $lnk.WorkingDirectory = $PSScriptRoot
        $lnk.IconLocation = "$ico,0"
        $lnk.WindowStyle = $d.Win
        $lnk.Description = $d.Desc
        $lnk.Save()
        Write-Host "Đã tạo: $(Join-Path $dir $d.Name)" -ForegroundColor Green
    }
}
Write-Host 'ScanApp: bấm là mở app (QR cho điện thoại ở đầu trang). ScanApp - Cai dat: cửa sổ QR + link + log.'
