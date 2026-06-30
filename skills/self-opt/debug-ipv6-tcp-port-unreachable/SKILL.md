---
name: Debug IPv6 TCP Port Unreachable
description: 排障外部telnet IPv6端口不通的步骤（确认服务监听、防火墙、抓包、修复）
triggers:
  - 用户反馈从外部telnet <IPv6>:<port> 返回 Connection refused
  - 服务端已确认端口在监听但外部仍不通
---

## 步骤

### 1. 确认服务监听地址
```bash
ss -tlnp | grep :<port>
```
- 检查输出中 `Local Address:Port` 是否包含 `[::]:<port>`（IPv6监听）或 `0.0.0.0:<port>`（仅IPv4）
- 如果只有IPv4监听 => 服务未绑定IPv6，跳至步骤4

### 2. 检查防火墙规则
```bash
iptables -L INPUT -n -v | grep :<port>
```
- 确认没有REJECT/DROP规则针对该端口
- 检查默认策略（policy）是否为DROP，若是则添加放行规则

### 3. tcpdump抓包确认
```bash
tcpdump -i any dst host <server-ipv6> and dst port <port> -nn
```
- 观察是否收到SYN包，以及是否回复RST
- 若收到SYN并回复RST => 服务未监听IPv6（内核直接RST）

### 4. 修复服务绑定
- 若服务支持绑定IPv6（如python http.server）:
  ```bash
  python3 -m http.server <port> --bind ::
  ```
- 若服务不支持或不易修改，使用socat建立独立监听:
  ```bash
  sudo apt install socat
  socat TCP6-LISTEN:<port>,reuseaddr,fork EXEC:./your-server  # 需要转发到实际服务
  # 或仅测试连通性:
  socat TCP6-LISTEN:<port>,reuseaddr,fork -
  ```

### 5. 验证
```bash
telnet <server-ipv6> <port>
```
连接成功即可。