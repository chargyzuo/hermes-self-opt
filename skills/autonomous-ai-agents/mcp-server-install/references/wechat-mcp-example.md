# WeChat MCP Server Setup

This is a concrete example of installing a third-party MCP server into Hermes — bridging WeChat messaging capabilities.

## The MCP Server

**Package**: [`mcp-wechat-server`](https://github.com/Howardzhangdqs/mcp-wechat-server) ⭐94
**Runtime**: Bun (via `bunx mcp-wechat-server`)
**Auth**: QR code scan (WeChat mobile → scan terminal QR)

### Tools Provided

| Tool | Description |
|------|-------------|
| `login_qrcode` | Generate WeChat login QR code |
| `check_qrcode_status` | Check if QR was scanned/confirmed |
| `logout` | Log out and clear credentials |
| `get_messages` | Poll for new messages (long-poll, `wait=true` blocks) |
| `send_text_message` | Send a text message to a WeChat user |
| `send_typing` | Show/cancel "typing..." indicator |

### Config Entry

```yaml
mcp_servers:
  wechat:
    command: bunx
    args:
      - mcp-wechat-server
    enabled: true
```

### Getting Running

1. **Install Bun**: `brew install oven-sh/bun/bun`
2. **Add to config**: Paste the YAML above into `~/.hermes/config.yaml` under `mcp_servers:`
3. **Test**: `hermes mcp test wechat` → should show 6 tools discovered
4. **Login**: Call `mcp_wechat_login_qrcode` → display QR (`cat ~/.mcp-wechat-server/qrcode.txt`) → scan with phone
5. **Check login**: Call `mcp_wechat_check_qrcode_status` → `confirmed`

### Data Storage

All state lives in `~/.mcp-wechat-server/`:
- `account.json` — Bot token and user ID (permissions 600)
- `state.json` — Message cursor and context token
- `qrcode.txt` / `qrcode.png` — QR codes
- Credentials persist across Hermes sessions — no re-login needed after initial scan

### Troubleshooting

**`hermes mcp test wechat` fails with "Input should be a valid list"**
→ `args` was stored as a YAML string. Edit `~/.hermes/config.yaml` and change `args: '["mcp-wechat-server"]'` to:
```yaml
    args:
      - mcp-wechat-server
```

**QR code scan doesn't connect**
→ If phone WiFi can't load the page, switch to mobile data network.
→ Alternatively, send the URL link to yourself in WeChat and open it from there.

**Connection hangs during `hermes mcp test`**
→ First time may take 3-5 seconds for `bunx` to download and cache the package. Subsequent calls are faster.
