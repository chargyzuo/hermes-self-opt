---
name: hermes-prompt-optimization
description: "Diagnose and reduce Hermes Agent's initial system prompt size — a class-level practice covering config tuning, skills indexing, platform env vars, and prompt auditing."
---

# Hermes Prompt Optimization

The initial system prompt (system prompt) is the preamble injected into every
LLM API call. A bloated prompt wastes tokens, fills the context window faster,
and increases latency/cost. This skill covers how to audit, measure, and shrink it.

## Signals / Triggers

- User asks "why is the initial prompt so big" or "reduce the system prompt"
- User wants to lower token consumption per turn
- User needs more context window headroom for long conversations
- Session tokens seem high for simple tasks
- After installing many skills, the prompt suddenly grows

## Architecture — Three Prompt Tiers

The system prompt (built in `agent/system_prompt.py`) has three layers:

| Tier | Contents | Stability |
|------|----------|-----------|
| **Stable** | Identity (SOUL.md/DEFAULT), guidance blocks, skills index, environment hints, platform hints, profile hint, coding context | Session-lifetime cache |
| **Context** | `system_message`, AGENTS.md / .hermes.md / CLAUDE.md / .cursorrules | Per-session |
| **Volatile** | Memory snapshot, user profile, external memory provider block, timestamp/model/provider line | Changes per session-start |

The **skills index** almost always dominates — easily 50–80% of the total prompt
when many skills are installed.

## Diagnosis — Measure First

### Use the audit script

```bash
bash /Users/bytedance/script/check_prompt_size.sh
```

This script builds the system prompt using Hermes internals and prints:
- Total chars and estimated tokens
- Per-block breakdown with percentages
- The actual skills listed in the index

### Live token monitoring in the TUI

While in an active session, use these in-session commands:

| Command | Effect |
|---------|--------|
| `/verbose` | **Cycle toggle** — cycles `off → new → all → verbose → off`. No numeric argument accepted. The "new" and "all" modes show per-message token consumption in the output. |
| `/usage` | Show cumulative token usage for the current session. |

The verbose modes control tool-progress rendering:

| Mode | What it shows |
|------|--------------|
| `off` | Silent — just the final response, no tool calls shown |
| `new` | Only first-time tools calls + token consumption per call |
| `all` | Every tool call + token consumption per call |
| `verbose` | Full args, results, think blocks + token consumption |

**Pitfall:** `/verbose` does NOT accept a numeric argument. `/verbose 2` will error with "unknown verbose mode: 2". Cycle through modes by calling `/verbose` repeatedly.

### Manual check via session export

```bash
# Start a session, send at least one message, exit, then:
hermes sessions export /tmp/session.jsonl
python3 -c "
import json
with open('/tmp/session.jsonl') as f:
    for line in f:
        d = json.loads(line)
        msg0 = d['messages'][0]
        if msg0['role'] == 'system':
            print(f'System prompt: {len(msg0[\"content\"])} chars')
            break
"
```

### CRITICAL: Set HERMES_PLATFORM

When analyzing the prompt programmatically (e.g. via `build_skills_system_prompt`),
the `HERMES_PLATFORM` environment variable MUST be set to match the target platform.
Without it, `get_disabled_skill_names()` cannot resolve the platform-specific
disabled list, and **ALL skills appear in the index** instead of only the enabled ones.

```python
os.environ['HERMES_PLATFORM'] = 'cli'  # or 'telegram', 'discord', etc.
```

This is the #1 gotcha — the `build_skills_system_prompt` cache key includes
the resolved platform, and without it the CLI disabled list is silently ignored.

## Reduction Strategies (highest impact first)

### 1. Disable unnecessary skills on the target platform

The single most effective action. Each skill in the index costs ~100–500 chars
(name + description). Disabling a skill removes it entirely from that platform.

```bash
# Add to config.yaml under skills.platform_disabled.<platform>:
hermes config set skills.platform_disabled.cli '<manual edit — YAML list>'
```

Or edit `~/.hermes/config.yaml` directly:

```yaml
skills:
  platform_disabled:
    cli:
      - skill-name-here
```

### 2. Disable tool-use enforcement guidance (if your model doesn't need it)

The `TOOL_USE_ENFORCEMENT_GUIDANCE` block (~800 chars) is injected when the
model name matches entries in `TOOL_USE_ENFORCEMENT_MODELS` (gpt, codex, gemini,
gemma, grok, glm, qwen, deepseek). For models that already use tools well,
disable it:

```bash
hermes config set agent.tool_use_enforcement false
```

### 3. Disable task-completion guidance

```bash
hermes config set agent.task_completion_guidance false   # ~500 chars
```

### 4. Disable parallel-tool-call guidance

```bash
hermes config set agent.parallel_tool_call_guidance false   # ~400 chars
```

### 5. Disable environment probe

```bash
hermes config set agent.environment_probe false   # ~200 chars
```

### 6. Reduce memory char limit

The memory snapshot can grow up to `memory.memory_char_limit` (default: 2200).

```bash
hermes config set memory.memory_char_limit 500   # cap at 500 chars
```

Or disable memory entirely if not needed:

```bash
hermes config set memory.memory_enabled false
```

## Common Pitfalls

1. **`/verbose` does NOT accept numeric arguments.** It's a cycle toggle:
   `off → new → all → verbose → off`. Calling `/verbose 2` produces
   "error: unknown verbose mode: 2". Cycle by calling the bare `/verbose`
   command repeatedly.

2. **HERMES_PLATFORM not set during analysis.** Without it, the prompt size
   estimate includes ALL skills, not just the platform-enabled ones. Always set
   `HERMES_PLATFORM=cli` (or the relevant platform) when running prompt-size
   analysis scripts.

3. **Disabled list uses frontmatter `name:` field, not directory name.**
   Verify the exact skill name with `head -5 <skill-dir>/SKILL.md` or by
   matching what `hermes skills list` shows in the Name column.

3. **Skills index intro text is mandatory.** The "Skills (mandatory)" intro
   paragraph (~800 chars) cannot be removed without modifying core code; it's
   part of the constant `prompt_builder.py::build_skills_system_prompt()`.

4. **Config changes need /reset or new session.** `agent.*` and `skills.*`
   settings are read at session start / prompt-build time. Changes inside a
   running session are not picked up until `/reset` or a fresh `hermes` client.

5. **Bundled/hub skills cannot be deleted or edited.** Only local (agent-created)
   skills can be modified. Bundled skills are shipped with Hermes; hub skills
   come from the skills catalog.

6. **Naming collision.** If two skills share the same frontmatter `name:`,
   `skill_view` will fail with an ambiguity error. Check for duplicates under
   `~/.hermes/skills/` when that happens.

## Verification

After changes, verify the prompt shrank:

```bash
bash /Users/bytedance/script/check_prompt_size.sh
```

Or start a new session and watch the startup banner for token stats.
