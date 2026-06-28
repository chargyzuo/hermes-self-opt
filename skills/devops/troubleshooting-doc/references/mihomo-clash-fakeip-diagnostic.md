# Mihomo (Clash Meta) Fake-IP 快速诊断

## 触发信号

用户/设备报告以下任一现象时立即参考本文：

- `ping` 某个公网域名解析到 `198.18.0.x`
- `nslookup` 显示 DNS Server 为 `198.18.0.2`
- `route print` 中存在 metric=0 的默认路由指向 `198.18.0.1`
- `ipconfig` 中出现名为 "Mihomo" 或 "Meta Tunnel" 的虚拟适配器
- 浏览器/curl 不通但 ping 通（Mihomo TUN 驱动正常，上游代理链断）

## 关键 IP 段

| IP 段 | 含义 | 来源 |
|-------|------|------|
| 198.18.0.0/15 | RFC 2544 基准测试保留段 | Mihomo 社区约定用作 Fake-IP 池 |
| 198.18.0.1 | Mihomo Meta Tunnel 虚拟网卡 IP | ipconfig 中可见 |
| 198.18.0.2 | Mihomo Fake-IP DNS 服务器 | nslookup 中可见 |
| 198.18.0.x (x>2) | 被代理域名的 Fake-IP 映射 | ping 目标地址 |

## 诊断三步

### 1. 确认 Mihomo 存在

```cmd
ipconfig /all | findstr "Mihomo"
route print -4 | findstr "198.18"
tasklist | findstr -i mihomo
```

任一有输出 → Mihomo 正在运行。

### 2. 区分 TUN vs TCP 故障

| 现象 | 判断 |
|------|------|
| ping 通, 浏览器不通 | TUN 驱动正常，TCP 上游代理链断 |
| ping 不通, 浏览器不通 | TUN 驱动本身故障或 Mihomo 未正常工作 |

### 3. 确认根因

- `nslookup baidu.com 8.8.8.8` 返回正常公网 IP → 仅 Mihomo DNS 劫持
- 抓包看 DNS 响应源 IP = 198.18.0.2 → Mihomo TUN DNS
- 抓包看 TCP SYN 发出无响应 → 上游代理链断

## 修复

关闭 Mihomo 是最高效的方式：

```cmd
taskkill /f /im verge-mihomo.exe
```

或任务管理器 → 详细信息 → 搜索 `mihomo` → 结束任务。

验证：关闭后 `route print -4` 中 198.18.x 路由消失，`nslookup baidu.com` 恢复正常。

## 注意：与飞连共存的冲突

Mihomo metric=0 高于飞连 metric=1。同时运行时：
- 非 10.x 内网的 DNS 全部被 Mihomo 劫持
- Mihomo 代理不通时飞连无法兜底
- 建议用户二选一
