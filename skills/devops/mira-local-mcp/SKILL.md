---
name: mira-local-mcp
description: "Deploy and troubleshoot Mira local MCP (miramcp) on macOS — install, configure in Mira web, diagnose device-id mismatches, and verify connectivity."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [mira, bytedance, mcp, local, deployment]
---

# Mira Local MCP Deployment

让字节跳动内部 AI Agent「Mira」通过本地 MCP 桥接操作 macOS 文件系统、执行终端命令。

## 架构

```
Mira 网页端 (mira.byteintl.net)  ←→  miramcp 桥接进程  ←→  本地 Mac
(云端 Agent)                         (127.0.0.1:9801)        (文件/命令)
```

## 前置条件

- 字节跳动内网 + 飞书账号
- Node.js v20+
- macOS

## 部署步骤

### Step 1：安装 miramcp

```bash
curl -sSL "https://blade.byteintl.net/v1/admin/obj/bsave-agent-mycis/mira_agent_boostrap.sh" | bash
```

**⚠ 必须在真实终端中运行**（PYTHON 或非 TTY 环境只能输出 wrapper 不会实际安装）。

安装内容：
- `miramcp` 二进制 → `~/.local/bin/`
- 内置 MCP (`mira_local`) → `~/.local/bin/miramcp_pkg/builtin_mcp/mira_local_mcp.js`
- 配置文件 → `~/.miramcp/config.json`
- 环境文件 → `~/.miramcp/env`

### Step 2：启动桥接服务

```bash
source ~/.miramcp/env && miramcp run --device-id <自定义设备码>
```

首次运行会弹出二维码，用飞书扫码登录。二维码 5 分钟过期。

后续启动直接 `miramcp run` 即可（已记住 device-id 和 session）。

**不要关掉这个终端**，它是守护进程。

### Step 3：在 Mira 网页端配置自定义 MCP

1. 打开 https://mira.byteintl.net/ → Settings → Custom MCP → Add
2. 填写：

| 字段 | 值 |
|------|-----|
| Name | `localmac`（纯英文） |
| Transport Type | `HTTP` |
| Server URL | `https://mira.byteintl.net/bridge/mcp` |
| JWT | 关闭 |

3. 添加两个 Custom Header：

| Key | Value |
|-----|-------|
| `x-mira-device-id` | **从 `~/.miramcp/config.json` 读取 `device_id` 字段**（UUID 格式，不是自定义的 device-id） |
| `x-mira-user-id` | 你的工号（可用 `lark-cli contact +search-user --query "你的名字" --as user` 查） |

4. Connect 保存

### Step 4：启用 Connector

Mira 聊天界面输入框附近有 Connectors 开关，确保 `localmac` 已启用。

## 故障排查

### Mira 提示"设备离线"

**根因：`x-mira-device-id` 填错了。** miramcp bootstrap 会生成 UUID 格式的 device_id 写入 `~/.miramcp/config.json`，和你命令行传的 `--device-id` 不一样。

修复：
```bash
cat ~/.miramcp/config.json | grep device_id
```
把输出的 UUID 填到 Mira MCP header 的 `x-mira-device-id`。

### MCP 工具列表为空 / tools/list failed

1. 确认 `miramcp` 进程在跑：`ps aux | grep miramcp`
2. Mira 网页端 MCP 配置三个关键值都对
3. Mira 聊天页 Connectors 已开启
4. 重启 Mira 页面

### 大模型不会自动调用本地工具

在 prompt 里加前缀：`用 compute use 工具，帮我 xxx`

## 内置工具

| 工具 | 说明 |
|------|------|
| `mira_local_bash` | 同步执行 bash 命令 |
| `mira_local_bash_start` | 后台启动长时间命令 |
| `mira_local_bash_read_output` | 按增量读取后台命令输出 |
| `mira_local_bash_interact_process` | 向会话写入 stdin 或发信号 |
| `mira_local_bash_close_session` | 关闭后台会话 |
| `mira_local_bash_list_sessions` | 列出所有会话 |
| `mira_local_read_file` | 读取本地文件（PDF/docx/xlsx/txt） |
| `mira_local_security_config` | 读写安全策略配置 |

## 安全策略

默认沙盒（`~/.miramcp/config.json` 中 `sandbox` 字段）：

| 约束 | 值 |
|------|-----|
| 允许写入 | `$HOME`, `/tmp` |
| 禁止读写 | `.ssh`, `.gnupg`, `.aws`, `Library/Keychains` |
| 高危命令拦截 | `rm -rf /`, fork bomb, curl \| bash 等 |
| 网络限制 | 关闭 |
| GUI 访问 | 关闭 |

可通过 `mira_local_security_config` 工具或直接编辑 `~/.miramcp/security.json` 调整。
