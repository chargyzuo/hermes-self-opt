# Knowledge Pipeline Watchdog Pattern

Incremental file-change detection that triggers a Hermes pipeline only when
source files are new or modified. Uses a `no_agent=True` cron job — zero LLM
overhead on unchanged ticks.

## Why

Running `hermes self-opt run-pipeline -y` every N hours processes ALL 80
normal/ documents every time (2+ minutes, heavy). When only 1-2 files change
per week, that's 99% wasted work. The incremental watchdog detects the change
and only processes what's new.

## Pattern

```
cron (every 30 min, no_agent=True)
  → Python script
    → Scan normal/*.md → per-file SHA256 hashes
    → Compare with stored hashes from last run
    → If changed: extract only changed files → distill → gate → commit
    → If unchanged: exit silently (empty stdout = no delivery)
```

## Implementation

**Script**: `~/.hermes/scripts/knowledge-pipeline-watchdog.py`

**Key design decisions**:

1. **Per-file hashes, not single aggregate** — Detects which specific files
   changed. Enables incremental extraction (only changed files pass through
   extract_one() → distill_and_generate()).

2. **No subprocess for the pipeline** — The watchdog imports
   `hermes_self_opt.*` modules directly and calls them on the subset of
   changed files. This avoids CLI overhead and the subprocess timeout.

3. **Hash state on detection, not completion** — Saves after detection so
   subsequent ticks won't re-trigger while the pipeline is still running.

4. **Deleted file cleanup** — Files removed from normal/ are auto-removed
   from the hash registry (in `find_changed`).

5. **Cron: `no_agent=True` + `script="<filename>"`** — The script IS the job.
   Script stdout is delivered verbatim; empty stdout = silent tick. No LLM
   tokens consumed on unchanged runs.

**State files**:
- `~/.hermes/knowledge/self-opt/.normal_hashes.json` — `{relpath: sha256}`
- `~/.hermes/knowledge/self-opt/pipeline_watchdog.log` — timestamped log

## Cron setup

```python
cronjob(
    action="create",
    name="knowledge-pipeline-watchdog",
    schedule="*/30 * * * *",
    no_agent=True,
    script="knowledge-pipeline-watchdog.py",
    deliver="local",
    repeat=-1,   # forever
)
```

## Pitfalls

- **Script timeout**: The cron system has a 120s script timeout. Don't call
  the full pipeline from the script as a subprocess — it will time out.
  Instead, import the Python modules directly and process incrementally.
- **First run**: When `.normal_hashes.json` doesn't exist yet, all files
  appear as "changed". But `distill_and_generate()` deduplicates against
  existing core/ entries, so the first run generates 0 new YAML (all 393
  duplicates) and only takes a few seconds.
- **`extract_one()` vs `extract_all()`**: The watchdog calls `extract_one()`
  on each changed file, not `extract_all()`. This is the key to incremental
  processing.
