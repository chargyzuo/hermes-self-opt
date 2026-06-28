---
name: Detect Running Service Before Recommend
version: 1.0.0
description: 在推荐新安装方案前，优先检查用户是否已有正在运行的同功能服务
---

## Steps

1. 当用户询问如何开启某个服务时，先检查历史会话中是否已记录该服务的启动信息。
2. 如果发现用户今日/近期曾启动过类似服务：
   - 查询具体进程状态（端口/进程ID/启动时间）。
   - 确认服务是否仍在运行中（如 `ps aux | grep <service>` 或 `curl localhost:<port>`）。
3. 若服务仍在运行：
   - 直接提供访问地址（如 `http://localhost:<port>`）。
   - 附上状态查看/停止/重启命令。
4. 若服务未运行或从未启动过，再提供标准安装方案。

## Triggers
- 用户问 "如何开启..." 
- 用户问 "今天不是打开过...吗"
- 用户提及 "本地"、"网页端"、"dashboard" 等关键词