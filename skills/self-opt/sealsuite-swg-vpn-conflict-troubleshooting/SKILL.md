---
name: sealsuite-swg-vpn-conflict-troubleshooting
version: 1.0.0
description: "Diagnose SealSuite/飞连 SWG + VPN dual Wintun tunnel conflicts on Windows — DNS resolution failures, split-tunnel routing gaps, full-tunnel data-plane dead, intermittent connectivity after node switching."
---

# SealSuite SWG + VPN Wintun 双隧道冲突诊断

## 触发条件

当用户报告以下症状组合时加载此技能：
- 飞连 VPN 连接后 DNS 解析内网域名超时（nslookup 超时）
- 飞连 Full Tunnel 模式下内网 IP ping 不通，但路由表正确
- 飞连 Split Tunnel 模式下内网流量走了本地网卡而非 VPN 隧道
- 问题间歇性出现，切换 server node 后有时自愈、有时复发
- 用户 `ipconfig /all` 显示多个 CorpLink Wintun 虚拟网卡（VPN + SWG 各一个）
- 问题出现在 SWG 功能开启之后（约 2026 Q2）

## 背景：架构概览

飞连客户端包含两个独立模块，各自创建 Wintun 虚拟网卡：

| 模块 | Wintun 实例 | 典型 IP | 作用 |
|------|------------|---------|------|
| VPN | CorpLink Wintun (ifIndex 7) | 10.200.x.x | 内网路由（split/full tunnel） |
| SWG | CorpLink Wintun #1 (ifIndex 21) | 192.168.3.x | 80/443 HTTP/HTTPS MITM 代理 |

两者都设置 DNS 为 `127.0.0.1`，都需要 `wintun.sys` 驱动。
官方文档称两者「独立模块，互不影响」，但实际上共享 Windows 网络栈（DNS、路由表、驱动层）。

内部文档来源（Lark）：
- IT-Oncall SealSuite SWG 运维FAQ: `YH83dU8ego9029xQ3jMcTWBmnEd`
- SealSuite SWG O&M FAQ (EN): `SVdcwVHTBi5cLmkQxadc461InIe`
- 常见问题与解答: `UjvpwAizoiG02NkyX0UcuL81nPd`
- Zscaler to SWG Replacement SOP: `HrM3dC6mAonSMExL2j3c8H9znhe`
- Migration Troubleshooting: `YltmwFBpli30KGk2yBScB2jan9d`

SOP 关键引述：*"飞连SWG也是隧道模式，与VPN隧道解耦。VPN隧道优先级高于SWG隧道，即可以通过开启飞连VPN FULL MODE，绕过飞连SWG隧道。"*

## 诊断流程

### 第 0 步：快速验证 — hosts 文件

先绕过 DNS 确认连通性，排除纯网络问题：

```cmd
# 管理员 CMD 或 PowerShell
echo 10.105.212.241 pipo-security-sea.tiktok-row.net >> C:\Windows\System32\drivers\etc\hosts
ping pipo-security-sea.tiktok-row.net
```

如果 hosts 加完能 ping 通但 nslookup 超时 → DNS 代理问题，继续排查。

### 第 1 步：Wintun 实例盘点

```powershell
Get-NetAdapter -Name "*Wintun*" | Format-Table Name, Status, ifIndex, InterfaceDescription
```

预期看到至少 2 个活跃的 Wintun 实例（VPN + SWG）。如果同一个类型有多个残留（`#0, #1, #2`），说明历史实例没清理干净。

### 第 2 步：DNS 绑定全量检查

```cmd
ipconfig /all | findstr /i "dns"
```

```powershell
netsh interface ipv4 show dnsservers
```

预期：飞连 Wintun 网卡 DNS 为 `127.0.0.1`。**关键**：检查 Wi-Fi/物理网卡是否也绑定了公网 DNS（如 `170.251.x.x`），它们会跟 `127.0.0.1` 竞争。

### 第 3 步：确认 DNS 实际走了谁

```cmd
nslookup pipo-security-sea.tiktok-row.net
```

第一行 `Address` 暴露实际 DNS 服务器。如果不是 `127.0.0.1`，DNS 被其他网卡劫持。

逐个对比：
```cmd
nslookup internal.corp.com 127.0.0.1
nslookup internal.corp.com <内网DNS_IP>
```

127.0.0.1 超时但内网 DNS 正常 → SWG/VPN DNS 代理没转发。两个都超时 → 先排查到内网 DNS 的连通性。

### 第 4 步：路由分析

```powershell
Find-NetRoute -RemoteIPAddress 10.105.212.241 | Format-List *
```

