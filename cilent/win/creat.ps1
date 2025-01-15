# Set execution policy
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# 绕过代理获取IP地址
try {
    Write-Host "Fetching remote IP address..." -ForegroundColor Green
    $webClient = New-Object System.Net.WebClient
    $webClient.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy()
    $jsonResponse = $webClient.DownloadString("http://192.168.0.105:5000/get_ip").Trim()
    $ipObject = $jsonResponse | ConvertFrom-Json
    $remoteAddress = $ipObject.ip
}
catch {
    Write-Host "Failed to get address from API" -ForegroundColor Red
    Write-Host "Please enter the remote address:" -ForegroundColor Yellow
    $remoteAddress = Read-Host
}

# 定义密码数组
$passwords = @(
    '@jNT5x4=ct4',
    'e!DQV)RY)jAnuM3!N5EU$F2%YgYL@FA;',
    'k(n=@fuQzAHp2jIMMrSo9xG&MqeW.'
)

Write-Host "Launching connections to $remoteAddress..." -ForegroundColor Yellow

# 为每个密码创建连接
foreach ($password in $passwords) {
    # 加密密码
    $encryptedPassword = ($password | ConvertTo-SecureString -AsPlainText -Force) | ConvertFrom-SecureString

    # 创建RDP文件内容
    $rdpContent = @"
username:s:administrator
password 51:b:$encryptedPassword
screen mode id:i:1
desktopwidth:i:1440
desktopheight:i:900
use multimon:i:0
session bpp:i:32
compression:i:1
keyboardhook:i:2
audiocapturemode:i:0
videoplaybackmode:i:1
connection type:i:6
networkautodetect:i:0
bandwidthautodetect:i:1
displayconnectionbar:i:1
enableworkspacereconnect:i:0
disable wallpaper:i:0
allow font smoothing:i:1
allow desktop composition:i:1
disable full window drag:i:1
disable menu anims:i:1
disable themes:i:1
disable cursor setting:i:0
bitmapcachepersistenable:i:1
full address:s:$remoteAddress
audiomode:i:0
redirectprinters:i:1
redirectcomports:i:0
redirectsmartcards:i:1
redirectwebauthn:i:1
redirectclipboard:i:1
redirectposdevices:i:0
autoreconnection enabled:i:1
authentication level:i:0
prompt for credentials:i:0
negotiate security layer:i:1
remoteapplicationmode:i:0
alternate shell:s:
shell working directory:s:
gatewayhostname:s:
gatewayusagemethod:i:4
gatewaycredentialssource:i:4
gatewayprofileusagemethod:i:0
promptcredentialonce:i:0
gatewaybrokeringtype:i:0
use redirection server name:i:0
rdgiskdcproxy:i:0
kdcproxyname:s:
enablerdsaadauth:i:0
drivestoredirect:s:
"@

    # 创建临时RDP文件
    $tempFile = [System.IO.Path]::GetTempFileName()
    $tempRdpFile = [System.IO.Path]::ChangeExtension($tempFile, ".rdp")
    Move-Item -Path $tempFile -Destination $tempRdpFile -Force
    $rdpContent | Out-File -FilePath $tempRdpFile -Encoding ASCII
    
    # 启动RDP连接
    Start-Process "mstsc.exe" -ArgumentList $tempRdpFile
    
    # 等待0.5秒后删除文件
    Start-Sleep -Milliseconds 500
    Remove-Item -Path $tempRdpFile -Force
}

Write-Host "Closing in 3 seconds..." -NoNewline
Start-Sleep -Seconds 3