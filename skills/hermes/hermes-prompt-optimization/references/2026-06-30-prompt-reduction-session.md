# Prompt-Optimization Session Reference (2026-06-30)

## Starting State

Before any changes, the CLI system prompt was estimated at **~21,000+ chars**.
The skills index alone was ~17,000 chars with 160 skills listed.

## Changes Applied

| Change | Effect |
|--------|--------|
| `agent.tool_use_enforcement: false` | Removed ~800 char tool-use enforcement block (deepseek was matching the default model list) |
| `agent.environment_probe: false` | Removed ~200 char Python toolchain probe line |
| `memory.memory_char_limit: 500` (was 2200) | Capped memory snapshot growth |
| Disabled 13 additional skills on CLI platform | Removed ~2–3K chars from skills index |
| `agent.task_completion_guidance: false` | Already set; ~500 chars saved |
| `agent.parallel_tool_call_guidance: false` | Already set; ~400 chars saved |

## Final State

| Tier | Size | % of Total |
|------|------|-----------|
| Stable (identity + guidance + skills) | 8,540 chars | 99% |
| Context | 0 chars | 0% |
| Volatile (timestamp) | 88 chars | 1% |
| **Total** | **8,630 chars (~2,157 tokens)** | 100% |

Breakdown of stable tier:
- Identity + guidance blocks: 3,077 chars (36%)
- Mid-turn steer note: 679 chars (8%)
- Skills index: 4,776 chars (56%) — **16 skills** in index

## Remaining Skills on CLI (after disabling 145/160)

- aruba-ap-troubleshooting
- hermes-agent (core skill)
- troubleshooting-doc
- github
- huawei-switch-auth-troubleshooting
- netbox-device-query
- pcap-analysis
- obsidian
- macos-system-configuration
- research-notes
- huawei-mac-auth-debug
- query-wireless-terminal-state
- self-opt-daily-bugfix-v2
- vlan-and-terminal-inquiry
- write-troubleshooting-note-v2
- systematic-debugging

## Key Pitfall Discovered

When calling `build_skills_system_prompt()` programmatically (or via
`build_system_prompt_parts()`), the function resolves the platform from
`HERMES_PLATFORM` env var → session env → `""`. If the platform resolves to
empty string, `get_disabled_skill_names(None)` cannot find the
platform-specific disabled list in config.yaml, so **all 160 skills appear** in
the index.

**Fix:** Always `export HERMES_PLATFORM=cli` before running analysis scripts.

## Config File Verification Commands

```bash
# Check specific values
hermes config set agent.tool_use_enforcement false    # re-set to verify
hermes config set agent.environment_probe false
hermes config set memory.memory_char_limit 500

# Count disabled skills
python3 -c "
import yaml
with open('/Users/bytedance/.hermes/config.yaml') as f:
    c = yaml.safe_load(f)
d = c['skills']['platform_disabled']['cli']
print(f'Disabled in CLI: {len(d)}')
"

# Measure
bash ~/.hermes/skills/hermes/hermes-prompt-optimization/scripts/check_prompt_size.sh
```
