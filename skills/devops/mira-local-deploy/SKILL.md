---
name: mira-local-deploy
description: "Deploy and troubleshoot Mira (字节内部 AI Agent) local computer-use capabilities on macOS — miramcp installation, desktop client vs web differences, bridge connectivity, and common pitfalls."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [mira, bytedance, mcp, local, troubleshooting, deployment]
---

# Mira Local Deployment & Troubleshooting

Mira is ByteDance's internal AI agent (mira.byteintl.net / mira.bytedance.com). This skill covers enabling local file/command access so Mira can operate on the user's Mac.

## Two Paths to Local Access

### Path A: Desktop Client "Use My Computers" (Recommended)

The desktop client (≥ 0.80.6, download from mira.bytedance.com) has BUILT-IN local computer-use support. This is DIFFERENT from manually configuring custom MCP on the web version.

**Setup:**
1. Install/upgrade desktop client to ≥ 0.80.6
2. Settings (bottom-left) → "Connect this computer" → Toggle "Let Mira use this computer" ON
3. Wait for green "Connected" status
4. Start a NEW chat → enable the "Use My Computers" toggle IN the chat input area
5. Ask Mira to do local tasks

**How it works under the hood:**
- Desktop client auto-launches `miramcp` as a child process on port 9801
- Config stored at `~/.miramcp/config.json` with only `device_id` (hardware-derived UUID) and `session_id` (JWT)
- Do NOT manually edit config.json — the desktop client manages it
- The `device_id` is a UUID like `db222b4e-49b2-51e0-af99-04a0a8a9f393`, NOT the user-supplied `--device-id`

### Path B: Web Version + Manual MCP (Legacy / Alternative)

Only use this if the desktop client is not available. Requires manual `miramcp` CLI setup.

**Install:**
```bash
curl -sSL "https://blade.byteintl.net/v1/admin/obj/bsave-agent-mycis/mira_agent_boostrap.sh" | bash
```

**Run:**
```bash
source ~/.miramcp/env && miramcp run --device-id <custom-name>
```

**Configure in Mira Web (mira.byteintl.net):**
Settings → Custom MCP → Add:
- Transport: HTTP
- Server URL: `https://mira.byteintl.net/bridge/mcp`
- Headers:
  - `x-mira-device-id`: the ACTUAL device_id from `~/.miramcp/config.json` (not the --device-id flag)
  - `x-mira-user-id`: user's 工号 (from JWT `uid` field)

## Critical Pitfalls

### 1. device-id Mismatch
The `--device-id` flag on `miramcp run` is IGNORED for bridge registration. The actual device_id is a hardware-derived UUID stored in `~/.miramcp/config.json`. ALWAYS check the config file for the real device_id:

```bash
cat ~/.miramcp/config.json | python3 -c "import json,sys; print(json.load(sys.stdin)['device_id'])"
```

### 2. Desktop Client Overwrites Config
When the desktop client launches, it OVERWRITES `~/.miramcp/config.json` with its own device_id and session. If you manually configured miramcp, the desktop client will wipe your MCP array.

### 3. Port 9801 Conflict
Both manual `miramcp run` and the desktop client's built-in miramcp use port 9801. Only ONE can run. If the desktop client is using "Use My Computers", STOP any manual `miramcp run` process.

### 4. Web vs Desktop "Connect" Are Different
- Desktop client "Connected" green dot = local agent is registered with bridge
- Web custom MCP "Connect" button = tests tools/list via bridge HTTP endpoint
- Desktop client's "Use My Computers" toggle IN THE CHAT is separate from settings

### 5. Session Expiry
If the bridge shows connected but tools fail, delete `session_id` from `~/.miramcp/config.json` and restart to force a new QR scan:
```bash
python3 -c "import json; d=json.load(open('$HOME/.miramcp/config.json')); d.pop('session_id',None); json.dump(d, open('$HOME/.miramcp/config.json','w'), indent=2)"
```

### 6. x-mira-user-id Must Match JWT uid
The `uid` in the QR-scan JWT becomes the authenticated user. Use this value:
```bash
python3 -c "import json,base64; d=json.load(open('$HOME/.miramcp/config.json')); p=d['session_id'].split('.')[1]; p+='='*(-len(p)%4); print(base64.urlsafe_b64decode(p))"
```

## Troubleshooting Flow

```
Device shows "offline" in chat?
  → Is "Use My Computers" toggle ON in the chat? (not just settings)
  → Is miramcp running? `ps aux | grep miramcp`
  → Is bridge connected? Check terminal for "[Client] connected to wss://..."
  → Device-id match? Compare config.json device_id ↔ Mira web header
  → Port conflict? Only ONE miramcp on 9801 (desktop OR manual, not both)
  → Session valid? Decode JWT, check exp > now

MCP Connect fails (web)?
  → Is manual miramcp running? (desktop client may have killed it)
  → Is desktop client's miramcp on 9801? They conflict
  → Stale session? Delete session_id, restart, re-scan

Desktop client "Connected" but chat fails?
  → Did you enable "Use My Computers" IN the chat? (separate toggle)
  → Start a NEW chat after enabling in settings
```

## Key Paths & Files

| Path | Purpose |
|------|---------|
| `~/.miramcp/config.json` | device_id, session_id, MCP configs |
| `~/.miramcp/env` | PATH setup for miramcp CLI |
| `~/.miramcp/security.json` | Sandbox security policy |
| `~/Library/Application Support/net.byteintl.mira/logs/mira.log` | Desktop client logs |
| `/Applications/Mira.app` | Desktop client binary |
