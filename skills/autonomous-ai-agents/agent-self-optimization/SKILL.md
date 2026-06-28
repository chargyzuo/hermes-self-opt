---
name: agent-self-optimization
description: "Harvest sessions, mine for patterns, distill memory, and route skills — the complete Agent Self-Optimization pipeline for Hermes."
version: 1.9.0
tags: [self-opt, harvest, mine, gate, memory, distillation, router, knowledge, phase2, phase3, phase4, skillopt, crystallize, feedback]
---

# Agent Self-Optimization

Four-phase pipeline that runs nightly via cron to keep your agent learning from every session.

> ⚠️ **语言要求**: 用户用中文，看不懂全英文。所有回复必须用中文（专业术语保留英文，如 YAML、commit、review）。

> ⚠️ **Git 纪律**: 每次修改 `~/script/hermes-self-opt/` 下的代码后必须 `git commit`。项目在 `main` 分支。

## Commands

```bash
# Phase 1: Core Pipeline
hermes self-opt process --days 1          # Full pipeline (Harvest → Mine → Gate → Write)
hermes self-opt process --session-id <id> # Single session

# Phase 2: Knowledge Pipeline
hermes self-opt extract              # Parse normal/ MD → structured
hermes self-opt distill-knowledge    # Dedup + generate YAML → staging/
hermes self-opt review [-y]          # Review staging changes (y/n confirm)
hermes self-opt gate-full [--verbose] [--judge]  # 4 checks + optional LLM Judge
hermes self-opt commit [--dry-run|--skip-gate|--skip-review]  # staging → core
hermes self-opt knowledge-build [-y] [--dry-run] [--skip-gate] [--judge]  # One-click all 5 stages + optional LLM Judge
hermes self-opt knowledge            # KB statistics
hermes self-opt export-schema [--dry-run]  # Export _schema.yaml
hermes self-opt judge [-v]           # LLM score full docs

# Phase 3: Skill Optimization (Rollout → Reflect → Edit → Gate-Lite)
hermes self-opt optimize                        # Optimize ALL skills with benchmark entries
hermes self-opt optimize --skill-name <name>    # Optimize a single skill
hermes self-opt optimize --dry-run              # Simulate only, don't write skills
hermes self-opt optimize --max-iters 5          # Max 5 iterations per skill (default: 3)
hermes self-opt optimize --json                 # JSON output

# Phase 3: Crystallization (New Skill Generation) ✅ IMPLEMENTED (2026-06-28)
hermes self-opt crystallize                       # Detect recurring patterns → generate new skills
hermes self-opt crystallize --detect-only         # Only detect patterns, don't generate
hermes self-opt crystallize --days 14             # Analyze 14 days of sessions
hermes self-opt crystallize --dry-run             # Simulate only, don't write skills
hermes self-opt crystallize --json                # JSON output

# Phase 3: Memory
hermes self-opt distill               # Deep Dream Daily → Core Memory
hermes self-opt memory                # Core Memory stats
hermes self-opt memory --show         # Full Core Memory content

# Phase 4: Router
hermes self-opt router build          # Rebuild skill index
hermes self-opt router query "<text>" # Search skills locally
hermes self-opt router gap <name>     # Find description gaps
hermes self-opt router rewrite <name> # LLM rewrite description
hermes self-opt router rollback <name># Rollback to last backup
hermes self-opt router monitor               # Trigger rate monitoring
hermes self-opt router monitor --skill <name> # Per-skill detail
hermes self-opt router monitor --days 30 --json

# Phase 4: Feedback
hermes self-opt feedback capture --target <name> --correction "<text>" [--type skill|knowledge]
hermes self-opt feedback list [--status pending|processed|rejected|all] [--json]
hermes self-opt feedback process [--id <id>|--all] [--dry-run]
hermes self-opt feedback reject --id <id> [--reason]
hermes self-opt router monitor               # Trigger rate monitoring (last 7 days)
hermes self-opt router monitor --skill <name> # Per-skill detail
hermes self-opt router monitor --days 30 --json # Extended window + JSON output

# Phase 4: Event Log ✅ IMPLEMENTED (2026-06-28)
hermes self-opt eventlog                          # View all self-opt events (skills/knowledge/cron runs)
hermes self-opt eventlog --type skill             # Only skill changes
hermes self-opt eventlog --type knowledge         # Only knowledge commits
hermes self-opt eventlog --type cron              # Only cron runs
hermes self-opt eventlog --days 30                # Extended window (default: 7)
hermes self-opt eventlog --limit 50               # Max events (default: 50)
hermes self-opt eventlog --json                   # JSON output
```

## Architecture

### Phase 1: Core Loop (Harvest → Mine → Gate-Lite → Write)

```
Session DB → Harvest (filter tool output, keep user+assistant)
  → Filter (pure forward keyword matching, ≥3 hits)
    → Mine (auxiliary LLM extracts: knowledge_chunk, memory_chunk, skill_candidate)
      → Gate-Lite (basic checks + Skill Execution Benchmark scoring)
        → Write (Daily Memory + Skill)
```

### Gate-Lite Skill Benchmark Integration ✅ IMPLEMENTED (2026-06-27)

Gate-Lite 现在使用 **Skill Execution Benchmark** 对自动生成的 skill 做精准评分，不再用知识库 benchmark（5 条散弹式考题）：

```
gate_skill(skill_content, skill_name="huawei-mac-auth-debug")
  → _load_skill_execution_benchmark(skill_name)  # 精准匹配
    → skill_execution_benchmark.json (8 skills, 56 steps + 30 redlines)
      → filter: skill == "huawei-mac-auth-debug"
        → 只返回 sb-001（MAC 认证场景）
  → 未匹配 → 降级到知识库 benchmark → 再未匹配 → 降级通过
```

**Benchmark 文件**:
- `~/.hermes/knowledge/self-opt/skill_router_benchmark.json` — 10 skills × 49 条路由查询
- `~/.hermes/knowledge/self-opt/skill_execution_benchmark.json` — 8 skills × required_steps + redlines
- `~/.hermes/knowledge/self-opt/benchmark.json` — 保留，知识库用（Gate-Full LLM Judge）

