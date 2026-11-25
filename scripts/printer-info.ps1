# Hiện IP + MAC của máy in (và máy tính này) để đặt IP cố định trong router.
# Chạy: bấm phải chuột -> Run with PowerShell, hoặc: powershell -ExecutionPolicy Bypass -File scripts\printer-info.ps1
Write-Host ''
Write-Host '=== MAY IN DA CAI TREN WINDOWS ===' -ForegroundColor Cyan
$ports = @{}
Get-PrinterPort -ErrorAction SilentlyContinue | ForEach-Object { $ports[$_.Name] = $_ }
Get-Printer -ErrorAction SilentlyContinue | ForEach-Object {
    $p = $ports[$_.PortName]
    $ip = if ($p -and $p.PrinterHostAddress) { $p.PrinterHostAddress } else { '(cong ' + $_.PortName + ' - khong phai IP)' }
    $mac = ''
    if ($p -and $p.PrinterHostAddress) {
        try { Test-Connection $p.PrinterHostAddress -Count 1 -Quiet | Out-Null } catch { }
        $n = Get-NetNeighbor -IPAddress $p.PrinterHostAddress -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($n -and $n.LinkLayerAddress) { $mac = $n.LinkLayerAddress }
    }
    Write-Host ("{0,-40} IP: {1,-18} MAC: {2}" -f $_.Name, $ip, $mac)
}
Write-Host ''
Write-Host '=== MAY TINH NAY ===' -ForegroundColor Cyan
Get-NetIPConfiguration | Where-Object { $_.IPv4Address -and $_.NetAdapter.Status -eq 'Up' } | ForEach-Object {
    Write-Host ("{0}: IP {1}  |  cong mac dinh (router) {2}" -f $_.InterfaceAlias, $_.IPv4Address.IPAddress, $_.IPv4DefaultGateway.NextHop)
}
Write-Host ''
Write-Host 'CACH DAT IP CO DINH CHO MAY IN (lam 1 lan):' -ForegroundColor Yellow
Write-Host ' 1. Mo trinh duyet, vao dia chi router (cong mac dinh o tren, thuong 192.168.1.1 hoac 192.168.0.1), dang nhap (mat khau thuong in o day router).'
Write-Host ' 2. Tim muc "DHCP" -> "Address Reservation" / "Static DHCP" / "Gan IP theo MAC" / "IP Binding".'
Write-Host ' 3. Chon may in trong danh sach thiet bi (hoac nhap MAC o tren) va giu nguyen IP dang hien (vd 192.168.1.50). Luu.'
Write-Host ' 4. Tat/bat may in. Chay lai file nay: IP phai van nhu cu.'
Write-Host ' Xong. Neu may in luc truoc la cong WSD/khong co IP: cai lai may in theo "Standard TCP/IP Port" voi IP do.'
Write-Host ''
Read-Host 'Nhan Enter de dong'
