# tunnel.ps1 - giữ link https (Cloudflare) sống: Cloudflare từ chối tạm thời (429) hoặc tunnel rớt thì tự thử lại sau 20 giây.
# run.ps1 -Tunnel tự gọi (chạy ẩn); tắt bằng stop.cmd. Log: logs\tunnel.log
param([int]$Port = 8000, [switch]$Https)
$ErrorActionPreference = 'Continue'
$log = Join-Path (Split-Path -Parent $PSScriptRoot) 'logs\tunnel.log'
$args2 = if ($Https) { @('tunnel', '--no-tls-verify', '--url', "https://localhost:$Port") } else { @('tunnel', '--url', "http://localhost:$Port") }
while ($true) {
    Remove-Item $log -Force -ErrorAction SilentlyContinue
    Start-Process cloudflared -ArgumentList $args2 -WindowStyle Hidden -Wait -RedirectStandardError $log
    Start-Sleep -Seconds 20
}
