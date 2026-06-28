# Hermes Agent Harness Architecture

> Key architectural patterns discovered through code exploration.

## Memory System (Current State)

Hermes memory is **two flat Markdown files**, not a layered CowAgent-style system:

```
~/.hermes/memories/
├── MEMORY.md    (~2.5KB) — Personal notes, split by § delimiter
└── USER.md      (~1.6KB) — User profile / preferences
```

**How it works:**
- Agent uses `memory` tool (add/replace/remove) → direct append to file
- On session start → both files read into system prompt
- No tiered storage, no auto-compression, no expiration
- When full → manual consolidation needed

**Implication:** The CowAgent-style 3-tier memory (Context→Daily→Core with Deep Dream distillation) is not implemented. Phase 3 of the self-optimization plan adds this.

## Session Storage

Hermes `hermes_state.py::SessionDB` (SQLite + FTS5):

### Key API:

```python
from hermes_state import SessionDB

db = SessionDB(str(db_path), read_only=True)

# List sessions (returns list[dict])
sessions = db.list_sessions_rich(limit=20)
# Each session dict keys: id, source, user_id, model, started_at, 
# ended_at, message_count, title (sometimes absent)

# Get messages for a session (returns list[dict])
messages = db.get_messages(session_id)
# Each message dict keys: id, session_id, role, content, tool_call_id,
# tool_calls, tool_name, timestamp, token_count, finish_reason

# Search sessions (FTS5)
results = db.search_sessions(query="keyword", limit=10)
```

### Important Details:
- `started_at` is a **float timestamp** (Unix epoch), not a string
- No `get_recent_sessions()` method — use `list_sessions_rich()` instead
- No `get_session_messages()` — use `get_messages()` instead
- Messages are flat dicts, not objects
- Read-only mode (`read_only=True`) works for query-only operations

## Auxiliary LLM Client

The auxiliary client module at `agent/auxiliary_client.py` exposes a **function**, not a class:

```python
from agent.auxiliary_client import call_llm

response = call_llm(
    task="default",              # or "compression", "vision", etc.
    messages=[{"role": "user", "content": prompt}],
    model="deepseek-chat",       # optional override
)

# Response has .choices[0].message.content
response_text = response.choices[0].message.content
```

**NOT** `get_auxiliary_client()` — that function does not exist.
**NOT** `.chat()` — there is no client object with a chat method.