**CLI**:
```bash
hermes self-opt gate --skill-file <path> --skill-name <name>  # 精准匹配
hermes self-opt gate --skill-file <path>                      # 降级到知识库 benchmark
```

**代码改动** (commit `063ee10`):
- `gate.py`: `_load_skill_execution_benchmark()`, `_format_benchmark_entries()`, `gate_skill()` 新 `skill_name` 参数
- `pipeline.py`: `run_session()` 自动传 `skill_name`
- `cli.py`: `gate` 子命令新增 `--skill-name`

**Pitfalls**:
- Never use negative keyword filtering (e.g., skip if "笔记" found). A troubleshooting session may mention "笔记" while the user asks to write a note about their findings. Pure forward matching (≥3 troubleshooting keywords) avoids false kills.
- `hermes_state` API: `SessionDB` class with `list_sessions_rich()` and `get_messages()`, NOT `get_session_db()` or `get_recent_sessions()`.
- Auxiliary client: `agent.auxiliary_client.call_llm()`, NOT `get_auxiliary_client()`.

### Phase 3: Skill Optimization Loop (Rollout → Reflect → Edit → Gate-Lite) ✅ IMPLEMENTED (2026-06-28)

借鉴 SkillOpt Training Loop，对已有 skill 做迭代优化（commit `8bf160d`）：

```python
# skillopt.py — 核心循环
optimize_skill(skill_name, max_iterations=3)
  ├── run_rollout()    # LLM 模拟 skill 在 benchmark 场景下执行，产出 trace
  ├── run_reflect()     # 对比 trace vs benchmark（required_steps + redlines）
  ├── run_edit()        # 根据差距分析生成 skill 修改补丁
  └── gate_skill()      # Gate-Lite 终验（复用 gate.py Skill Execution Benchmark）

optimize_all()           # 批量优化所有在 skill_execution_benchmark.json 中有条目的 skill
```

**架构**:
- `skillopt.py` (578 行) — Rollout/Reflect/Edit 三个核心函数 + 驱动循环
- `cli.py` — `optimize` 子命令（--skill-name, --dry-run, --max-iters, --json）
- 自动备份：`_write_skill()` 写入前自动创建 `.bak` 备份
- 非 LLM 路径可独立测试（31 项 ad-hoc 验证通过）

**CLI**:
```bash
hermes self-opt optimize                          # 全部 8 个有 benchmark 的 skill
hermes self-opt optimize --skill-name huawei-mac-auth-debug  # 单个
hermes self-opt optimize --dry-run --max-iters 5  # 预览 + 最多 5 轮
```

### Phase 3: Crystallization (Auto Skill Generation) ✅ IMPLEMENTED (2026-06-28)

借鉴 GenericAgent Crystallization，从多个 session 中发现重复排障模式，自动生成新 skill（commit `3d547ab`）：

```python
# crystallize.py — 核心流程
crystallize(days=7) → 跨 session 模式检测 + 自动生成
  ├── _collect_recent_sessions()   # 收集近期排障 session（via harvest.py）
  ├── _format_session_summaries()  # 格式化 + 自动截断（MAX_TOTAL_DIALOG_CHARS=12000）
  ├── 单次 LLM 调用                 # 跨 session 检测重复模式 → 生成 SKILL.md
  ├── _is_duplicate_skill()        # Router 语义去重（threshold=0.6）
  ├── _skill_name_exists()         # 文件名去重
  └── gate_skill() → write_skill() # Gate-Lite 验证 → 写入 self-opt/skills/self-opt/
```

**架构**:
- `crystallize.py` (388 行) — 收集/格式化/LLM调用/去重/Gate-Lite 全流程
- `cli.py` — `crystallize` 子命令（--days, --dry-run, --detect-only, --json）
- 最少 3 个排障 session 才触发（`MIN_SESSIONS_FOR_PATTERN=3`）
- 单次 LLM 调用处理所有 session（符合「process larger chunks」偏好）
- 两重去重：文件名存在检查 + Router 语义重叠检查

**CLI**:
```bash
hermes self-opt crystallize              # 全流程：检测 → 去重 → Gate → 写入
hermes self-opt crystallize --detect-only # 仅检测（返回 session 数量 + 是否满足门槛）
hermes self-opt crystallize --days 14     # 扩展回溯窗口
hermes self-opt crystallize --dry-run     # 模拟，不写入
```

### Phase 3: Memory Architecture (Daily → Core → Distill + Auto-Optimization) ✅ v2.0 (2026-06-28)

```
write_daily(daily/<date>.md) → accumulate per-session memory fragments
  → distill_daily() → auxiliary LLM compresses → Core Memory (YAML per category)
    → core_memory.py: facts.yaml, preferences.yaml, patterns.yaml, environment.yaml
      → upsert_entry() — 4-tier dedup before save:
         1. exact match → skip, increment duplicate_count
         2. high similarity (>=0.70) → merge, increment duplicate_count
         3. same topic (>=0.35) + contradiction → resolve, keep one
         4. new content → append
      → cleanup_core_memory() — post-distill global dedup + conflict resolution
      → duplicate_count — tracks how many times each entry was seen (weight)
      → added/updated — tracks first-write and last-update dates per entry
      → MEMORY.md and USER.md deprecated (historical reference only)
```

**Key decision**: MEMORY.md is NOT the primary store anymore. New memory goes to `daily/<date>.md`, distilled to `core/*.yaml`. Old files preserved as reference.

**PITFALL — core YAML does NOT auto-inject into sessions**: Hermes reads `~/.hermes/memories/MEMORY.md` and `USER.md` into every session's system prompt. The `core/*.yaml` files (facts/preferences/environment/patterns) are the self-opt structured store and are NOT auto-injected — they only serve the `hermes self-opt distill` pipeline and `hermes self-opt memory --show` CLI. If you replace MEMORY.md content with a deprecation notice, the agent in the NEXT session will have ZERO memory context. 

**Mitigation options**:
- Keep a compiled summary in MEMORY.md (auto-generated from core YAML by cron before each session)
- Load core YAML explicitly at session start via a startup hook
- Wait for self-opt to implement auto-injection (not yet implemented)

**Legacy migration**: For one-time migration of traditional MEMORY.md → core YAML, see `references/legacy-memory-migration.md`.

