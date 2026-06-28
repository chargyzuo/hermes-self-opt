# Hermes Context Length Resolution Chain

When the context progress bar in Hermes shows the wrong max value (e.g. shows 1M but actual limit is 256K), the root cause is almost certainly a mis-resolution in this chain.

## Resolution Order (from `agent/model_metadata.py::get_model_context_length`)

1. **`config_context_length`** (priority 0) — explicit `model.context_length` in `config.yaml`. This is only set at session start or from the `/model` command via `_config_context_length`. **Dropped during `/model` switch**: line 1426 of `agent_runtime_helpers.py` clears `agent._config_context_length = None` on model switch, so the new model resolves from scratch.

2. **`custom_providers` per-model override** (priority 0b) — `context_length` set per-model in a `custom_providers` block.

3. **Persistent cache** (priority 1) — previously discovered via endpoint probing. Stored per `(model, base_url)` pair.

4. **Active endpoint metadata** / **OpenRouter live API** — probes `/v1/models` on the endpoint.

5. **Hardcoded defaults** (priority ~7) — `DEFAULT_CONTEXT_LENGTHS` dict in `model_metadata.py`. **This is the typical culprit** when display is wrong.

6. **Default fallback** (priority 9) — 256K.

## The Common Bug: Hardcoded Default Wins

If `config_context_length` is `None` (cleared on `/model` switch) and no cache/endpoint probe succeeds, the model name is matched against `DEFAULT_CONTEXT_LENGTHS` (case-insensitive, longest-substring-first match). Examples of entries that cause 1M display when actual is 256K:

```python
"deepseek-chat": 1_000_000,       # model_metadata.py:194 — DeepSeek free tier is 256K
"deepseek-reasoner": 1_000_000,     # same issue
"deepseek-v4-flash": 1_000_000,     # V4 flash is 1M on paid, 256K on free
```

These values assume the model's *theoretical maximum* context, not what the user's API tier actually provides.

## How to Fix (in priority order)

### Quick Fix (per-user, immediate)
```bash
hermes config set model.context_length 262144
```
Then `/new` to start a fresh session. This forces priority-0 override.
**But**: `/model` switch clears this (see above), so you'll need to re-set it or use the code fix.

### Proper Fix (per-install, developer)
Edit `/Users/bytedance/.hermes/hermes-agent/agent/model_metadata.py` and change the relevant entry in `DEFAULT_CONTEXT_LENGTHS`:

```python
# Before (line ~194):
"deepseek-chat": 1_000_000,
# After:
"deepseek-chat": 262144,
```

Then restart the session. This survives `/model` switches.

### Reporting to Upstream
If this affects you and you're on a standard tier (free/256K), the hardcoded default should match reality. Open a PR or issue at https://github.com/NousResearch/hermes-agent.

## Tracing the Value at Runtime

1. Check `agent._config_context_length` — `None` means no config override.
2. Check `comp.context_length` on `agent.context_compressor` — this is the actual value used for the progress bar display in `tui_gateway/server.py:1939`.
3. Add a `logger.info(...)` call in `get_model_context_length()` at model_metadata.py:1562 to see what resolution step fires.

## Key Files
- `agent/model_metadata.py` — `get_model_context_length()` + `DEFAULT_CONTEXT_LENGTHS`
- `agent/context_compressor.py` — `ContextCompressor.__init__()` calls `get_model_context_length()`
- `agent/agent_runtime_helpers.py` — `switch_model()` clears `_config_context_length`
- `tui_gateway/server.py` — progress bar reads `comp.context_length`
