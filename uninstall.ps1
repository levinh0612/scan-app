# uninstall.ps1 - gỡ tác vụ tự chạy và dừng app (chạy bằng quyền Administrator). Không xoá dữ liệu/mã nguồn.
$ErrorActionPreference = 'Continue'
Set-Location -LiteralPath $PSScriptRoot
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Start-Process powershell -Verb RunAs -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`""); exit 0 }
foreach ($t in 'ScanApp', 'ScanApp-Update') { Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue }
Get-NetFirewallRule -DisplayName 'ScanApp *' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
& (Join-Path $PSScriptRoot 'stop.ps1')
Write-Host 'Đã gỡ tác vụ tự chạy và quy tắc firewall.' -ForegroundColor Green
Read-Host 'Enter để đóng'
