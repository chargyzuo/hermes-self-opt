# Delegation + MCP Pattern: Hermes -> agy -> Switch

## Architecture

```
┌─ 本机 (Mac, 国内直连) ─────────────────────────┐
│  Hermes (DeepSeek)                             │
│    ├─ delegate_task → 子agent (script -q agy)  │
│    └─ MCP: config.yaml → switch_mcp_server.py  │
└────────────────────────────────────────────────┘
         ↓ SSH (文本流量, 轻量)
┌─ 海外 VPS (Tokyo, VPN) ────────────────────────┐
│  agy CLI (Gemini Pro)                          │
│    └─ MCP: ~/.gemini/config/mcp_config.json     │
│         → switch_mcp_server.py                 │
└────────────────────────────────────────────────┘
         ↓ Netbox WebSSH Proxy
┌─ 华为交换机 ────────────────────────────────────┐
│  display interface brief, display arp, etc.    │
└────────────────────────────────────────────────┘
```

## When to Delegate to agy

| 场景 | 推荐 | 原因 |
|---|---|---|
| 需要 Gemini Pro 推理 | agy | 用户无法直接访问 Gemini API |
| 简单配置修改 | Hermes 直接做 | 少一次 round-trip |
| 交换机查询 | Hermes 或 agy 均可 | 两个 MCP 都能连 switch |
| 代码生成+执行 | agy | Gemini Pro 更适合生成, 子agent 隔离执行 |
| 配额/成本查询 | agy (/usage) | agy 独有的 slash command |

## Dual MCP Config Maintenance

两个 agent 各自维护自己的 MCP 配置：

**Hermes**: `~/.hermes/config.yaml` (mcp_servers 段)
**agy**: `~/.gemini/config/mcp_config.json` (mcpServers 段)

同一条 MCP server 需要同时写入两个文件才能被两个 agent 共用。

格式对照：
```yaml
# Hermes config.yaml
mcp_servers:
  switch:
    command: python3
    args: [/Users/bytedance/mcp/switch/switch_mcp_server.py]
    enabled: true
```

```json
// agy mcp_config.json
{
  "mcpServers": {
    "switch": {
      "command": "python3",
      "args": ["/Users/bytedance/mcp/switch/switch_mcp_server.py"],
      "env": {}
    }
  }
}
```

## Delegation Invocation Pattern

```python
delegate_task(
    goal="Use agy to <task description>",
    context=(
        "The user wants to check switch status. "
        "Run: script -q /dev/null agy -p 'USE the switch_execute MCP tool...' --print-timeout 120s"
    ),
    toolsets=["terminal", "file"]
)
```

Key points:
- 总用 `script -q /dev/null` 包装（agy 需要 TTY 但 Hermes terminal 不提供）
- `--print-timeout` 设足（一般 60-120s 给 switch 命令)
- 子 agent 只有 terminal+file 工具, 不需要 browser/web
