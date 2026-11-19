# setup-autostart.ps1 - đăng ký tác vụ Windows: tự chạy khi đăng nhập và cứ 5 phút kiểm tra code mới trên GitHub.
# Dùng:  powershell -ExecutionPolicy Bypass -File .\setup-autostart.ps1          (bật)
#        powershell -ExecutionPolicy Bypass -File .\setup-autostart.ps1 -Remove  (gỡ)
param([switch]$Remove, [int]$EveryMinutes = 5)
$ErrorActionPreference = 'Stop'
$TaskName = 'ScanApp'

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Đã gỡ tác vụ $TaskName."; exit 0
}

$arg = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSScriptRoot\run.ps1`" -Auto"
$action   = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg -WorkingDirectory $PSScriptRoot
$logon    = New-ScheduledTaskTrigger -AtLogOn
$repeat   = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $EveryMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($logon, $repeat) -Settings $settings `
    -Description 'Tự chạy và tự cập nhật app scan cầm đồ' -Force | Out-Null
Write-Host "Đã đăng ký tác vụ '$TaskName': chạy khi đăng nhập + mỗi $EveryMinutes phút kiểm tra bản mới."
Write-Host 'Lưu ý: tác vụ chỉ chạy khi tài khoản Windows này đã đăng nhập. Nên bật tự đăng nhập trên máy tiệm.'