### Phase 4: User Feedback Loop (Capture → Queue → Process) ✅ IMPLEMENTED (2026-06-28)

```python
# feedback.py (435行) — 框架底部反馈层
capture_feedback(target, correction, target_type="skill")
  → pending/ JSON → 不阻塞当前 session
  → 空闲时 cron 自动消化（skill）或生成报告（knowledge）

process_feedback(correction_id)
  ├── _find_skill_file() / _find_knowledge_file()  # 双匹配
  ├── LLM 修正（FEEDBACK_APPLY_PROMPT）
  ├── gate_skill()  # Gate-Lite 终验（仅 skill）
  └── 写回 .bak → processed/
```

**存储**: `~/.hermes/knowledge/self-opt/corrections/{pending,processed,rejected}/`

**CLI**:
```bash
hermes self-opt feedback capture --target <name> --correction "<text>" [--type skill|knowledge]
hermes self-opt feedback list [--status pending|processed|rejected|all] [--json]
hermes self-opt feedback process [--id <id>|--all] [--dry-run]
hermes self-opt feedback reject --id <id> [--reason]
```

> ⚠️ **CORE KNOWLEDGE CONSTRAINT**: core Knowledge 是所有知识资产的核心，**任何变更必须经用户同意**（Staging→Gate-Full→Review→Commit）。Cron 自动消化仅限 skill correction（Gate-Lite 自动挡），knowledge correction 只生成报告不自动写入（commit `1af51cf`）。

### Phase 4: Skill Router (Observe → Detect → Evolve → Watch) ✅ MONITORING IMPLEMENTED (2026-06-28)

> ⚠️ **路由自动回滚**: 2026-06-28 确认不做。只保留收集+监控。

> ⚠️ **Benchmark 区分**: 现有 `benchmark.json` 是知识库评测（5条排障考题，用于 Gate-Lite/Gate-Full 评分）。Skill Benchmark 是另一层——测试路由准确性和技能执行质量，已建两个文件：
> - `~/.hermes/knowledge/self-opt/skill_router_benchmark.json` (10 skills, 49 queries)
> - `~/.hermes/knowledge/self-opt/skill_execution_benchmark.json` (8 skills, 56 steps + 30 redlines)
> 详见 `references/skill-benchmark-design.md`。

> ⚠️ **Router 中文分词 PITFALL** (2026-06-27 修复, 2026-06-28 提升): 原 `query()` 用 `lower.split()` 分词对中文完全无效，准确率仅 2% (1/49)。两步修复：
> 1. CJK 字符级重叠匹配（权重 0.5）+ 反向匹配 → 40.8% top-1 / 46.9% top-3 (commit `bd8ca71`)
> 2. jieba 分词多字词加分 0.15 + MIN_SCORE 0.3→0.2 → **53.1% top-1 / 61.2% top-3** (commit `79267e1`)
>
> jieba 不可用时自动降级（ImportError catch），字符级重叠做主力。no_results 从 17/49 降到 4/49。

```
record_match() → record what user said + which skill matched
  → find_description_gap() → detect phrases NOT in skill description
    → rewrite_description() → LLM fills in missing keywords
      → _backup_skill() → auto-backup before every rewrite
        → rollback_skill() → manual rollback to last backup
```

## Cron Schedule

```bash
03:00 → self-opt-nightly           (Phase 1: Harvest → Mine → Gate → Daily Memory)
04:00 → self-opt-distill           (Phase 3: Daily → Core Memory 蒸馏 + cleanup_core_memory 去重冲突解决)
05:00 → self-opt-router            (Phase 4: Rebuild index + gap scan)
06:00 → self-opt-daily-bugfix      🆕 每日 Bug 修复: 读日志 → 找 bug → 修 → 记录 Obsidian → git commit
*/30  → knowledge-pipeline-watchdog (Phase 2: normal/ 变化检测 → 增量 extract→distill→gate→commit)
        └─ 脚本: ~/.hermes/scripts/knowledge-pipeline-watchdog.py
        └─ 状态: ~/.hermes/knowledge/self-opt/.normal_hashes.json
        └─ 日志: ~/.hermes/knowledge/self-opt/pipeline_watchdog.log
```

## Logging (ALL cron events + skill/knowledge changes) ✅ IMPLEMENTED (2026-06-28)

Every self-opt cron event and every skill/knowledge change MUST produce a log entry. Logging
is not optional — if it ran, it must be traceable.

### Log locations

```
~/.hermes/self-opt/
├── change.log                          ← 统一变动日志: skill/knowledge changes
├── logs/<YYYYMMDD_HHMMSS>.json         ← per-run structured JSON logs
└── pipeline_watchdog.log               ← Phase 2 watchdog text log (已有)
```

### change.log format

Per-line format: `UTC_timestamp | target | action | name | source=... | path=... | detail=...`

- **target**: `skill` or `knowledge`
- **action**: `created`, `updated`, `committed`, `skipped`
- **source**: session_id or `pipeline` or `cron`

Writers: `writer.py::write_change_log()` (skill changes via `write_skill()`),
`committer.py::commit_to_core()` (knowledge commits).

### Per-phase JSON logs

Each phase writes a structured JSON log to `logs/<timestamp>.json` via `writer.py::write_log()`:

| Phase | log key | writer | when |
|-------|---------|--------|------|
| Phase 1 | `session_id` + `steps` | `pipeline.py` → `write_log()` | every `hermes self-opt process` |
| Phase 3 distill | `phase: "distill"` | `distill.py::distill_daily()` | cron or manual distill |
| Phase 4 router | `phase: "router-build"` | `router.py::build_index()` | cron or manual rebuild |

### Verification

Run `ls -lt ~/.hermes/self-opt/logs/` and `cat ~/.hermes/self-opt/change.log`.
Every cron job listed above must produce visible log output within 1 minute of its schedule.

The knowledge-pipeline watchdog is a `no_agent=True` cron job — a Python script with NO LLM overhead. It computes per-file SHA256 hashes of all `normal/*.md` files, compares with the last run, and only triggers `hermes self-opt knowledge-build -y` when files are new or changed. Deleted files are auto-removed from the hash registry. Unchanged runs are fully silent (empty stdout → no delivery). Pattern: `incremental change detection → conditional pipeline execution`.

