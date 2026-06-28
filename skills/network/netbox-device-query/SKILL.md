---
name: netbox-device-query
description: Query NetBox for device info by name, management IP, or IPAM IP address. Read-only (GET only). Returns management IP, model, site, rack, serial, status, and more.
category: network
---

# NetBox Device Query

Query production NetBox (https://netbox.bytedance.net/, v2.5) for device information. **ALL OPERATIONS READ-ONLY — GET requests only. NEVER POST/PUT/PATCH/DELETE.**

## Authentication

NetBox uses SSO-based auth. The canonical credential file is `sso_state.json` (Playwright storage state), NOT `/tmp/netbox_cookie_str.txt` (often stale).

**Preferred approach — use `get_device_ip.py` instead of raw curl:**

```bash
cd /Users/bytedance/script/NetDevOps_Byte/tasks
python3 get_device_ip.py "DEVICE_NAME"
```

This script handles cookie loading, API call, and fallback to HTML scraping automatically. Returns the `managementip` value directly.

**If using curl/requests directly**, load cookies from `sso_state.json` with Python `requests.Session` — the file contains cookies for both `sso.bytedance.com` (SSO session) and `netbox.bytedance.net` (Django session). The Django sessionid expires same-day (18:10 local). If you get 403, the SSO session needs refresh.

**SSO refresh:** see `references/sso-auth.md` for the complete refresh workflow, cookie locations, and pitfalls.

## Query Methods

### 1. By Device Name (exact)

```bash
curl -sS -H "Cookie: $COOKIE" \
  "https://netbox.bytedance.net/api/dcim/devices/?name=<NAME>"
```

### 2. By Device Name (fuzzy, using `q`)

```bash
curl -sS -H "Cookie: $COOKIE" \
  "https://netbox.bytedance.net/api/dcim/devices/?q=<PARTIAL_NAME>"
```

### 3. By Management IP

```bash
curl -sS -H "Cookie: $COOKIE" \
  "https://netbox.bytedance.net/api/dcim/devices/?managementip=<IP>"
```

### 4. Reverse Lookup by IP Address (IPAM)

Find which device an IP belongs to:

```bash
curl -sS -H "Cookie: $COOKIE" \
  "https://netbox.bytedance.net/api/ipam/ip-addresses/?q=<IP>"
```

Then extract `interface.device.name` from results.

### 5. By Other Fields

All supported query params on `/api/dcim/devices/`:
- `serial`, `asset_tag`, `model`
- `site_id`, `site`, `region`, `rack_id`, `position`
- `device_type_id`, `role_id`, `role`, `manufacturer_id`, `manufacturer`
- `department_id`, `platform_id`, `status`, `priority`
- `mac_address`, `has_primary_ip`
- `tenant_id`, `tag`

## Key Return Fields

| Field | Description |
|---|---|
| `name` | Device name |
| `managementip` | Management IP (custom field) |
| `primary_ip4/6` | Primary IP (standard field, often null) |
| `device_type.model` | Hardware model |
| `device_role.name` | Role (Access Switch, etc.) |
| `device_department.name` | Department |
| `site.name` | Site name |
| `rack.name` | Rack name |
| `position` | Rack U position |
| `serial` | Serial number |
| `asset_tag` | Asset tag |
| `status.label` | Status (Active, Planned, etc.) |
| `platform.name` | OS platform (Huawei, Arista, etc.) |

## Common Query Patterns

**Get device detail (single device):**
```
/api/dcim/devices/?name=<EXACT_NAME>
```
Returns `count` and `results[]`. If count=1, extract `results[0]`.

**Get device by ID:**
```
/api/dcim/devices/<ID>/
```
Returns single device object directly (no pagination wrapper).

**List devices at a site:**
```
/api/dcim/devices/?site=<SITE_NAME>&limit=50
```

**Find switch by serial:**
```
/api/dcim/devices/?serial=<SERIAL>
```

**List all access switches at a site:**
```
/api/dcim/devices/?site=<SITE>&role=access-switch
```

## Workflow: Query Device → Log into Switch

When the user asks to log into a switch by name:

1. **Resolve IP via `get_device_ip.py`** (preferred):
   ```bash
   cd /Users/bytedance/script/NetDevOps_Byte/tasks
   python3 get_device_ip.py "DEVICE_NAME"
   ```
   This handles cookie loading and returns the management IP directly.

2. **Show the IP source** — explicitly tell the user "IP from NetBox: managementip = X.X.X.X". Never silently use a previously-cached IP.

3. **Log in via MCP** — use `mcp_switch_switch_execute` with the managementip.

4. **If SSO cookies are expired**, `get_device_ip.py` returns nothing. Run the SSO refresh workflow (see `references/sso-auth.md`), then sync to `/Users/bytedance/mcp/switch/sso_state.json`.

## Pitfalls

- `primary_ip4` is often `null` — use `managementip` field instead
- `interfaces` count on list endpoint is often 0 — use `/api/dcim/interfaces/?device_id=<ID>` to see interfaces
- IPAM reverse lookup: use `/api/ipam/ip-addresses/?q=<IP>` (the `q` param does partial match on address)
- Site names with Chinese characters must be URL-encoded in curl, or use `site_id` (numeric) instead
- The API uses pagination with `limit` and `offset`; default limit is 50
- **SSO cookie expiration**: The `netbox.bytedance.net` Django `sessionid` expires same-day at 18:10. When expired, all NetBox API calls return 403. The SSO cookies (`sso.bytedance.com`) last ~1 week. See `references/sso-auth.md` for the refresh workflow.
- **Cookie location mismatch**: SSO refresh writes to `tasks/sso_state.json`, but the switch MCP reads from `mcp/switch/sso_state.json`. After refresh, copy the file: `cp tasks/sso_state.json mcp/switch/sso_state.json`.
- **`save_auth.py` `input()` pitfall**: The original SSO login script uses `input()` which fails in Hermes (EOFError). Use the file-signal variant or run outside Hermes. See `references/sso-auth.md`.
- **Always show where the IP came from**. When logging into a switch, explicitly state the NetBox query that yielded the managementip. Never use an IP without showing its source — the user needs to see the chain: device name → NetBox → managementip → login.

## Data Scale (June 2026)

- 44,606 devices
- 55,168 interfaces
- 959 sites
- 5,863 racks
- 457 device types

## Supporting Files

- `references/sso-auth.md` — SSO cookie architecture, refresh workflow, `save_auth.py` pitfalls, cookie sync between locations, and `get_device_ip.py` usage.
