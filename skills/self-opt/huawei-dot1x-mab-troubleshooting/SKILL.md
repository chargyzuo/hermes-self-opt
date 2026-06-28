---
name: huawei-dot1x-mab-troubleshooting
description: 华为交换机 dot1x MAC 旁路认证卡 Pre-authen 排查
---

# 华为 dot1x MAB 认证卡 Pre-authen 排查步骤

1. **收集基础信息**：
   - 获取设备名、版本、端口、VLAN 及认证配置 (`display dot1x`, `display mac-access-profile`)
   - 查看 RADIUS 配置与服务器状态 (`display radius-server configuration`, `display radius-server status`)

2. **验证 RADIUS 可通性**：
   - Ping 测试服务器
   - 发不分片大包探测 Path MTU (`ping -f -s <size>`)
   - 注意 `test-aaa` 对 MAB 不准确（RADIUS 走 Call-Check 非 PAP/CHAP）

3. **检查端口物理与认证状态**：
   - 查看端口 up/down 历史及 CRC (`display interface brief`, `display interface <int>`)
   - 检查 `display access-user` 状态、认证类型、domain
   - 查看 dot1x 统计 (`display dot1x interface <int>`)，关注 EAPOL 失败、MAC bypass 触发计数

4. **查找失败原因**：
   - 执行 `display aaa online-fail-record mac-address <mac>` 查看明确拒绝原因（如 IP 冲突、RADIUS 超时）
   - 检查 DHCP snooping 绑定表、ARP 表是否存在 IP 冲突
   - 调查同 VLAN 其他用户 IP 分配情况

5. **终端侧排查**：
   - 确认客户端是否运行容器（Docker）导致默认 bridge 地址泄露
   - 检查网卡驱动/NetworkManager 是否导致 link flap

6. **解决方案**：
   - 修改 Docker `bip` 参数避开冲突子网
   - 必要时调整交换机认证 domain 或 bypass 延迟