检查 `InterfaceAlias` 和 `NextHop`：
- Split Tunnel：应走 CorpLink Wintun + 飞连网关。如果没有 10.x 路由，说明飞连没推送。
- Full Tunnel：应有 `0.0.0.0/1` 和 `128.0.0.0/1` 覆盖全网到飞连网关。

```cmd
tracert -d 10.105.212.241
```

第一跳超时 → 隧道数据面死（路由正确但网关不可达）。

```cmd
ping 10.200.72.1    # 飞连 VPN 隧道网关
```

### 第 5 步：路由表 IP 一致性

```powershell
# 看 Wintun 接口上的 IP
Get-NetIPAddress -InterfaceAlias "*Wintun*" -AddressFamily IPv4 | Format-Table InterfaceAlias, IPAddress

# 看路由表中的出接口 IP
Get-NetRoute -InterfaceAlias "*Wintun*" -AddressFamily IPv4 | Format-Table DestinationPrefix, NextHop, ifIndex
```

如果 `Get-NetIPAddress` 的 IP 和 `Get-NetRoute` 的接口 IP 不一致 → 路由挂到了旧/错误的 Wintun 实例。

### 第 6 步：端口 53 监听

```cmd
netstat -ano | findstr ":53 "
```

预期只有飞连进程监听 `127.0.0.1:53`。如果还有其他进程 → DNS 代理冲突。

### 第 7 步：NRPT / DoH 检查

```powershell
Get-DnsClientNrptPolicy | Format-Table -AutoSize
Get-DnsClientDohServerAddress
```

组策略或 DoH 可能强制某些域名走特定 DNS，绕过飞连代理。

### 第 8 步：防火墙临时验证

```powershell
Get-NetFirewallProfile | Format-Table Name, Enabled
```

```cmd
netsh advfirewall set allprofiles state off
# 立刻测试 ping 10.200.72.1
netsh advfirewall set allprofiles state on
```

### 第 9 步：Wintun Profile 检查

```powershell
Get-NetConnectionProfile -InterfaceAlias "CorpLink Wintun" | Format-List Name, NetworkCategory
```

如果是 `Public` → Windows 防火墙可能阻止入站流量：
```powershell
Set-NetConnectionProfile -InterfaceAlias "CorpLink Wintun" -NetworkCategory Private
```

## 根因模式

### 模式 1：双 Wintun DNS 竞争（最常见）

两个 Wintun 网卡都设 DNS 为 `127.0.0.1`，但 Windows DNS Client 服务同时向两个接口发查询，SWG 代理抢到查询后无法解析内网域名（SWG 只管 80/443 Web 代理），VPN 代理没收到查询 → nslookup 超时。

**验证**：`nslookup` 第一行 `Address` 确认实际 DNS，然后用 `nslookup domain 127.0.0.1` 单测。

### 模式 2：节点切换竞态 → 隧道数据面死

用户在飞连里切换 server node 时：
1. 旧 Wintun 实例销毁
2. 新 Wintun 实例创建
3. 路由推送到新实例
4. 隧道加密通道建立

如果步骤 3-4 异步未完成或路由推送到了旧实例 → Full Tunnel 下路由正确但网关不通。

**验证**：`Get-NetRoute` 出接口 IP 与 `Get-NetIPAddress` 不一致。

### 模式 3：Split Tunnel 路由推送缺失

SWG 部署后，飞连管理后台的 split-tunnel Route Inclusion 可能不包含所有内网网段（如新增的 `10.105.x.x`）。

**验证**：`Get-NetRoute -DestinationPrefix "10.*"` 为空或不全。

## 修复路径（由简到深）

1. **清理 Wintun 残留**：设备管理器 → 显示隐藏设备 → 网络适配器 → 删除所有灰色/隐藏的 Wintun Userspace Tunnel 和 TAP-Windows Adapter V9 残留 → 重启飞连
2. **临时绕过路由**：`route add 10.0.0.0 mask 255.0.0.0 <飞连网关> metric 1 if 7`
3. **禁用 SWG 验证**：临时禁用 SWG 24h，观察问题是否消失
4. **重置网络**：`netsh winsock reset` + `netsh int ip reset` → 重启
5. **升级/重装飞连**：确认版本 ≥ 3.2.16

## 注意事项

- 不要直接写 `10.0.0.0/8` 路由——如果 Full Tunnel 的 `/1` 路由已存在，再加是冗余的
- 飞连有多个 server node，切换前建议先断开等 5 秒再切，给异步清理留时间
- SWG 禁用码有时效性，需联系 IT-Security 获取
- 如果同事正常、仅单个用户故障，优先怀疑客户端残留而非服务端配置

## 参考文件

- `references/windows-vpn-dns-cheatsheet.md` — Windows VPN/DNS 诊断命令速查
- `references/internal-docs-index.md` — SealSuite SWG + VPN 内部文档索引与架构引述
