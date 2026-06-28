# NetBox SSO Authentication Details

## Cookie Architecture

Two sets of cookies in `sso_state.json`:

| Domain | Key Cookie | Purpose | Typical Expiry |
|---|---|---|---|
| `sso.bytedance.com` | `bd_sso_6nskq38`, `bd_sso_sid_c4f15a` | SSO session (WebSSH endpoint auth) | ~1 week |
| `netbox.bytedance.net` | `sessionid`, `csrftoken` | Django session (NetBox API auth) | Same day 18:10 |

The NetBox Django `sessionid` expires quickly (same day at 18:10 local time). When expired, both the API (`/api/dcim/devices/`) and WebSSH (`/ssh/host/`) return 403/connection failure.

The SSO cookies last ~1 week and are the source of truth — they can be used to obtain a fresh NetBox Django session.

## Refresh Workflow

### Step 1: Run Playwright SSO Login

Script: `/Users/bytedance/script/NetDevOps_Byte/tasks/save_auth.py`

**Pitfall**: The original script uses `input()` to wait for the user. This does NOT work with Hermes — `input()` gets EOF in both foreground PTY and background modes, causing the browser to close immediately.

**Fix**: Use `save_auth_v2.py` (file-signal approach) or run interactively outside Hermes. The file-signal version polls for `/tmp/sso_login_done` instead of `input()`:

```python
# Key change:
while not os.path.exists("/tmp/sso_login_done"):
    time.sleep(1)
```

After the user completes SSO in the browser, create the signal:
```bash
touch /tmp/sso_login_done
```

The script then saves to `sso_state.json` in the current directory.

### Step 2: Sync to MCP Switch Location

The switch MCP server reads from `/Users/bytedance/mcp/switch/sso_state.json`. After refreshing:

```bash
cp /Users/bytedance/script/NetDevOps_Byte/tasks/sso_state.json /Users/bytedance/mcp/switch/sso_state.json
```

### Step 3: Verify

Use `get_device_ip.py` to verify the API works:
```bash
cd /Users/bytedance/script/NetDevOps_Byte/tasks
python3 get_device_ip.py "DEVICE_NAME"
```

Then test switch login via MCP:
```
mcp_switch_switch_execute(ip="<managementip>", commands=["dis version", "quit"])
```

## get_device_ip.py

Quick device-name-to-IP resolution without manual API calls:

```bash
cd /Users/bytedance/script/NetDevOps_Byte/tasks
python3 get_device_ip.py "CNCAN30-F02-M-S5731-ASW05"
```

This script:
1. Tries NetBox API with SSO cookies
2. Falls back to HTML scraping of the search page
3. Returns the `managementip` value

## File Locations

| File | Purpose |
|---|---|
| `/Users/bytedance/script/NetDevOps_Byte/tasks/sso_state.json` | SSO cookies (source of truth after refresh) |
| `/Users/bytedance/mcp/switch/sso_state.json` | Switch MCP server's copy |
| `/Users/bytedance/script/NetDevOps_Byte/tasks/save_auth.py` | Playwright SSO login (original, uses input()) |
| `/Users/bytedance/script/NetDevOps_Byte/tasks/get_device_ip.py` | Device name → IP resolver |
| `/tmp/netbox_cookie_str.txt` | Legacy cookie file (may be stale, prefer sso_state.json) |
