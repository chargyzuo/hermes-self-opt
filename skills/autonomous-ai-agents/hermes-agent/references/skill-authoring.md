# Authoring Hermes-Agent Skills

> This was formerly the standalone `hermes-agent-skill-authoring` skill, now consolidated as a reference under the `hermes-agent` umbrella.

## Two Skill Locations

1. **User-local:** `~/.hermes/skills/<maybe-category>/<name>/SKILL.md` — personal, created via `skill_manage(action='create')`
2. **In-repo:** `skills/<category>/<name>/SKILL.md` — committed, shipped with the package. Use `write_file` + `git add`.

## Required Frontmatter

Source of truth: `tools/skill_manager_tool.py::_validate_frontmatter`. Hard requirements:
- Starts with `---` as the first bytes
- Closes with `\n---\n` before the body
- Parses as a YAML mapping
- `name` field present, ≤64 chars, lowercase + hyphens
- `description` field present, ≤1024 chars
- Non-empty body after closing `---`

Peer-matched shape:
```yaml
---
name: my-skill-name
description: Use when <trigger>. <one-line behavior>.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [short, descriptive, tags]
    related_skills: [other-skill, another-skill]
---
```

## Size Limits
- Description: ≤1024 chars (enforced)
- Full SKILL.md: ≤100,000 chars (~36k tokens)
- Peer skills sit at 8-14k chars — aim for that range

## Peer-Matched Structure
```
# <Title>
## Overview
## When to Use
## <Topic sections>
## Common Pitfalls
## Verification Checklist
```

## Directory Placement
Categories currently: `autonomous-ai-agents`, `creative`, `data-science`, `devops`, `dogfood`, `email`, `github`, `media`, `mlops/*`, `note-taking`, `productivity`, `research`, `smart-home`, `social-media`, `software-development`, `web`.

## Workflow for In-Repo Skills
1. Survey peers in target category: `ls skills/<category>/`
2. Draft with `write_file` to `skills/<category>/<name>/SKILL.md`
3. Validate: check frontmatter, description length, total size
4. `git add` + `git commit`
5. **Note:** the current session's skill loader is cached — new skills only appear in fresh sessions

## Common Pitfalls
1. **Using `skill_manage(action='create')` for in-repo skills** — writes to `~/.hermes/skills/`, not the repo
2. **Leading whitespace before `---`** — validator checks `content.startswith("---")`
3. **Description too generic** — start with "Use when ..."
4. **Forgetting metadata block** — every peer has it
5. **Silently creating skills without user confirmation** — always `clarify()` first
6. **Expecting current session to see new skill** — loader is cached at session start
