# Mira 本地 MCP (miramcp) 部署与排障

Mira 是字节跳动内部 AI Agent（网页端 mira.byteintl.net）。默认只能云端沙盒执行，通过 `miramcp` 本地 MCP 桥接可获得本地文件读写和终端执行能力。

## 概念区分

| 组件 | 角色 | 位置 |
|------|------|------|
| Mira 网页端 | Agent 本体，对话推理 | mira.byteintl.net |
| miramcp | MCP 桥接守护进程，转发工具调用 | 用户本地 Mac |
| mira_local MCP | 内置 MCP（bash 等工具），由 miramcp 启动 | 用户本地 Mac |

**miramcp 不是 Mira agent 的 CLI 版本**，不能 `miramcp chat -q`。它只是桥接，让 Mira 网页端能操作本地。

## 部署步骤

### 前置条件
- Node.js v20+ (`node --version`)
- macOS / Linux / Windows (WSL)
- 内网环境（需访问 blade.byteintl.net 和 mira.byteintl.net）

### Step 1：安装 miramcp

bootstrap 脚本会检查 Node.js、下载 miramcp 二进制、注册内置 MCP。

```bash
curl -sSL "https://blade.byteintl.net/v1/admin/obj/bsave-agent-mycis/mira_agent_boostrap.sh" | bash
```

**TTY 检测坑**：脚本首行有 `if [ ! -t 1 ]; then ... exit 0; fi`，在非交互终端下只输出 wrapper 不实际安装。**必须让用户在真实终端中手动执行**，不要尝试在 Hermes terminal 工具中跑（包括 PTY 模式）。

如果脚本被 TTY 阻塞，手动步骤：
1. 下载 `https://blade.byteintl.net/v1/admin/obj/bsave-agent-mycis/miramcp.tar.gz`（macOS arm64）
2. 解压到 `~/.local/bin/miramcp_pkg/`
3. 复制 `miramcp` 到 `~/.local/bin/`，`chmod 755`
4. 注册内置 MCP：
   ```bash
   miramcp mcp remove mira_local 2>/dev/null || true
   miramcp mcp add '{"id":"mira_local","protocol":"stdio","command":"<node_path>","args":["<pkg_path>/builtin_mcp/mira_local_mcp.js"]}'
   ```
5. 写 `~/.miramcp/env` 添加 PATH

### Step 2：启动桥接

```bash
source ~/.miramcp/env && miramcp run --device-id <自定义设备码>
```

- `device-id`：用户自定，保密。用于后续 Mira 网页端匹配设备。
- 启动后终端弹出二维码，用飞书（内网）扫码登录 Mira 账号。
- 二维码 5 分钟过期，过期重跑即可。
- 成功标志：日志显示 `MCP Proxy on 127.0.0.1:9801`、`connected to wss://mira.byteintl.net/bridge/ws`
- 该命令是**守护进程**，会一直跑着。不要 Ctrl+C。

### Step 3：Mira 网页端配置 MCP

访问 https://mira.byteintl.net/ → 设置 → 自定义 MCP → 添加：

| 配置项 | 值 |
|--------|---|
| Name | 任意英文，如 `localmac` |
| Transport type | `http` |
| Server URL | `https://mira.byteintl.net/bridge/mcp` |
| Header `x-mira-device-id` | 与 Step 2 的 `--device-id` **完全一致** |
| Header `x-mira-user-id` | 用户的**纯数字工号**（不是飞书 ID、不是邮箱） |
| JWT 验证 | **不需要**，留空 |

Description 建议：
```
## 本地 Mac 工具
当用户需要读写本地文件、执行终端命令、操作项目代码时使用。
可用工具：bash, bash_start, bash_read_output
注意：只能操作 ~ 和 /tmp，禁止访问 .ssh/.gnupg/.aws 等敏感目录。
```

## 排障

### 网页端报 "id invalid"
- 确认 `x-mira-device-id` 与 `miramcp run --device-id` 完全一致（大小写、连字符）
- 确认 `x-mira-user-id` 是纯数字工号
- 确认 miramcp 进程还在跑：`ps aux | grep miramcp`

### 网页端显示设备离线
- 确认终端里 `miramcp run` 进程未退出
- 确认日志中有 `connected to wss://mira.byteintl.net/bridge/ws`
- 尝试重启 `miramcp run`，在 Mira 网页端重新启用 MCP

### 截图排查
用户截图是最高效的排障方式。让用户截 Mira 网页端 MCP 配置页 + 终端 `miramcp run` 日志。

## 安全沙盒策略（默认）

```
write_allow_paths: ["/Users/<user>", "/tmp"]
write_deny_paths:  ["~/.ssh", "~/.gnupg", "~/.aws", "~/Library/Keychains"]
read_deny_paths:   ["~/.ssh", "~/.gnupg", "~/.aws"]
```

可通过 `~/.miramcp/config.json` 自定义。

## 相关内部文档

- 《【Mira社区】本地MCP插件: 让 AI 操作你的电脑》(巫建辉) — doc token: R3w6dyHdzoih50xXguFcC9zXn0h
- 《Mira Harness 工程深度解析》(陈国林) — doc token: GVb6dBKIooN0kdxsoktcxgmTnde
- 《【小白版】Mira 本地 MCP 插件》(陈宇浩) — doc token: A4aLdb2kgoCHR0xgkWScOqc9nXf
- Mira 网页端: https://mira.byteintl.net/
- Mira 反馈群: 飞书群 oc_8d8fc798655295ea3545176b27747d31
