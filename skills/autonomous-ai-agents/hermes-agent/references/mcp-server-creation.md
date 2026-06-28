# Custom MCP Server Creation (FastMCP Pattern)

## Skeleton

```python
#!/usr/bin/env python3
import os, sys
from typing import Annotated
from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mcp = FastMCP("my-server")

@mcp.tool()
def my_tool(
    arg: Annotated[str, "Description shown to the LLM"] = "default",
) -> str:
    """Tool description — keep concise, mention typical use cases."""
    return "result"

if __name__ == "__main__":
    mcp.run()
```

## Pre-existing Library Wrapping Patterns

### Problem: hardcoded default file paths

Your library does `open("sso_state.json")` relative to CWD. The MCP subprocess inherits Hermes' CWD (~/.hermes or user home), not your script's directory.

**Fix: monkey-patch the default at import time.**

```python
import my_library

_STATE_FILE = os.environ.get("STATE_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "state.json"
)

_original_load = my_library.load_state
def _patched_load(path=None):
    return _original_load(path or _STATE_FILE)
my_library.load_state = _patched_load

from my_library import do_work  # import AFTER patching
```

**Alternative: env var.** Set `env: {STATE_PATH: "/abs/path"}` in `mcp_servers` config and read `os.environ.get("STATE_PATH")` in the server.

### Problem: interactive input()/getpass.getpass()

Library calls `input()` or `getpass.getpass()` — these hang in stdio MCP mode because stdin is the JSON-RPC transport.

**Fix 1: environment variables for credentials.**

```python
# In MCP server
u = os.environ.get("MY_USERNAME", "")
p = os.environ.get("MY_PASSWORD", "")
result = library.do_work(username=u, password=p)
```

Then in Hermes config:
```yaml
mcp_servers:
  my-server:
    command: python3
    args: ["/path/to/server.py"]
    env:
      MY_USERNAME: "admin"
      MY_PASSWORD: "***"
```

**Fix 2: monkey-patch input()/getpass before import.**

```python
import builtins
builtins.input = lambda _="": os.environ.get("CREDS", "")
import getpass
getpass.getpass = lambda _="": os.environ.get("CREDS", "")
```

## Registration in Hermes

```bash
# Non-interactive: pipe 'Y' to accept the tool-enable prompt
echo 'Y' | hermes mcp add my-server --command python3 --args /abs/path/to/server.py

# Verify
hermes mcp test my-server

# Tools appear as: mcp_my_server_my_tool (hyphens → underscores)
```

## Config Gotcha: args must be YAML list, not string

`hermes config set` stores values as YAML scalars. For `args`, MCP's `StdioServerParameters` requires a Python `list[str]`:

```yaml
# ✓ Correct — YAML list
mcp_servers:
  switch:
    command: python3
    args:
      - /path/to/server.py

# ✗ Wrong — YAML string (hermes config set stores it as literal string)
mcp_servers:
  switch:
    command: python3
    args: '["/path/to/server.py"]'

# ✗ Wrong — YAML dict (hermes config set mcp_servers.switch.args.0 stores as {'0': '...'})
mcp_servers:
  switch:
    command: python3
    args:
      '0': /path/to/server.py
```

**Always use `hermes mcp add` for initial registration.** The `hermes mcp` subcommands handle YAML serialization correctly. If you accidentally broke the config with `hermes config set`, do `hermes mcp remove <name>` then `hermes mcp add` again.

## Testing During Development

```bash
# Quick smoke test: send tools/list via stdin
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 server.py 2>/dev/null

# Full validation through Hermes
hermes mcp test <server-name>
```

Note: the smoke test will show an init-error response because FastMCP expects a proper `initialize` handshake first, but it confirms the server at least starts without crashing.

## Common Pitfalls

- **ModuleNotFoundError in sandbox**: The server runs from your system Python, not Hermes' sandbox. Dependencies need to be installed globally or in a venv that `python3` resolves.
- **CWD surprises**: The MCP process inherits Hermes' CWD. Use absolute paths or resolve relative to `__file__`.
- **State files**: If your library uses `sso_state.json` or similar relative paths, make them absolute via env var or monkey-patch before any function calls.
- **Timeout**: Switch/network commands can take 10-30 seconds. Set `timeout: 60` or higher in the mcp_servers config. Default is 120s but err on the high side for slow devices.
