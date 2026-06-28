---
name: mcp-server-install
description: "Install, configure, and troubleshoot third-party MCP servers in Hermes Agent — npm/Bun packages and PyPI modules that provide external tool capabilities (messaging, databases, APIs)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [mcp, servers, configuration, hermes, setup, integration]
    related_skills: [hermes-agent]
---

# MCP Server Installation (Third-Party Packages)

This skill covers installing MCP servers published on npm or PyPI into Hermes Agent. These are pre-built servers that bridge messaging platforms, databases, APIs, and web services — as opposed to self-written FastMCP Python scripts.

## Decision: npm vs PyPI

| Package format | How to run | Look for |
|----------------|------------|----------|
| **npm / Bun** | `bunx <package>` or `npx <package>` | TypeScript/Node.js repos, `package.json` |
| **Python (pip)** | `python3 -m <module>` | Python repos, `pyproject.toml`, `requirements.txt` |

If a repo has both, prefer Bun/npm for simpler lifecycle (auto-cache, no venv management).

## Workflow

### 1. Discover MCP Servers

Search GitHub for `<keyword> mcp server`. Key quality signals:
- Stars > 30
- Clear README with tool list and config examples
- MIT or Apache license
- Recent commits (< 12 months)

### 2. Check Runtime Requirements

```bash
which bun      # Bun runtime (brew install oven-sh/bun/bun if missing)
which npx      # For npm packages without bun
python3 --version  # For Python packages
```

### 3. Add to Hermes Config

**For Bun/npm packages:**
```yaml
mcp_servers:
  <server-name>:
    command: bunx       # or npx
    args:
      - <npm-package-name>
    enabled: true
```

**For Python packages (pip-installed):**
```yaml
mcp_servers:
  <server-name>:
    command: python3
    args:
      - -m
      - <module_name>
    enabled: true
```

### 4. Test Connection

```bash
hermes mcp test <server-name>
```

Expected success:
```
✓ Connected (Xms)
✓ Tools discovered: N
  <tool1>     <description>
```

### 5. (If Needed) Authenticate

Some MCP servers expose login tools (e.g. `login_qrcode`, `check_qrcode_status`). Use them in-session to authenticate.

**QR code lifecycle**: QR codes expire after ~2-3 minutes. If the user says "expired", call `login_qrcode` again to generate a fresh one. Display the terminal QR with `cat ~/.../qrcode.txt` so the user can scan immediately.

### 6. Verify Tools Are Available

After config + auth, start a **new session** (`/new` in CLI, or exit and re-run `hermes`). MCP tools are only discovered at process startup — `hermes mcp test <name>` confirms the connection, but the tools don't appear in the current session's tool registry until restart.

```bash
# Test connection (works in any session)
hermes mcp test <server-name>

# Verify tools are callable — try the simplest tool
# e.g. for wechat: mcp_wechat_check_qrcode_status
```

## 🚨 Critical Pitfalls

### 1. `args` Must Be YAML List, NOT String

This is the #1 mistake. `hermes config set mcp_servers.<name>.args '["..."]'` stores the value as a YAML **string**. The MCP client requires a list.

```yaml
# ✓ Correct
mcp_servers:
  wechat:
    args:
      - mcp-wechat-server

# ✗ Wrong — hermes mcp test fails with:
# "Input should be a valid list"
mcp_servers:
  wechat:
    args: '["mcp-wechat-server"]'
```

**Fix**: Edit `~/.hermes/config.yaml` directly. Change the `args:` line from string to YAML list format.

### 2. macOS Incompatibility: pywin32

`mcp_server_wechat` (PyPI) depends on `pywin32` — a Windows-only library. On macOS, `pip install` fails with:
```
ERROR: Cannot install ... because these package versions have conflicting dependencies.
The conflict is caused by: pywechat127 ... depends on pywin32>=308
```

**Workaround**: Use the Bun/npm-based alternative (e.g. `mcp-wechat-server`) instead.

### 3. `bunx` Auto-Installs

No manual `npm install` needed. `bunx <pkg>` automatically downloads from npm and caches it.

### 4. Authentication Persists

MCP servers that use file-based login state (e.g. `~/.mcp-wechat-server/account.json`) keep credentials across Hermes sessions. No re-login needed after initial scan.

### 5. Runtime Environment

MCP servers run as subprocesses of Hermes. They see the same environment (PATH, home directory) as the Hermes process. For Python packages, dependencies must be installed in the system Python or an active venv.
