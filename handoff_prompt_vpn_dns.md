# 飞连 VPN DNS 解析失败 — 排障交接 Prompt

> **时间**: 2026-07-01  
> **故障用户**: Windows 用户（单用户，同事正常）  
> **状态**: 排查中，用户已下班，下次回来继续

---

## 一、故障现象

| 维度 | 详情 |
|------|------|
| **环境** | Windows + 飞连（SealSuite）客户端，同时启用 VPN + SWG 模块 |
| **SWG 独立工作** | ✅ 正常 — 不开 VPN 时，所有流量走 SWG 隧道，上网/DNS 正常 |
| **VPN Full Tunnel** | ❌ 路由正确（0.0.0.0/1 → VPN 网关），但 tracert 第一跳超时，隧道**数据面死** |
| **VPN Split Tunnel** | ❌ 10.x 内网路由未推送，流量走物理 Wi-Fi 默认路由。nslookup 内网域名超时 |
| **DNS** | 飞连 DNS 代理 `127.0.0.1:53`，内网域名解析超时，公网 DNS 正常 |
| **间歇性** | 出现过一次自愈，后又复发。用户一直在切换飞连 server node |

## 二、设备环境（来自 ipconfig /all + route print）

### 虚拟网卡

| 接口 | IP | 用途 |
|------|-----|------|
| CorpLink Wintun (ifIndex 7) | 10.200.x.x/22 | **飞连 VPN 隧道**，DNS: 127.0.0.1, ::1 |
| CorpLink Wintun #2 (ifIndex 21) | 192.168.3.118/20 | **飞连 SWG 隧道**，DNS: 127.0.0.1, ::1 |
| CorpLink TAP-Windows6 ×2 | disconnected | 残留 TAP 适配器 |
| Wi-Fi (ifIndex 5) | 172.19.210.24/21 | 物理网卡，DNS: 170.251.204.212 等公网 DNS |

### 关键路由

- Full tunnel: `0.0.0.0/1 → 10.200.72.1 (metric 1)`, `128.0.0.0/1 → 10.200.72.1 (metric 1)` — VPN 隧道
- Split tunnel: `0.0.0.0/0 → 172.19.208.1 (metric 45)` — 走 Wi-Fi，**无 10.x 路由**
- VPN 网关 `10.200.72.1` ping 不通（full tunnel 下）

### 路由表异常

`Find-NetRoute 10.105.212.241` 确认路由走 CorpLink Wintun (ifIndex 7)，但 **路由表里的接口 IP（10.200.104.175）和 ipconfig 看到的 Wintun IP（10.200.82.45→10.200.75.12）对不上**→ 飞连重建实例后残留路由指向旧 IP。

## 三、已排查项

1. ✅ 写 hosts → 能通（证明到目标 IP 的连通性存在，问题在 DNS 解析路径）
2. ✅ `Find-NetRoute` 确认路由方向正确
3. ✅ `ipconfig /all` + `route print` 已收集完整
4. ✅ `nslookup` 显式指定 DNS 测试未执行（用户下班）
5. ✅ 已读取内部文档：

### 内部文档发现

| 文档 | 关键信息 |
|------|---------|
| **OSC-Tier2-SOP: Zscaler to Seal SWG Replacement** (`HrM3dC6mAonSMExL2j3c8H9znhe`) | 「飞连SWG也是隧道模式，与VPN隧道解耦。**VPN隧道优先级高于SWG隧道**」 |
| **IT-Oncall SealSuite SWG 运维FAQ** (`YH83dU8ego9029xQ3jMcTWBmnEd`) | 已知条目：「问：客户端显示SWG已连接，但是VPN连接后却无法使用」→ 答：检查版本≥3.2.16 + Zscaler卸载 |
| **SealSuite SWG 常见问题与解答** (`UjvpwAizoiG02NkyX0UcuL81nPd`) | SWG 使用 MITM 代理（80/443），VPN 提供内网加密通道。两者「独立模块、互不影响」 |
| **SealSuite SWG Operation and Maintenance FAQ** (`SVdcwVHTBi5cLmkQxadc461InIe`) | VPN vs SWG 对比表；ROW 用户应只有 RoW Sealsuite client，不用 Felian client |

## 四、当前根因分析（阶段性结论）

```
SWG 开启 → 创建第二个 Wintun 虚拟网卡 (192.168.3.118)
                ↓
与 VPN 的 Wintun 网卡 (10.200.x.x) 共享 Windows 网络栈
                ↓
用户频繁切换 server node → VPN Wintun 重建 → 竞态：
  ├── 路由残留指向旧实例 IP（路由表 vs ipconfig IP 不一致）
  ├── Full tunnel: 路由正确但数据面死（Wintun 驱动层绑定到错误实例？）
  ├── Split tunnel: 10.x 路由推送丢失（竞态导致路由推送静默失败）
  └── DNS: 两个网卡都设 127.0.0.1，可能代理冲突
                ↓
间歇性：切节点刚好没撞上 → "自己好了"
```

**核心嫌疑**: SWG + VPN 双 Wintun 实例 + 频繁切节点 → Wintun 驱动竞态。

**次要嫌疑**: Zscaler 残留（用户来自 Zscaler→SWG 迁移批次）。

## 五、用户回来后的下一步诊断

### 优先做（最快定位）

```powershell
# 1. 对比两个 Wintun 状态
Get-NetAdapter -Name "*Wintun*" | Format-Table Name, Status, LinkSpeed, State, ifIndex

# 2. 确认谁在监听 127.0.0.1:53
Get-Process -Id (Get-NetUDPEndpoint -LocalPort 53).OwningProcess -ErrorAction SilentlyContinue | Format-Table Name, Id, Path

# 3. 显式指定 DNS 对比
nslookup pipo-security-sea.tiktok-row.net          # 看默认走谁
nslookup pipo-security-sea.tiktok-row.net 127.0.0.1 # 强制飞连代理解析
nslookup pipo-security-sea.tiktok-row.net <内网DNS> # 绕过代理直连

# 4. ping VPN 网关
ping 10.200.72.1 -n 2
```

### 其次验证 Zscaler 残留

```powershell
Get-Service | Where-Object { $_.Name -match "zscaler|zsa" }
Get-Process | Where-Object { $_.Name -match "zscaler|zsa" }
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s | findstr /i zscaler
```

### 终极验证

如果上面都没结论，让用户在飞连客户端 **临时关闭 SWG 模块**，只跑 VPN，看 24 小时内是否复现。不复现 → 双 Wintun 冲突实锤。

### 对比同事

让正常同事跑同样的 `Get-NetAdapter` + `Get-NetRoute`，对比 Wintun 实例数量。

## 六、参考

- 目标域名: `pipo-security-sea.tiktok-row.net` → 解析 IP: `10.105.212.241`
- hosts 临时写入: `10.105.212.241  pipo-security-sea.tiktok-row.net`
- 用户身份: 网络运维工程师 zuojiajie（但本次是协助他人排障）
- 相关历史 session: `20260701_014257_a85038`（同群 SWG 故障汇总，Seattle 多人受影响）

---

> **给下一位 AI**: 直接接着排查。用户回来后会提供上面的诊断命令输出。核心问题是飞连 VPN 隧道在双 Wintun（SWG+VPN）环境下的数据面间歇性故障。优先让用户做「第一步」的四条命令。
