---
date: 2026-06-30
source: agent/system_prompt.py::build_system_prompt_parts()
config: deepseek-v4-flash / deepseek / CLI platform
---

# Hermes System Prompt Composition — Detailed Breakdown

## Three-Tier Architecture

The system prompt is assembled by `build_system_prompt_parts()` in
`agent/system_prompt.py`. Three tiers are joined with `"\n\n"`:

```
stable + "\n\n" + context + "\n\n" + volatile
```

| Tier | Scope | Cache behavior |
|------|-------|----------------|
| **stable** | Session-lifetime invariant | Cached entire session — prefix-cache friendly |
| **context** | Per-project / per-cwd | Rebuilt on `/reset` |
| **volatile** | Per-session-start | Never cached, regenerated every session |

The combined string is cached on `agent._cached_system_prompt` for the
lifetime of the AIAgent instance. Only context compression triggers a rebuild.

## Stable Tier — Full Paragraph List

Ordered as constructed (not all paragraphs apply to every session):

| # | Paragraph | Condition | Config gate |
|---|-----------|-----------|-------------|
| 1 | **Agent Identity** — SOUL.md or `DEFAULT_AGENT_IDENTITY` ("You are Hermes Agent...") | SOUL.md preferred; fallback to constant | `load_soul_identity` |
| 2 | **Hermes Agent Help Guidance** — pointer to docs & skill | Always | Built-in |
| 3 | **Task Completion Guidance** — actually complete tasks, don't fabricate | When `_task_completion_guidance=True` AND tools loaded | `agent.task_completion_guidance` |
| 4 | **Parallel Tool Call Guidance** — batch independent calls into one turn | When `_parallel_tool_call_guidance=True` AND tools loaded | `agent.parallel_tool_call_guidance` |
| 5 | **Tool-specific Guidance** — memory / session_search / skill_manage usage | Per-tool, only when the tool is loaded | Tool availability |
| 6 | **Kanban Worker Guidance** — lifecycle instructions for dispatched workers | Only when dispatched by kanban dispatcher | `_kanban_worker_guidance` |
| 7 | **Steer Channel Note** — out-of-band user message handling | When tools are loaded | Built-in |
| 8 | **Nous Subscription Prompt** | Only on Nous Portal | Subscription status |
| 9 | **Tool Use Enforcement** — force tool calling; model-family-specific guidance | Auto-matched to model name or configured list | `agent.tool_use_enforcement` |
| 10 | **Skills List** — `available_skills>` block | When skills_list/skill_view/skill_manage tools are loaded | Platform skill disabling |
| 11 | **Alibaba Model Name Fix** — explicit model identity | Only when `provider == "alibaba"` | Provider match |
| 12 | **Environment Hints** — OS, home, cwd, terminal backend | Always when local; suppressed on remote backends | `build_environment_hints()` |
| 13 | **Coding Posture** — workspace snapshot + git state | Only in coding workspace | `coding_context.py` |
| 14 | **Python Toolchain Probe** — pip/uv/PEP-668 state | When non-default; emits ONE line or nothing | `agent.environment_probe` |
| 15 | **Active Profile Hint** — profile name + cross-profile guard | Always | Runtime detection |
| 16 | **Platform Hints** — platform-specific operating guidance (`You are running in the Hermes terminal UI (TUI)...` etc.) | Per platform key match | `PLATFORM_HINTS` dict + `platform_hints` config override |

## Context Tier

| Part | Source | Condition |
|------|--------|-----------|
| `system_message` | Caller-supplied parameter | When non-None |
| Context files | `AGENTS.md` / `.cursorrules` / `CLAUDE.md` / `.hermes.md` | When discovered under TERMINAL_CWD and `skip_context_files=False` |

## Volatile Tier

| Part | Source | Config gate |
|------|--------|-------------|
| Memory snapshot | `~/.hermes/memories/memory/` (built-in) | `memory.memory_enabled` |
| User profile | `~/.hermes/memories/user/` (USER.md) | `memory.user_profile_enabled` |
| External memory provider block | Honcho / Mem0 etc. | `_memory_manager` presence |
| Timestamp line | `Conversation started: Tuesday, June 30, 2026` + Model + Provider | Built-in (always) |

The timestamp uses **date-only** precision (no minutes) to keep the prompt
byte-stable for the full day and preserve prefix cache.

## Real-World Size (Current Config)

```
Platform: cli
Model:    deepseek-v4-flash
Provider: deepseek

stable:    8,677 chars  (~2,169 tokens)
context:         0 chars  (skip_context_files=True, no system_message)
volatile:     360 chars  (~90 tokens, memory + timestamp)
───────────────────────────────────────
TOTAL:      9,037 chars  (~2,259 tokens)
```

Breakdown of the stable tier:

```
段                                          字符数     占比
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are Hermes Agent... (identity)          3,077     35.5%
Skills (mandatory) — available_skills>      4,103     47.3%
Hermes Agent help guidance                    687      7.9%
Environment hints (Host, Home, CWD)           430      5.0%
Active Profile hint                           380      4.4%
Skills guidance                                281      3.2%
Platform hints (TUI)                           387      4.5%
Steer channel note                             175      2.0%
Memory guidance                                159      1.8%
Session search guidance                        134      1.5%
Timestamp line                                 131      1.5%
Other (probe, coding, etc.)                    335      3.9%
```

The **Skills list** dominates at ~47% of the stable tier even after
disabling most skills (14 kept out of 161 total).

## Key Design Principles

1. **Prefix cache friendly** — Stable tier byte-identical for session lifetime
2. **Byte-stable** — Timestamp uses date-only to avoid cache invalidation
3. **Dynamic dependency** — Only inject paragraphs relevant to current model/platform/tools
4. **Configurable** — Most paragraphs have independent config.yaml gates
5. **Exception-safe** — All external calls wrapped in try/except (coding context, env probe, memory)
