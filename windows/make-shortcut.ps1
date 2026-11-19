# make-shortcut.ps1 - tạo MỘT icon "ScanApp" ngoài Desktop + Start Menu: bấm = cửa sổ ScanApp
#   (chưa cài thì tự cài, chưa chạy thì tự bật server ngầm, rồi hiện QR + link cho điện thoại)
# Dùng:  .\windows\make-shortcut.ps1      (không cần quyền Administrator; install.ps1 cũng tự gọi)
param([switch]$AllUsers)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$ico = Join-Path $Root 'assets\scanapp.ico'
if (-not (Test-Path $ico)) { Write-Host 'Thiếu assets\scanapp.ico' -ForegroundColor Red; exit 1 }
$desk = [Environment]::GetFolderPath($(if ($AllUsers) { 'CommonDesktopDirectory' } else { 'Desktop' }))
$menu = [Environment]::GetFolderPath($(if ($AllUsers) { 'CommonPrograms' } else { 'Programs' }))
$run = Join-Path $Root 'scripts\run.ps1'; $open = Join-Path $PSScriptRoot 'open-app.ps1'
$sh = New-Object -ComObject WScript.Shell
$defs = @(
    @{ Name = 'ScanApp.lnk'; Args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$open`""; Desc = 'ScanApp - quét giấy tờ (tự cài, tự bật, hiện QR + link)'; Win = 7 }
)
foreach ($dir in @($desk, $menu)) {
    if (-not $dir -or -not (Test-Path $dir)) { continue }
    Remove-Item (Join-Path $dir 'ScanApp - Cai dat.lnk') -Force -ErrorAction SilentlyContinue   # icon thứ hai của bản cũ
    foreach ($d in $defs) {
        $lnk = $sh.CreateShortcut((Join-Path $dir $d.Name))
        $lnk.TargetPath = 'powershell.exe'
        $lnk.Arguments = $d.Args
        $lnk.WorkingDirectory = $Root
        $lnk.IconLocation = "$ico,0"
        $lnk.WindowStyle = $d.Win
        $lnk.Description = $d.Desc
        $lnk.Save()
        Write-Host "Đã tạo: $(Join-Path $dir $d.Name)" -ForegroundColor Green
    }
}
Write-Host 'Bấm icon ScanApp: tự cài (nếu chưa) + tự bật + hiện QR và link cho điện thoại.'
