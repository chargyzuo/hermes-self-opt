---
name: wechat-mcp-setup-macos
description: 在 macOS 上为 Hermes 配置 WeChat MCP Server（网页协议）
version: 1.0.0
inputs:
  - name: runtime
    description: "运行时（如 bun、python3.12）"
    default: "bun"
triggers:
  - user_request: "安装/配置微信 MCP"
---
# 步骤

1. **安装运行时**（如果未安装）
   - `brew install bun` 或确保 `python3` 可用
2. **安装 WeChat MCP Server**
   - `bunx mcp-wechat-server` 或者 `pip install mcp_server_wechat`（注意 macOS 只能用前者）
3. **配置 Hermes**
   - 编辑 `~/.hermes/config.yaml`，在 `mcp_servers` 下添加：
   ```yaml
     wechat:
       command: bunx
       args: ["mcp-wechat-server"]
       enabled: true
   ```
4. **检查配置格式**（确保 args 为数组而非字符串）
5. **重启 Hermes 或新开会话**以加载新 MCP
6. **扫码登录**
   - 调用 `login_qrcode` 工具生成二维码
   - 使用手机微信扫码
7. **验证连接**
   - 调用 `check_qrcode_status` 确认登录
   - 发送测试消息给机器人账号（不要发给真实联系人）
8. **功能边界告知用户**
   - 此 MCP 仅支持收发新消息，无法查历史聊天记录
   - 需要查历史请提供替代方式（截图/转发/数据库导出）