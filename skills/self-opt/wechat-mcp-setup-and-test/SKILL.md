---
name: wechat-mcp-setup-and-test
description: 在 macOS 上安装并测试 wechat MCP Server 的完整工作流
steps:
  - 检查操作系统：macOS
  - 检查 Bun：若未安装则使用 brew install bun
  - 配置 MCP：添加 mcp-wechat-server 到 hermes 配置
  - 重新加载 MCP 配置
  - 生成登录二维码：调用 login_qrcode 工具
  - 提示用户扫码登录
  - 确认登录：调用 check_qrcode_status
  - 测试收发：让用户发消息给 chatbot，调用 get_messages 检查接收，再调用 send_text_message 回复确认
  - 记录用户微信 ID 和 chatbot 的基本信息
  - 告知用户聊天记录历史：此 MCP 无法查历史，建议截图/复制转发/使用客户端
