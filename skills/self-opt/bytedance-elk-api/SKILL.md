---
name: bytedance-elk-api
description: Access ByteDance ELK (itelk.bytedance.net) Kibana/Elasticsearch APIs behind SSO proxy. Covers auth flow, working endpoints, curl templates, and pitfalls.
tags: [elk, kibana, elasticsearch, bytedance, itelk, api]
---

# ByteDance ELK API Access

Access the internal ELK stack at `https://itelk.bytedance.net` programmatically via curl or Python. This stack sits behind both an SSO reverse proxy AND Kibana's native authentication.

## Architecture

```
Client → SSO Proxy (sso.bytedance.com) → Kibana (6.8.0) → Elasticsearch
         └─ sso_user cookie           └─ sid cookie       └─ console proxy
```

Two-layer auth required:
1. **SSO proxy layer** — needs `sso_user` cookie from SSO state
2. **Kibana native auth** — `POST /api/security/v1/login` returns `sid` cookie

## Trigger

Use this skill when the user asks to:
- Query Elasticsearch logs from itelk.bytedance.net
- Access Kibana APIs programmatically
- Search ELK data for devices, errors, or logs
- Set up ELK API automation or cron jobs

## Auth Flow

### Prerequisites

- SSO session file: `/Users/bytedance/script/NetDevOps_Byte/tasks/sso_state.json`
- Kibana credentials (user: `zuojiajie.dcsl` by default)

### Step 1: Obtain SSO Cookies

SSO cookies are obtained via Playwright with the SSO state file. This is a one-time browser flow that sets the `sso_user` cookie on `itelk.bytedance.net`.

```python
from playwright.sync_api import sync_playwright

state_file = "/Users/bytedance/script/NetDevOps_Byte/tasks/sso_state.json"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=state_file)
    page = context.new_page()
    page.goto("https://itelk.bytedance.net/s/network/app/kibana/app/discover")
    # SSO redirects auto-handled; extract cookies after:
    cookies = context.cookies()
    sso_cookie = next(c['value'] for c in cookies 
                      if c['name'] == 'sso_user' and 'itelk' in c['domain'])
```

### Step 2: Login to Kibana

```bash
# Login — returns 204 on success, sets sid cookie
curl -sk -c /tmp/elk_cookies.txt \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
  -d '{"username":"zuojiajie.dcsl","password":"<password>"}' \
  'https://itelk.bytedance.net/api/security/v1/login'
```

But typically you combine both cookies from Playwright in one curl call:

```bash
# Full auth: sso_user (from SSO) + login to get sid
curl -sk -b 'sso_user=<value>' -c /tmp/elk_sid.txt \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
  -d '{"username":"zuojiajie.dcsl","password":"<password>"}' \
  'https://itelk.bytedance.net/api/security/v1/login'
```

Then use both cookies for subsequent API calls:
```bash
COOKIES="sso_user=<value>; sid=<value>"
```

### Step 3: Verify Auth

```bash
curl -sk -b "$COOKIES" -H 'kbn-xsrf: true' \
  'https://itelk.bytedance.net/api/security/v1/me'
# Returns: {"username":"zuojiajie.dcsl","roles":["network_read","so_reader"],...}
```

## Working API Endpoints

All paths are relative to `https://itelk.bytedance.net`. The `/api/*` prefix is universal — do NOT use `/s/network/app/kibana/api/*` (returns 404).

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/api/status` | GET | 200 | Kibana health |
| `/api/security/v1/login` | POST | 204 | Auth, sets `sid` cookie |
| `/api/security/v1/me` | GET | 200 | Current user info |
| `/api/saved_objects/_find?type=index-pattern` | GET | 200 | List index patterns |
| `/api/saved_objects/_find?type=search` | GET | 200 | List saved searches |
| `/api/saved_objects/_find?type=dashboard` | GET | 200 | List dashboards |
| `/api/saved_objects/_find?type=visualization` | GET | 200 | List visualizations |
| `/api/spaces/space` | GET | 200 | List spaces (network, ct, etc.) |
| `/api/console/proxy?path=_search&method=POST` | POST | 200 | **ES search queries** |
| `/api/stats` | GET | 200 | Kibana metrics |
| `/api/xpack/v1/info` | GET | 200 | X-Pack license info |

### Elasticsearch Search via Console Proxy

The primary way to query logs:

```bash
curl -sk -b "$COOKIES" \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "query_string": {
        "query": "\"EGCAI02-F04-M-121G-SPOKE01\" AND \"power\""
      }
    },
    "size": 10,
    "sort": [{"@timestamp": "desc"}]
  }' \
  'https://itelk.bytedance.net/api/console/proxy?path=_search&method=POST'
```

For time-range queries (last 7 days):
```bash
curl -sk -b "$COOKIES" \
  -H 'kbn-xsrf: true' -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "bool": {
        "must": [{"query_string": {"query": "\"device-name\" AND \"error\""}}],
        "filter": [{"range": {"@timestamp": {"gte": "now-7d", "lte": "now"}}}]
      }
    },
    "size": 50
  }' \
  'https://itelk.bytedance.net/api/console/proxy?path=_search&method=POST'
```

## Permissions

Current user (`zuojiajie.dcsl`) has roles:
- `network_read` — search access to ES
- `so_reader` — read-only access

**Forbidden (403):**
- `/api/console/proxy?path=_cat/indices` — needs `monitor` role
- `/api/console/proxy?path=_cluster/health` — needs `monitor` role

## Pitfalls

### Wrong API path prefix

❌ `/s/network/app/kibana/api/status` → 404
✅ `/api/status` → 200

The Kibana SPA routing intercepts everything under `/s/network/app/kibana/`. API calls must use the bare `/api/*` prefix.

### write_file truncates @ in passwords

When using `write_file` to create Python scripts containing passwords with `@`, the tool may truncate the line at the `@` character, writing something like `PASSWORD="Zjj1...` instead of the full password. **Fix**: after `write_file`, use `patch` to correct the specific line:

```python
# After write_file produced truncated line, fix it:
patch(path="/tmp/script.py",
      old_string='p.fill("Zjj1...',  # the truncated result
      new_string='p.fill("Zjj10157924@")')  # full password
```

Always verify with `read_file` after `write_file` that the password line is intact.

### Kibana version-specific paths

Kibana 6.8.0 uses these API paths. Newer Kibana versions (7.x+) may use different paths or require additional headers. Always probe with `/api/status` first to determine version.

### SSO session expiry

The SSO `sso_user` cookie expires periodically. If API calls start returning the Kibana login page (HTML instead of JSON), the SSO session has expired. Re-run the Playwright SSO flow to refresh.

## Verification

After setup, verify with:
```bash
curl -sk -b "$COOKIES" -H 'kbn-xsrf: true' \
  'https://itelk.bytedance.net/api/status' | python3 -m json.tool | head -10
```

Expected output: `"name": "kibana"`, `"version": {"number": "6.8.0", ...}`, `"state": "green"`
