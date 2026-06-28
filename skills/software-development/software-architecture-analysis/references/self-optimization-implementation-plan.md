# Agent Self-Optimization Implementation Plan

4-phase plan for building the framework on top of Hermes Agent.

## Phase 0 — Infrastructure Setup (1-2 days)

| Task | What | Output |
|------|------|--------|
| Session DB | Read `hermes_state.py`, confirm table structure and query | Can run `SELECT * FROM sessions LIMIT 5` |
| Knowledge dirs | Create `~/.hermes/knowledge/{core,normal,self-opt}/` | Three-layer directory structure |
| Benchmark v1 | Pick 10 troubleshooting questions, tag with "necessary steps + red-line list" | `benchmark.json` |
| Auxiliary LLM | Confirm `auxiliary` client is configured for LLM Judge + Deep Dream | `hermes config get auxiliary` returns a model |

## Phase 1 — Core Loop: Harvest → Mine → Gate-Lite (3-5 days)

Build the Memory + Skills auto-optimization pipeline (no user approval needed).

### Step 1.1 Harvest
- Cron: daily, read past 24h sessions from Session DB
- Manual: `hermes self-opt run`
- Output: list of raw session texts

### Step 1.2 Mine
One LLM call per session, extract 3 things:
```
Input: session text
LLM prompt: "Extract:
  1. Troubleshooting logic (symptom→steps→root→action)
  2. User preferences/habits (tone, common mistakes, favorite commands)
  3. Is there a reusable workflow?"
Output: JSON {knowledge_chunk, memory_chunk, skill_candidate}
```

### Step 1.3 Edit + Gate-Lite
- **Memory** → write directly to MEMORY.md, log
- **Skills** → LLM generates SKILL.md → LLM Judge on Benchmark (Gate-Lite) → pass→write, fail→reject, log either way

### Step 1.4 Log
- `~/.hermes/logs/self-opt/<date>.json`
- Fields: `{time, memory_changes, skill_changes, gate_results}`

**Done when**: `hermes self-opt run` produces log entries with Memory and Skills changes.

## Phase 2 — Knowledge Base Staging → Review → Commit (3-4 days)

### Step 2.1 Self-Opt Reference Write
- `knowledge_chunk` from Mine → `~/.hermes/knowledge/self-opt/pending/<id>.yaml`
- Each file has `status: pending` + source session + YAML body

### Step 2.2 Review Commands
- `hermes self-opt diff` — list pending changes
- `hermes self-opt approve <id>` — approve
- `hermes self-opt reject <id>` — reject (optional reason)
- `hermes self-opt edit <id>` — edit then approve

### Step 2.3 Gate-Full
- After approval: run Benchmark on the new knowledge
- "Does this knowledge, as skill context, cause the skill to hit any red lines?"
- Pass → move to `committed/`, update core knowledge index
- Fail → return to `pending/`

**Done when**: `hermes self-opt diff` shows pending items, approve commits them, agent uses them in diagnosis.

## Phase 3 — Deep Dream + Memory Three-Layer (2 days)

| Step | What |
|------|------|
| Context→Daily | Session end → write summary to `~/.hermes/memories/daily/<date>.md` |
| Daily→Core | Idle → LLM compresses daily into core memory entries |
| Core persistence | Write to `~/.hermes/memories/core.json`, agent loads at startup |

## Phase 4 — Polish (ongoing)

| Priority | Task | Notes |
|----------|------|-------|
| P1 | Expand Benchmark | Add new question per novel fault type |
| P2 | Auto-rollback | Deploy→detect regression→revert to previous |
| P2 | User feedback detection | Agent auto-detects dissatisfaction signals |
| P3 | Routing layer | Wait until 20-30 skills exist |
| P3 | Self-Opt Web UI | Simple dashboard for log + staging review |

## Skills → Knowledge → Memory Data Flow

```
Memory (auto, logged)
  ← Sessions via Deep Dream
  → User preferences, habits, env config
  → NO knowledge generation

Skills (auto, logged)
  ← Sessions via Mine (workflow extraction)
  → SKILL.md files (reusable procedures)
  → References core knowledge base for context

Knowledge (manual + staged)
  ← Troubleshooting docs (manual import → normal KB)
  ← Sessions via Mine (→ Staging → Review → Commit → Self-Opt Ref)
  → Core KB: YAML + JSON Schema (machine-first, refined logic)
  → Normal KB: Markdown (full reference materials)
  → Self-Opt Ref: Working area for optimization pipeline
```

## Reference Projects Mapping

| Project | Frame position | Mechanism borrowed |
|---------|---------------|-------------------|
| SkillOpt | Skills optimization | Training Loop + Gate + LR Scheduler |
| Hermes Self-Evolution | Skills (alternative) | GEPA genetic algorithm |
| GenericAgent | Skills generation | Crystallization from session patterns |
| CowAgent | Memory + holistic | Deep Dream + 3-layer memory |
| selftune | Routing + verification | Auto-rollback + trigger monitoring |
| Hermes Curator | Infrastructure | Session DB, usage stats, backup |