**PITFALL — don't run full pipeline on every tick**: The initial implementation naively called the full pipeline (80 files, 2+ minutes). Fixed by per-file hash comparison and incremental extraction. Only the changed files pass through extract → distill → gate → commit. The first run after a new normal/ doc is added processes only that 1 file (a few seconds).

## Knowledge Base Architecture (v4 — Three-Type Atomic) ✅ IMPLEMENTED

Three layers at `~/.hermes/knowledge/`:
```
normal/     # Markdown — human + LLM readable, distilled from Feishu docs (80 MD files)
core/       # YAML — agent-facing, three atomic types:
  _index.yaml       # Inverted index (tags → ids, triggers → full_id)
  check-source/     # 294 reusable check atoms (command, device_type)
  decision-source/  # 46 reusable conclusion atoms (action, confidence)
  full-*.yaml       # 47 routing graphs (links check_source → decision_source via True/False branches)
self-opt/   # Working area — staging/, committed/ (387 archives), benchmark.json
```

**Three document types**:
- `check_source` — atomic check step (id, description, command, device_type). Reused across multiple full docs. ID format: `check-<docid>-step<N>`.
- `decision_source` — terminal conclusion (id, description, action, confidence=high|medium|low). ID format: `decision-decision-<docid>`.
- `full` — routing graph (id, triggers, flow). Each flow step has `check` (link to check_source id), `on_true` (next_check|decision|redirect), `on_false` (same). Empty `{}` branch = terminal stop.

### Phase 2 Implementation (COMPLETED 2026-06-27)

Code lives at `/Users/bytedance/script/hermes-self-opt/hermes_self_opt/`. All five modules implemented and tested E2E (80 normal/ MD → 387 core/ YAML, Gate 100% pass):

