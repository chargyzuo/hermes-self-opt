# Quick Start: Hermes SessionDB

This is the minimal bootstrap to read Hermes session data.

```python
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))
from hermes_state import SessionDB

db_path = Path.home() / ".hermes" / "state.db"
db = SessionDB(str(db_path), read_only=True)

# List recent sessions
sessions = db.list_sessions_rich(limit=20)
for s in sessions:
    sid = s.get("id", "")
    title = s.get("title", "") or sid[:16]
    started = s.get("started_at", 0)
    if isinstance(started, (int, float)):
        started = datetime.fromtimestamp(started, tz=timezone.utc)
    msg_count = s.get("message_count", 0)
    print(f"{sid[:16]}... | {title[:40]} | {msg_count} msgs")

# Get messages for a specific session
msgs = db.get_messages(sid)
for m in msgs[:5]:
    print(f"[{m['role']}] {str(m.get('content',''))[:80]}")
```

Start from this to verify your session reading works before building any pipeline.
