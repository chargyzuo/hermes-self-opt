---
name: Token Usage Optimizer
version: 1.0.0
description: Analyze session token usage and optimize skill index to reduce prompt inflation.
parameters:
  skill_list: list of installed skills
  active_skills: list of currently active skills (not disabled)
steps:
  - |
    Calculate total prompt characters and estimate token count (chars / 4).
    Break down composition: Skills index, Agent identity + instructions, Mid-turn steering.
  - |
    Examine skill list: identify disabled vs active, find stale entries (pointing to deleted/renamed skills).
    For each active skill, assess necessity for current session.
  - |
    Recommend actions:
    - Remove stale entries from disabled list
    - Add unnecessary active skills to disabled list
    - Report optimized active skill count
  - |
    Apply changes (update skill configuration) and summarize reductions.
---

## Token Usage Optimization Workflow

### 1. Analyze Prompt Composition
- Total prompt: {{total_chars}} chars (≈{{tokens_est}} tokens)
- Skills index: {{skills_chars}} chars ({{skills_percent}}%)
- Agent identity+guidance: {{identity_chars}} chars ({{identity_percent}}%)
- Mid-turn steering: {{steering_chars}} chars ({{steering_percent}}%)

### 2. Inspect Skills State
- Installed: {{installed_count}}
- CLI disabled: {{cli_disabled_count}}
- Actually matched disabled: {{matched_disabled_count}}
- Active: {{active_count}}
- Stale entries: list names that no longer exist

### 3. Optimization Decision
- Remove stale entries ({{stale_list}})
- Disable additional skills: {{disable_list}}
- New active count: {{new_active_count}}

### 4. Apply
- Execute `hermes skill disable {{skill_name}}` for each new disabling
- Update disabled list configuration accordingly
- Summarize net reduction