| Module | Function |
|--------|----------|
| `extractor.py` | Walk normal/*.md, parse YAML frontmatter, extract 6 named sections (症状/排查/根因/方案/操作/备注), infer device_type, extract commands |
| `eventlog.py` | Unified event log viewer — aggregates change.log + logs/*.json + pipeline_watchdog.log |
| `distill_knowledge.py` | Three-layer dedup → generate check_source/decision_source/full YAML → write staging/ |
| `gate_full.py` | Schema (manual + jsonschema fallback), reference integrity, branch completeness, DFS cycle detection, **P1: export_schema(), LLM Judge** |
| `committer.py` | Atomic staging→core move with archive, _index.yaml update, rollback, **P1: auto-export schema after commit** |
| `reviewer.py` (P0) | scan_staging, review_staging, save/load_review_state, staging_changed_since_review |
| `cli.py` (extended) | `hermes self-opt extract|distill-knowledge|gate-full|review|commit|knowledge|export-schema|judge|eventlog` |

### Deduplication (Three-Layer)

When distilling, check_source and decision_source are deduped against existing entries:
1. Exact match on `id`
2. Exact match on `command + device_type` (for check_source) or `action` (for decision_source)
3. Semantic similarity > 0.92 + tags intersection ≥ 2 → flagged as `candidate_duplicate`

Full documents are always generated fresh.

**CRITICAL PITFALL**: When layer 2 dedup fires ("exact"), do NOT add the deduped ID to `check_ids` for the full doc flow — the check won't be written to staging (it already exists in core), creating a dangling reference. Just skip it entirely. Two genuinely different troubleshooting steps may share the same command (e.g., `python3 -m http.server 5000` run on different machines); if they dedup as "exact", the second step is dropped from the flow and the full doc routes through fewer steps — this is correct behavior.

### Gate-Full Validation

Before committing to core/, every YAML passes four checks:
1. **JSON Schema validation** — per-type required fields exist with correct types (manual implementation, jsonschema optional)
2. **Reference integrity** — every `check`/`next_check`/`decision`/`redirect` link resolves in staging ∪ core
3. **Branch completeness** — every step has `on_true` and `on_false` keys present (may be empty `{}` = terminal, but must NOT be `None`/missing). Empty dict means "stop here, no further path."
4. **Cycle detection** — DFS three-color marking over `redirect` edges between full documents

**PITFALL**: Never generate fake redirect targets like `fallback-troubleshoot`. If no real fallback full doc exists, use empty `{}` for the branch (terminal). Gate will reject any non-resolving reference.

### CLI Commands (Phase 2 — Final)

```bash
hermes self-opt extract              # Parse normal/ → stdout (or --json)
hermes self-opt extract --file <md>  # Extract single MD
hermes self-opt distill-knowledge    # Extract + dedup + generate → staging/
hermes self-opt distill-knowledge --dry-run  # Simulate only
hermes self-opt review               # 展示 staging/ 变更摘要，y/n 确认
hermes self-opt review -y            # 自动批准
hermes self-opt gate-full            # Run four checks on staging/
hermes self-opt gate-full --verbose  # Per-file pass/fail
hermes self-opt gate-full --judge    # 4 项刚性检查 + LLM 评分
hermes self-opt commit               # Review gate + Gate + move staging → core
hermes self-opt commit --skip-gate   # Skip Gate, commit directly
hermes self-opt commit --skip-review # Skip review gate (cron/自动化)
hermes self-opt commit --dry-run     # Simulate only
hermes self-opt knowledge            # KB statistics (core counts, index stats)
hermes self-opt export-schema        # 导出 JSON Schema → core/_schema.yaml
hermes self-opt export-schema --dry-run  # Preview
hermes self-opt judge                # LLM Judge: 对所有 staging/ full 文档评分
hermes self-opt judge --verbose      # Per-file 详细结果
hermes self-opt judge --benchmark <path>  # 指定 benchmark 路径
hermes self-opt knowledge-build [-y] [--dry-run] [--skip-gate] [--judge]  # 🆕 P2: 一键 extract→distill→review→gate→commit
hermes self-opt knowledge-build -y      # 自动批准 review
hermes self-opt knowledge-build --dry-run  # 模拟运行，停在 review
hermes self-opt knowledge-build --skip-gate  # 跳过 Gate-Full
hermes self-opt knowledge-build --judge     # 🆕 Gate-Full 后跑 LLM Judge
```

### ✅ Review Gate (P0 — Implemented 2026-06-27)

The framework's hard rule **"knowledge base writes must go through user approval"** is now enforced:

1. **`hermes self-opt review`** — scans staging/, shows change summary (new/existing breakdown by type, file list), asks y/n confirmation. Use `--yes`/`-y` for auto-approval.
2. **Commit intercept** — `hermes self-opt commit` checks `.review_state.json` before proceeding:
   - No review state → rejected ("Run 'hermes self-opt review' first")
   - Review rejected → rejected
   - Staging changed since review → rejected (hash-based change detection)
   - `--skip-review` bypasses the gate (for cron/automation)
3. **Gate order**: review → gate-full → commit (both gates must pass, each has its own --skip flag)

Implementation: `reviewer.py` (scan_staging, save/load_review_state, staging_changed_since_review, review_staging).

### ✅ P1 Completion (Implemented 2026-06-27)

**P1-3: Schema export** — `gate_full.py::export_schema()`:
- Exports the three-type JSON Schema to `core/_schema.yaml` (144 lines)
- Triggered manually via `hermes self-opt export-schema [--dry-run]`
- Auto-sync after every successful commit (committer.py)

**P1-4: LLM Judge** — `gate_full.py::run_llm_judge()`:
- Reuses `benchmark.json` (5 network troubleshooting scenarios) for quality scoring
- Evaluates full docs: matches to benchmark, scores coverage (0-5), checks redlines
- Advisory only — does NOT block commit
- Triggered via `hermes self-opt judge [--benchmark] [--verbose]` or `gate-full --judge`
- Works with Hermes `agent.auxiliary_client.call_llm()`, gracefully falls back without it

### ✅ P2 Completion (Implemented 2026-06-27)

**P2-5: run-pipeline** — One-click pipeline (`cli.py::_handle_run_pipeline`, +107 lines):
- Chains all 5 stages: extract → distill → review → gate → commit
- Prints per-stage progress with ✅/❌ status
- Fails fast: if any stage fails, pipeline stops immediately
- Flags: `--yes`/`-y` (auto-approve review), `--dry-run` (stop after review), `--skip-gate`, `--verbose`
- Dry-run shows full pipeline up to review, then exits without writing core/

**P2-6: LLM Confidence Evaluation** — `distill_knowledge.py::_evaluate_confidence_llm()` (+109 lines):
- Replaces heuristic confidence (count sections) with LLM evaluation
- Prompt (`CONFIDENCE_EVAL_PROMPT`): evaluates root cause clarity, verification steps, reproducibility
- Returns `{confidence: "high|medium|low", reason: "..."}` — matches the v4 enum spec
- Graceful degradation: LLM unavailable → heuristic fallback (3 sections=high, 2=medium, 1=low)
- Auto-loads `agent.auxiliary_client.call_llm()` at runtime; no config needed

**PITFALL — Python `.format()` brace escaping**: LLM prompts that contain JSON examples (e.g., `{"confidence": "high"}`) will collide with `str.format()` placeholders. The `{` and `}` in JSON must be doubled: `{{"confidence": "high"}}`. This bit `CONFIDENCE_EVAL_PROMPT` — the JSON example was interpreted as a format key, causing runtime failure. Fixed with `{{confidence}}`.

**PITFALL — Cron prompt chained commands cause timeout**: The `self-opt-router` cron prompt originally chained 5 commands with `&&` in a single `terminal()` call (`cd && source venv && hermes build && echo ... && gap && stats`). This caused a 977s TimeoutError because the shell waited on the venv activation or `hermes` stdin. **Fix (2026-06-28)**: split into 5 separate `terminal()` calls, each with its own timeout. When writing cron prompts, always keep commands short and separate — never chain with `&&` in a single `terminal()`. Verified: `cd /Users/bytedance/.hermes/hermes-agent && source venv/bin/activate && hermes self-opt router build` runs in 240.9ms when called alone.

**PITFALL — Verification after code changes**: When editing code without a canonical test suite, create a focused ad-hoc verification script under the OS temp directory with a `hermes-verify-` prefix, run it, clean it up, and report results explicitly as ad-hoc verification. **CRITICAL**: import and exercise the REAL module, not a standalone copy of the logic. The system will reject standalone reimplementations as unverified — only exercising the actual changed `gate_skill()`, `_extract_json()`, etc. counts as proof. Use `sys.path.insert(0, PROJECT)` + mock external dependencies (e.g. `agent.auxiliary_client`) to make imports work. The script should test each changed function's happy path and edge cases.

**PITFALL — Testing Phase 1 pipeline (not just cron status)**: When testing the self-opt pipeline, do NOT just check whether cron jobs ran. Run `hermes self-opt process --session-id <id>` on a real troubleshooting session, inspect the actual output files (daily memory, SKILL.md, knowledge chunk), verify against benchmark with `hermes self-opt gate --skill-file <path> --skill-name <name>`, and write a test record document to `Agent学习/Agent self-optimization Frame/测试记录/`. The session should be a real troubleshooting session (not a config session), found via `session_search` with queries like `dis aaa online-fail-record` or `switch_execute`.

**PITFALL — Gate-Lite LLM Judge returns empty JSON**: The LLM Judge in `gate.py::_run_judge()` may return JSON wrapped in markdown code blocks (```json ... ```), causing `json.loads()` to fail with `"评分解析失败，默认通过"`, defaulting all skills to `coverage_score=3`. **Fix (commit `f11a687`)**: replaced single `try/except json.loads()` with 4-strategy `_extract_json()`: (1) direct parse, (2) markdown code block extraction, (3) inline/braces extraction, (4) escape repair. To diagnose: run `hermes self-opt gate --skill-file <path> --skill-name <name>` and check if `coverage_score` is 3 with a parse failure reason.

**PITFALL — Extractor heading format (no numbered prefixes)**: The extractor uses `_identify_section()` which matches section headings via `startswith(alias)`. Numbered headings like `## 1. 问题描述` strip to `1. 问题描述` which does NOT start with `问题描述` — sections will be silently skipped. Always use bare headings: `## 问题描述`, `## 排查过程`, `## 原因分析`, `## 解决方案`. The SECTION_ALIASES map was updated (2026-06-28) to include `原因分析` (root_cause) and `解决方案` (solution), but `## 1. xxx` format still fails.

**PITFALL — Gate-Full tags minItems**: CHECK_SOURCE_SCHEMA and DECISION_SOURCE_SCHEMA originally required `tags.minItems: 1`, but the distill module does not yet auto-generate tags. Empty `tags: []` would fail all four jsonschema oneOf branches. Fixed (2026-06-28) by removing minItems from tags in all three schemas. If tags generation is added later, consider re-enabling minItems.

**PITFALL — Phase 2 testing with Feishu docs**: When testing Phase 2 with a real Feishu troubleshooting doc, the workflow is: (1) fetch with `lark-cli docs +fetch --api-version v2 --doc-format markdown`, (2) strip `<img>` noise and fix headings to bare format, (3) save to `~/.hermes/knowledge/normal/<id>.md`, (4) run `hermes self-opt knowledge-build -y`. Verify output with `hermes self-opt knowledge` (counts) and `hermes self-opt eventlog --type knowledge` (commit log). If check_sources > 6, the normal/ Markdown was too verbose — re-distill with fewer steps.

**PITFALL — rollback_last_commit() is destructive**: `committer.py::rollback_last_commit()` reads from `committed/` (ALL previously committed files) and moves them ALL back to staging/. This flushes the ENTIRE knowledge base. Do NOT use for incremental undo. Recovery: `hermes self-opt review -y && hermes self-opt commit --skip-gate`.

**PITFALL — cleanup_core_memory skips solo entries**: Original `cleanup_core_memory()` used `if len(entries) < 2: continue`, which skipped backfill of `duplicate_count` on categories with only 1 entry. This caused old entries to never get the `duplicate_count` field. **Fix (commit `eb378eb`)**: add a `setdefault("duplicate_count", 1)` branch for `len(entries) == 1` before the `continue`. Always verify backfill works on solo- and multi-entry categories with a temp-directory test (`/tmp/hermes-verify-*.py` using `core_memory.CORE_DIR` monkey-patch).

**PITFALL — core_memory.py was append-only (no update/change mechanism)**: The original `save_entry()` only appended — no dedup, no update, no merge. This caused the same preference ("Core Knowledge 必须经用户同意") to be appended 4 times in 28 preferences entries. **Fix (commit `c3ceb3b`)**: replaced `save_entry()` with `upsert_entry()` implementing 4-tier logic (exact skip → similar merge → contradiction resolve → new append). Post-distill `cleanup_core_memory()` runs global dedup across all 4 categories. The `distill_knowledge.py::_generate_check_source()` mechanically splits the troubleshooting section by numbered steps and creates a check_source for EVERY step, including user confirmations, screenshots, dead-end guesses, and communication noise. This produces bloated output (12+ check_sources from a single doc, many with `command == description` — just narrative text, not actual commands). The user rejected this: "过于繁杂，找到根因，其他无关排查去除".

**Fix (2026-06-28)**: Applied at the **Feishu→normal distillation stage** (lark-doc-distill.md template): 排查路径 now requires `只保留走向根因的关键路径，3-6步。跳过用户确认、截图沟通、失败猜测、重复验证。` With a lean normal/ Markdown (5 steps instead of 13), Phase 2 produces 5 clean check_sources instead of 12. The root fix belongs at Stage 1, not in distill_knowledge.py.

## Knowledge Distillation Pipeline

Two-stage process with different automation levels:

**Stage 1: Feishu doc → Normal Markdown** (`references/normal-distillation-prompt.md`) — ⚠️ **必须用户手动触发，不能自动跑**
- Strip chat noise, screenshots, dead ends. Keep commands, values, error messages.
- Output: clean Markdown with YAML frontmatter → `normal/<vendor>/<id>.md`
- Trigger: user explicitly asks to distill Feishu docs

**Stage 2: Normal Markdown → Core YAML** (`references/core-distillation-prompt.md`) — ✅ 可以自动化
- Extract check steps → check_source, root cause + fix → decision_source, assemble flow → full
- Output: JSON with `check_sources`, `decision_sources`, `full` keys → staging/ then core/
- Pipeline: extract → distill-knowledge → review → gate-full → commit

**Prompt style**: Keep prompts tight. No verbose explanations, no role-playing fluff. Format specs + rules + minimal example. Token cost matters — user will reject bloated prompts.

## Skills as Separate Files

Each skill lives in `self-opt/skills/<category>/<name>/SKILL.md`. Phase 1 Mine generates new skills into `self-opt/skills/self-opt/`. Phase 4 Router only touches the `description:` field in the YAML frontmatter — never the skill body content.
（Hermes 通过 `~/.hermes/skills → self-opt/skills` 软链接访问）

## Feishu Doc Discovery — Finding Troubleshooting Documents

When the user says "I have a document library, help me find distillation candidates" but hasn't provided a specific URL/token:

### Steps

1. **Check wiki spaces** (`lark-cli wiki spaces list --as user --format json`) — relevant spaces are usually named `IT`, `基础设施` (Infrastructure), or team-specific names.
2. **Explore space root** (`lark-cli wiki +node-list --space-id <id> --as user --format json`) — list top-level folders. Sub-directories may not appear here if they're organized as `<cite>` links within a Wiki page rather than as wiki nodes.
3. **Read root doc** (`lark-cli docs +fetch --api-version v2 --doc <obj_token> --as user --format pretty`) — extract `<cite>` tags to find sub-documents. Use `re.findall(r'<cite[^>]*doc-id=\"([A-Za-z0-9]+)\"...file-type=\"([^\"]+)\"...title=\"([^\"]*)\"...', content)`.
4. **If no structured document collection found** → ask the user directly: "请提供飞书文档集合的 URL 或 token"，instead of guessing.

### Limitations

- **Search API** (`POST /open-apis/search/v2/search`) requires `drive:drive` scope — most user auths won't have it. Don't bother unless the user explicitly authorized for Drive search.
- **Wiki node listing** (`+node-list`) only shows direct child nodes. Nested structures often live as `<cite>` links within pages, not as API-visible children. Always read the parent doc content.
- **Bot identity** fails on troubleshooting docs (code 3380004). Always use `--as user` with `docs` domain scope.
- **lark-cli `_notice.update`**: When CLI output includes `_notice.update` with a newer version, proactively offer to update with `lark-cli update` before proceeding. It also updates skills.

### When You Have a Doc Collection Token

Follow the batch workflow below. Use the token to fetch the index doc, extract all `<cite>` links, deduplicate, and batch-distill via `delegate_task`.

## Stage 1: Batch Execution Workflow

When distilling a large set of Feishu troubleshooting docs (10-32+) into normal Markdown, use **parallel subagents** for efficiency:

### Preconditions

1. **lark-cli must be authenticated as user, not bot** — bot tokens lack view permission on non-public docs. Run `lark-cli auth login --domain docs` if user identity is missing. Check with `lark-cli auth status` (look for `"identity": "user"`).
2. **Output directories exist**: `mkdir -p ~/.hermes/knowledge/normal/{huawei,arista,network,misc}`
3. **Check pre-existing registry**: Read `Agent学习/Agent self-optimization Frame/已蒸馏文档.md` in the Obsidian vault first. Skip any token already listed. If the file doesn't exist, create it with `# 目录` and `# 子文档` sections.

### Batch Workflow

1. **Parse the index doc**: Fetch the master table doc that lists all sub-docs (`lark-cli docs +fetch`). Extract `doc-id` and `title` from `<cite doc-id="..." title="...">` tags. Deduplicate docs that appear multiple times.
2. **Batch via delegate_task**: Split into batches of 8, dispatch each batch as `delegate_task` with `toolsets=["terminal","file"]`. Each subagent gets the full distillation prompt plus its batch doc-tokens and titles. 3 concurrent max; dispatch remaining after prior batches finish.
3. **Within each subagent**: Read each doc with `lark-cli docs +fetch --api-version v2 --doc "<token>" --scope full`, parse JSON output, extract `data.document.content`, distill to structured Markdown per `normal-distillation-prompt.md`, write to `~/.hermes/knowledge/normal/<vendor>/<id>.md`.
4. **Consolidate**: After all batches complete, inspect files — frontmatter completeness, section presence, file count matches doc count (minus permission-denied skips).

5. **Write distillation registry** (cross-session dedup): After consolidation, write/append the full list of distilled doc tokens to a persistent registry file so future sessions can check before re-distilling. Format per vendor directory:

   ```markdown
   ## 已蒸馏（<vendor>/ 目录）
   
   | Token | 标题 | 文件 |
   |-------|------|------|
   | `<token>` | 标题 | `<vendor>/<id>.md` |
   ```

   The registry lives in the user's Obsidian vault: `Agent学习/Agent self-optimization Frame/已蒸馏文档.md`. Use tables organized by vendor directory (`arista/`, `huawei/`, `network/`, `misc/`), plus a `⚠️ 无权限跳过` section for docs that returned 3380004. Before starting any distillation session, first read this registry and filter out any token already present.

### ID Generation

Generate `id` from Chinese title → kebab-case English:
- Strip `【解决】`/`【未解决】`/`[解决]` prefix and IT ticket number
- Translate key terms: 认证→auth/authentication, 无法→failure, 有线→wired, 无线→wireless, 设备→device, 地址→address, 访问→access
- Format: lowercase, hyphens between words, e.g. "PDI角色用户有线无法认证" → `pdi-youxian-wufa-renzheng`

### Vendor Directory Assignment

| Device type | Directory |
|---|---|
| 华为交换机 | `huawei/` |
| Arista | `arista/` |
| 白盒交换机/Cisco | `network/` |
| 非网络设备/终端/Mac/Win/Phone | `misc/` |
| SD-WAN/VPN/DNS/路由协议 | Root `normal/` (no subdirectory) |

### Pitfalls

- **Permission errors**: If a doc returns error code 3380004 (no permission), skip it silently and note in summary. Do not retry — it's an ACL issue, not transient.
- **Bot vs user**: Using bot identity will fail on almost all troubleshooting docs. Always ensure user identity with `docs` domain scope.
- **Rate limiting**: 3 concurrent `delegate_task` max. For 32 docs, split into 4 batches of 8 and dispatch after prior batches finish.
- **Image noise**: Feishu doc content includes `<img>` tags with verbose `alt` text (screen reader descriptions of screenshots). These are noise — strip them during distillation. The only useful info in `<img>` is embedded text in the `alt` attribute (if present), otherwise discard.
- **Verify after batch**: Check each subagent created the expected number of files. A subagent may complete successfully but have actually failed on some docs due to permission issues.
- **Don't skip registry check**: Always read the pre-existing registry before distilling. Tokens in the registry have already been processed. Re-distilling wastes tokens and creates duplicates.

## Design Decisions (Cumulative)

1. **YAML vs DB**: YAML 存储，不切 DB
2. **飞书→normal**: 手动触发，不可自动。normal→core: Phase 2 管线，可自动
3. **P0 review gate**: commit 前人工审批，`.review_state.json` 强制拦截
4. **工程风格**: 渐进（Phase 1→3→4→2），简洁优先（cron 一行，纯正向过滤）
5. **回滚**: 手动，不做自动回滚
6. **core Knowledge 安全约束**: core Knowledge 是所有知识资产的核心，任何变更必须经用户同意（Staging→Gate-Full→Review→Commit）。Cron 自动消化仅限 skill，knowledge correction 只生成报告不自动写入
6. **Benchmark skill 名对齐**: Router 索引 + benchmark 的 `skill` 字段必须匹配 skill frontmatter 的 `name:`，**不是目录名**。E.g. 目录 `mab-fallback-dot1x-diagnosis/` → frontmatter name 为 `MAB Fallback 802.1X 故障诊断`
7. **Gate-Lite Benchmark 优先级**: Skill Execution Benchmark（精准匹配 skill_name）→ 知识库 Benchmark（通用）→ 降级通过（coverage=3）
8. **蒸馏文档去重**: 飞书→normal 蒸馏前必须查 `已蒸馏文档.md` 做 token 去重
9. **CJK 匹配策略**: router.py 用字符级重叠匹配（无需 jieba 依赖），准确率 40.8% top-1。短查询（<10 中文字符）命中率低
10. **SkillOpt 训练循环**: Rollout→Reflect→Edit→Gate-Lite 完整闭环（skillopt.py 578 行）。每次 Edit 前自动备份 `.bak`，最终 Gate-Lite 终验不倒退才写入
11. **Crystallization 门槛**: 最少 3 个排障 session 才触发新 skill 自动生成。单次 LLM 调用处理所有 session。两重去重：文件名 + Router 语义重叠（threshold=0.6）
12. **Core Memory v2.0 自动优化**: upsert_entry 4 层去重 + cleanup_core_memory 全局冲突解决，集成到 distill cron（commit `c3ceb3b` / `eb378eb`）。每条记录含 duplicate_count 权重、added/updated 日期。生产数据 71→33 条（清理后），每天蒸馏后自动维护。
13. **Skills 目录迁移到 self-opt**: 所有 157 个 skill 从 `~/.hermes/skills/` 迁移到 `~/script/hermes-self-opt/skills/`。Hermes 通过软链接 `~/.hermes/skills → self-opt/skills` 保持兼容。self-opt 框架通过 `__init__.py::SKILLS_ROOT` 统一引用 canonical 路径。writer.py 写入 `self-opt/skills/self-opt/`。Phase 3/4（optimize、crystallize、router）现在扫描全部 157 个 skill，不再仅限 self-opt 生成的部分（commit `c78d626`）。

## Handover & Pending Items

### 已完成 (2026-06-28)

| 项 | commit |
|----|--------|
| 用户反馈回流 | `1af51cf` — feedback.py (435行) + CLI |
| 命令重命名 run→process, run-pipeline→knowledge-build | `4190adb` |
| 路由事件收集 + 触发率监控 | `0c833a6` — router.py monitor() + record_match 扩展 |
| **Gate-Lite LLM Judge 空 JSON** | `f11a687` / `2ea4257` — gate.py: 4-strategy `_extract_json()` 支持 markdown 代码块、inline JSON、嵌套 JSON 提取。原 `try/except json.loads + 转义修复` 无法处理 LLM 常见的 markdown code block 格式导致所有 skill 降级 coverage=3。新策略：直接解析 → markdown 代码块 → inline {} → 转义修复。8 项 ad-hoc 测试全部通过。 |
| **Core Memory v2.0 自动优化** | `c3ceb3b` / `eb378eb` — core_memory.py: upsert_entry 4 层去重（exact→similar→contradiction→new）+ cleanup_core_memory 全局冲突解决 + duplicate_count 权重字段 + added/updated 日期追踪。集成到 self-opt-distill cron。生产数据 71→33 条，20/20 ad-hoc 验证通过。 |
| **self-opt-daily-bugfix cron** | `e83481499353` — 每天 06:00 自动读日志、找 bug、修、记录 Obsidian 更新记录、git commit。模型 deepseek-v4-flash。技能: self-opt-daily-bugfix。 |
| **Skills 目录迁移** | `c78d626` — 157 个 skill 从 `~/.hermes/skills/` 迁到 `self-opt/skills/`，软链接保持 Hermes 兼容。`__init__.py::SKILLS_ROOT` 统一路径。Phase 3/4 现在扫描全部 skill。 |

### 确认不做

| 项 | 原因 |
|----|------|
| 路由自动回滚 | 2026-06-28 确认弃用，只做收集+监控 |

### 待做项

| # | 缺口 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | Router 中文准确率 53.1% | 🟢 低 | 已从 40.8% 提升到 53.1% (jieba + MIN_SCORE=0.2)，可继续优化但非紧急 |
| 2 | 替换 Hermes Curator | 🟡 中 | 自建 curator.py；22 skill 已 pin；一个月后（约 2026-07-28）评估 |

### Handover Documents

每次 session 结束后的交接文档保存到 Obsidian:
`Agent学习/Agent self-optimization Frame/交接文档/<date>_<topic>.md`

### Framework Cross-Reference

当审查待做项（pending items）时，必须以框架构思文档为权威来源交叉核对：
- 框架文档路径: `Agent学习/Agent self-optimization Frame/Agent self-optimization框架构思.md`
- 待做项清单: `Agent学习/Agent self-optimization Frame/待做项清单.md`
- 待做项优先级如与框架设计冲突，以框架为准（e.g. 框架标注路由层「暂不深入研究」→ Router 准确率提升不应标 🔴高）
- 框架中提到的模块如未出现在待做项中，应补入（e.g. Crystallization 新 Skill 自动生成、用户反馈回流）

## References

- `references/aruba-ap-troubleshooting.md` — real session harvest of AP LED troubleshooting
- `references/hermes-self-opt-repo.md` — code repository structure and key files
- `references/normal-distillation-prompt.md` — Stage 1: Feishu doc → Normal Markdown prompt
- `references/core-distillation-prompt.md` — Stage 2: Normal Markdown → Core YAML prompt
- `references/stage1-batch-workflow.md` — detailed batch execution example from a real 31-doc distillation session
- `references/knowledge-pipeline-watchdog.md` — incremental file-change detection pattern for Phase 2 auto-sync cron
- `references/skill-benchmark-design.md` — Skill Benchmark 两层结构设计（Router Benchmark + Execution Benchmark）
- `references/handover-pending-items.md` — 交接文档处理工作流 + 当前待做项 + 框架缺口
- `references/skillopt-architecture.md` — Phase 3 SkillOpt 优化循环架构（Rollout→Reflect→Edit→Gate-Lite）
- `references/router-accuracy-diagnostic.md` — Router 准确率诊断方法：benchmark 驱动 miss 分类 + 根因分析
- `references/phase2-testing-workflow.md` — Phase 2 端到端测试工作流（飞书文档 → normal/ → knowledge-build）
- `references/legacy-memory-migration.md` — 传统 MEMORY.md → Core YAML 一次性迁移流程（2026-06-29 执行）

## Related Skills

- `self-opt-event-log` — 查看 self-opt 所有事件日志（change.log + logs/*.json + watchdog.log），CLI: `hermes self-opt eventlog`
- `self-opt-daily-bugfix` — 每日 06:00 自动检查 self-opt 日志，发现问题、修复、记录 Obsidian 更新记录、git commit。Bug 分级：🔴 必修 → 🟡 LLM 评估 → 🟢 不修。
