---
name: vlan-and-terminal-inquiry
description: 查询终端在线状态及 VLAN 信息，并尝试查找 VLAN 的权限文档
triggers:
  - 用户请求查询终端 VLAN 状态
  - 用户请求查询 VLAN 内网权限
steps:
  - 从 NetBox 获取设备信息和管理 IP
  - 登录设备查询终端的在线状态、IP 地址和 VLAN（注意设备类型，如交换机和无线控制器查询方式不同）
  - 返回终端查询结果（状态、IP、VLAN）
  - 根据用户进一步请求，搜索内部文档（如 Obsidian、飞书）获取 VLAN 的权限信息
  - 返回搜索到的权限信息或说明未找到结果
  - 如需更详细排障，提供下一步建议（如查交换机端口、ACL 等）
