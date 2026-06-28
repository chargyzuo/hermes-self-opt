---
name: query-wireless-terminal-state
description: 查询无线终端在 Aruba AC 上的状态、IP、VLAN 及 VLAN 权限
triggers:
  - 用户询问终端状态（MAC/ID）
  - 用户询问 VLAN 权限
steps:
  - 1. 根据设备名从 NetBox 获取设备类型和管理 IP
  - 2. 如果设备是无线控制器（AC），登录后查询指定 MAC 的客户端状态
  - 3. 返回终端在线状态、IP（IPv4/IPv6）、VLAN
  - 4. 如果用户询问 VLAN 权限，搜索内部知识库（Obsidian/飞书）
  - 5. 若未找到，报告未找到文档
