# Windows VPN/DNS 诊断命令速查

## DNS 与网卡

```cmd
ipconfig /all | findstr /i "dns"              # 所有网卡 DNS 绑定
netsh interface ipv4 show dnsservers          # DNS 服务器清单
nslookup <domain>                             # 确认实际使用的 DNS（第一行 Address）
nslookup <domain> 127.0.0.1                  # 显式指定 DNS 测试
nslookup <domain> <内网DNS_IP>               # 直接对内网 DNS 测试
Get-DnsClientNrptPolicy                       # NRPT 策略（PowerShell）
Get-DnsClientDohServerAddress                 # DoH 配置
```

## Wintun 虚拟网卡

```powershell
Get-NetAdapter -Name "*Wintun*" | Format-Table Name, Status, ifIndex
Get-NetIPAddress -InterfaceAlias "*Wintun*" -AddressFamily IPv4 | Format-Table InterfaceAlias, IPAddress
Get-NetConnectionProfile -InterfaceAlias "CorpLink Wintun" | Format-List Name, NetworkCategory
```

## 路由表

```powershell
Find-NetRoute -RemoteIPAddress <目标IP> | Format-List *    # 查去往某 IP 的路由
Get-NetRoute -DestinationPrefix "10.*" -AddressFamily IPv4  # 查 10 段路由
Get-NetRoute -InterfaceAlias "*Wintun*" -AddressFamily IPv4  # Wintun 接口路由
```

```cmd
route print -4 | findstr "0.0.0.0"            # 默认路由
route add 10.0.0.0 mask 255.0.0.0 <网关> metric 1 if 7   # 手动加路由
tracert -d <目标IP>                            # 看第一跳
```

## 端口与进程

```cmd
netstat -ano | findstr ":53 "                  # DNS 端口监听
tasklist | findstr <PID>                       # 查进程名
```

## hosts 文件

```powershell
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "10.105.212.241  pipo-security-sea.tiktok-row.net"
Get-Content "$env:SystemRoot\System32\drivers\etc\hosts" | Select-String "pipo-security"
```

```cmd
notepad C:\Windows\System32\drivers\etc\hosts    # 管理员 CMD 打开编辑
type C:\Windows\System32\drivers\etc\hosts        # 查看
```

## 防火墙

```powershell
Get-NetFirewallProfile | Format-Table Name, Enabled
Set-NetConnectionProfile -InterfaceAlias "CorpLink Wintun" -NetworkCategory Private
```

```cmd
netsh advfirewall set allprofiles state off       # 临时关闭（测试后记得开）
netsh advfirewall set allprofiles state on
```

## 网络重置

```cmd
netsh winsock reset
netsh int ip reset
```
