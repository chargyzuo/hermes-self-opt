---
name: hermes-extension-dev
description: Build Hermes Agent extensions and plugins — CLI subcommand registration, SessionDB integration, auxiliary LLM client, and Hermes internals patterns.
---

# Hermes Extension Development

Pragmatic patterns for building Python packages that extend Hermes Agent with new CLI commands, SessionDB integration, and auxiliary LLM calls.

## When to Use

- Adding a new `hermes <subcommand>` to the CLI
- Reading from Hermes Session DB (SQLite + FTS5)
- Calling auxiliary LLM for side tasks (mining, judging, distilling)
- Building an independent pip-installable package that integrates with Hermes

## CLI Subcommand Registration

Add a `hermes <subcommand>` by creating two files:

### 1. Bridge file: `hermes_cli/subcommands/<name>.py`

```python
from __future__ import annotations
from typing import Callable

def build_<name>_parser(subparsers, *, cmd_<name>: Callable) -> None:
    from <your_package>.cli import build_<name>_parser as _build
    _build(subparsers, cmd_<name>=cmd_<name>)
```

### 2. Register in `hermes_cli/main.py`

```python
# Add import at top of file with other subcommand imports
from hermes_cli.subcommands.<name> import build_<name>_parser

# Define handler function (near other cmd_* handlers)
def cmd_<name>(args):
    from <your_package>.cli import handle_<name>
    sys.exit(handle_<name>(args))

# Register parser in main()
build_<name>_parser(subparsers, cmd_<name>=cmd_<name>)
```

### 3. Install as pip package in Hermes venv

```bash
source ~/.hermes/hermes-agent/venv/bin/activate
pip install -e ~/script/<your-package>
```

## SessionDB Interaction

Hermes stores sessions in `~/.hermes/state.db` (SQLite + FTS5).

### Common APIs

```python
from hermes_state import SessionDB

# Read-only access
db = SessionDB(str(db_path), read_only=True)

# List recent sessions (returns list of dicts with id, started_at, message_count, title, etc.)
sessions = db.list_sessions_rich(limit=20)

# Get all messages for a session
messages = db.get_messages(session_id)

# Each message: dict with role, content, timestamp, tool_calls, etc.
# role is "user" | "assistant" | "tool"
```

### Pitfalls

- **`started_at` is a float timestamp**, not a string. Use `datetime.fromtimestamp(val, tz=timezone.utc)`.
- **`get_messages()` returns `role: "tool"` entries** — filter them out when building dialog for LLM. Tool messages contain command output, base64 images, and API responses that waste tokens.
- **Use `read_only=True`** when only reading — avoids write locks on the live DB.
- There is NO `get_recent_sessions()` function. Use `list_sessions_rich()` or `search_sessions()`.

## Auxiliary LLM Client

Hermes provides `agent.auxiliary_client.call_llm()` for side tasks (mining, judging, distilling). This runs on a separate provider configured under `auxiliary:` in config.yaml.

### Usage

```python
from agent.auxiliary_client import call_llm

messages = [{"role": "user", "content": prompt}]
response = call_llm(task="default", messages=messages)
if hasattr(response, "choices"):
    text = response.choices[0].message.content or ""
```

### Pitfalls

- `call_llm()` is a **function**, not a class. There is no `get_auxiliary_client()`.
- `task="default"` reads from `auxiliary.default` config. If not configured, it falls back to the main provider.
- LLM responses often contain **invalid JSON escapes** (e.g. `\_`). Always wrap `json.loads()` with a repair step:
  ```python
  import re
  fixed = re.sub(r'\\(?!["\\/bfnrtu])', '\\\\', raw_json)
  result = json.loads(fixed)
  ```
- For robustness, add a fallback that strips all escapes:
  ```python
  stripped = re.sub(r'\\(.)', r'\1', raw_json)
  ```

## Package Structure

```
<your-package>/
├── pyproject.toml
├── hermes_<name>/
│   ├── __init__.py
│   ├── cli.py       # build_*_parser + handle_* functions
│   └── core.py      # business logic modules
```

- Keep the Hermes bridge file (`hermes_cli/subcommands/<name>.py`) **inside Hermes repo** — it delegates to your package via import
- Your package lives **in its own repo** — independent versioning, no merge conflicts with upstream Hermes

## Design Principle: "能跑就行"

"Make it work, then make it better." Prioritize:

1. **Simple keyword matching over complex ML** — a 30-line filter with forward keyword matching beats a 500-line classifier for session triage
2. **Basic checks before LLM calls** — secret detection, length limits, and empty-content checks cost <1ms locally. Don't pay LLM cost for things regex can catch
3. **Pure forward matching for filters** — never use negative keywords to exclude content. A troubleshooting session that mentions "笔记" is still a troubleshooting session. False positives from forward matching are safer than false negatives from reverse exclusion
