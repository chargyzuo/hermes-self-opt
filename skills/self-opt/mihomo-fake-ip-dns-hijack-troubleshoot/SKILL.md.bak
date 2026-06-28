---
name: mihomo-fake-ip-dns-hijack-troubleshoot
description: 排查 Mihomo/Clash Fake-IP 模式导致 DNS 解析返回 198.18.0.x 无法上网的问题
title: Mihomo Fake-IP DNS Hijack Troubleshoot
tags:
  - network
  - proxy
  - dns
  - troubleshooting
---

# Mihomo Fake-IP DNS Hijack Troubleshoot

## 场景
用户 ping 域名返回 198.18.0.73，浏览器或 curl 无法访问，路由表中存在 metric 0 的虚拟网卡默认路由。

## 排查步骤

### Step 1: 确认 DNS 解析
```
nslookup baidu.com
```
如果返回 198.18.0.73，继续下一步。

### Step 2: 检查路由表
```
route print -4
```
查找是否有 `0.0.0.0 0.0.0.0 on-link 198.18.0.1 metric 0` 条目。

### Step 3: 识别代理网卡
```
ipconfig /all
```
查找名称包含 `Mihomo`、`Meta Tunnel`、`Clash` 的适配器，其 IP 通常在 198.18.0.1，DNS 198.18.0.2。

### Step 4: 定位进程
```
tasklist /fi "IMAGENAME eq verge*"
```
常见进程名为 `verge-mihomo.exe` 或 `clash-verge.exe`。

## 解决方案

### 方法A：临时关闭代理
```
taskkill /f /im verge-mihomo.exe
```
网络将立即恢复。

### 方法B：配置直连规则
在 Mihomo 配置中添加：
```yaml
rules:
  - DOMAIN-SUFFIX,baidu.com,DIRECT
  - DOMAIN-KEYWORD,bytedance,DIRECT
```

### 方法C：切换 DNS 模式
将配置中的 `dns.mode` 从 `fake-ip` 改为 `redir-host`。

## 数据流说明
```
用户 ping baidu.com
  → DNS 查询 (走 Mimoho 网关 198.18.0.1)
  → Fake-IP 返回 198.18.0.73 (虚拟地址，不走代理)
  → ICMP 可在 TUN 层转发，但 TCP 到 Fake-IP 若无代理链则不通
```

## 原始数据示例
### route print -4
```
0.0.0.0 0.0.0.0 198.18.0.1 198.18.0.1 0
0.0.0.0 0.0.0.0 192.168.0.1 192.168.0.107 35
```

### ipconfig /all (相关部分)
```
未知适配器 Mihomo:
   描述: Meta Tunnel
   IPv4 地址: 198.18.0.1
   DNS 服务器: 198.18.0.2
```