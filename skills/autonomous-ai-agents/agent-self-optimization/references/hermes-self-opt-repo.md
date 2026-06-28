# hermes-self-opt Repository Structure

Repo: `/Users/bytedance/script/hermes-self-opt/` (GitHub: chargyzuo/hermes-self-opt)

```
hermes_self_opt/
├── harvest.py            # Session DB reader + dialog cleaner
├── filter.py             # Pure forward keyword pre-filter (≥3 hits)
├── mine.py               # Auxiliary LLM extracts knowledge/memory/skill
├── gate.py               # Gate-Lite: basic checks (len, secret) + LLM Judge
├── writer.py             # write_daily(), write_skill(), write_log()
├── pipeline.py           # run_session(), run() — full orchestration
├── distill.py            # Deep Dream: daily → core memory (Phase 3)
├── core_memory.py        # Core Memory YAML read/write
├── router.py             # Skill index, query, gap detection, rewrite, rollback
├── cli.py                # hermes self-opt subcommand definitions (655 lines, Phase 1-4 + P0-P2)

│  # ── Phase 2 (implemented 2026-06-27, P0/P1/P2 complete) ──
├── extractor.py          # Parse normal/*.md → structured dicts (195 lines)
├── distill_knowledge.py  # 3-layer dedup + LLM confidence → check/decision/full YAML (522 lines)
├── gate_full.py          # 4 checks + export_schema() + LLM Judge (750 lines)
├── committer.py          # staging→core atomic move + _index.yaml (330 lines)
└── reviewer.py           # P0: review gate — scan, approve, hash-detect (287 lines)

~/.hermes/self-opt/
├── logs/                 # Per-run JSON logs
├── router.db             # Skill index + match events + backups
└── benchmark.json        # Troubleshooting test cases

~/.hermes/knowledge/
├── normal/               # 80 MD files (arista/19, huawei/8, network/24, misc/12, root/23)
├── core/                 # YAML core — 387 entries (294 checks, 46 decisions, 47 full)
│   ├── _index.yaml       # Inverted index: tags→ids, triggers→full_id
│   ├── check-source/     # 294 reusable check atoms
│   ├── decision-source/  # 46 reusable conclusion atoms
│   └── full-*.yaml       # 47 routing graphs
└── self-opt/
    ├── staging/           # Temp workspace for Gate review
    ├── committed/         # 387 archive backups
    └── benchmark.json

~/.hermes/memories/
├── daily/<date>.md       # Per-day memory fragments
├── core/*.yaml           # Distilled long-term memory
├── MEMORY.md             # Deprecated (historical reference)
└── USER.md               # Deprecated (historical reference)

Install: pip install -e /Users/bytedance/script/hermes-self-opt
Hermes bridge: hermes_cli/subcommands/self_opt.py + main.py patch
```

## Key Design Patterns

1. **Pure forward filtering** — never use negative keyword exclusion. AP troubleshooting sessions contain words like "笔记" or "文档" that would be misclassified as non-troubleshooting. Match on ≥3 positive keywords only.

2. **Basic checks before LLM** — length check, sensitive content scan, and empty-content check all run locally (<1ms) before any LLM call. Saves token cost on invalid inputs.

3. **Memory ≠ Knowledge** — Memory stores user preferences, habits, environment configs. Knowledge stores troubleshooting logic chains (trigger → check → decision). They come from different extraction paths in Mine.

4. **Staging before commit** — Knowledge base changes go through a staging area (like Git index) requiring Gate-Full validation before entering core/. Committed files are archived for rollback.

## Phase 2 Module Details

### extractor.py
- `extract_one(filepath)` → dict with `id`, `frontmatter`, `sections`, `commands`, `device_type`, `tags`, `source`
- `extract_all(normal_dir=None)` → list of dicts
- Section detection via aliases: 现象→symptoms, 排查路径→troubleshooting, 根因→root_cause, 方案→solution, 操作→actions, 备注→notes
- device_type inferred from file path + tags

### distill_knowledge.py
- `distill_and_generate(extracted_list, dry_run=False, auxiliary_client=None)` → result dict
- Dedup uses `SequenceMatcher` (stdlib, no deps) for semantic similarity
- `_id_slug(text, prefix)` generates safe YAML ids (truncated at 60 + prefix)
- **P2-6**: `_evaluate_confidence_llm(root_cause, solution, actions, tags, auxiliary_client)` — LLM confidence evaluation with heuristic fallback. Replaces the old section-count heuristic.

**PITFALL**: When embedding JSON examples in LLM prompts used with Python `.format()`, double all braces: `{{"key": "value"}}`. Single braces collide with format placeholders and raise `KeyError`. This bit us on `CONFIDENCE_EVAL_PROMPT` — the `{"confidence": "high|medium|low"}` example broke at runtime.

### gate_full.py
- `run_gate_checks(staging_dir=None, verbose=False)` → `{passed, failed, errors, all_passed}`
- Schema: manual implementation (no deps); falls back if jsonschema not installed
- Reference check: collects all IDs from staging ∪ core before cross-referencing
- DFS: three-color white/gray/black marking over `redirect` graph edges

### committer.py
- `commit_to_core(gate_result=None, dry_run=False)` — gates by default
- `rollback_last_commit()` — restore from committed/ archives
- `stats()` — KB statistics
- Atomic: copy to committed/ first, then move to core/

## ✅ P0 Security Gaps — Resolved (2026-06-27)

The framework's hard rule **"knowledge base writes must go through user approval"** is now enforced:

1. **`hermes self-opt review`** — scans staging/, shows change summary, asks y/n. Use `-y` to auto-approve.
2. **Commit intercept** — `hermes self-opt commit` checks `.review_state.json`:
   - No review → rejected
   - Review rejected → rejected
   - Staging changed since review → rejected (hash-based)
3. **`--skip-review`** bypasses for automation/cron.

Implementation: `reviewer.py` (scan_staging, save/load_review_state, staging_changed_since_review).

## ✅ P1 Completion (2026-06-27)

**P1-3: Schema export** — `gate_full.py::export_schema()` exports three-type JSON Schema to `core/_schema.yaml` (144 lines). Auto-sync after every successful commit. CLI: `hermes self-opt export-schema [--dry-run]`.

**P1-4: LLM Judge** — `gate_full.py::run_llm_judge()` reuses `benchmark.json` for knowledge quality scoring (coverage 0-5, redline check). Advisory only — does NOT block commit. CLI: `hermes self-opt judge [--benchmark] [--verbose]` or `gate-full --judge`.

## ✅ P2 Completion (2026-06-27)

**P2-5: run-pipeline** — `cli.py::_handle_run_pipeline()`:
- One-click pipeline: extract → distill → review → gate → commit
- Flags: `--yes`/`-y`, `--dry-run`, `--skip-gate`, `--verbose`
- Five-stage progress display with per-stage ✅/❌ status
- Fails fast — any stage failure stops the pipeline with a clear error

**P2-6: LLM Confidence Evaluation** — `distill_knowledge.py::_evaluate_confidence_llm()`:
- LLM evaluates decision_source confidence (high/medium/low) based on root cause clarity, verification steps, and reproducibility
- Prompt: `CONFIDENCE_EVAL_PROMPT` — Chinese, evaluates `{tags}`, `{root_cause}`, `{solution}`, `{actions}`
- Graceful degradation: LLM unavailable → heuristic (3 sections=high, 2=medium, 1=low)
- Auto-loads `agent.auxiliary_client.call_llm()`; passed through `distill_and_generate(auxiliary_client=...)`

**PITFALL — `.format()` brace escaping**: Embedded JSON examples in LLM prompts (e.g., `{"confidence": "high"}`) must use double braces `{{"confidence": "high"}}` when the prompt is used with Python's `str.format()`. Otherwise `.format()` tries to substitute `{confidence}` as a placeholder → `KeyError`. This was caught during verification and fixed in commit `dcaa8ac`.

**PITFALL — Ad-hoc verification**: When editing code without a canonical test suite, create a focused ad-hoc verification script under the OS temp directory with a `hermes-verify-` prefix. Run it, clean it up, and report results explicitly as ad-hoc verification. Example: `python3 -c "import tempfile,os,subprocess; ..."`. The script should test each changed function's happy path + edge cases.

## Design Docs (Obsidian)

Absolute path: `/Users/bytedance/Library/Mobile Documents/com~apple~CloudDocs/笔记/Obsidian Vault/Agent学习/Agent self-optimization Frame/`

| File | Purpose |
|------|---------|
| `核心知识库存储设计.md` (479行) | v4 three-type atomic architecture, §7 YAML vs DB decision (finalized: YAML) |
| `Phase2 核心知识库YAML管线实施文档.md` | Merged implementation doc with module details |
| `Agent self-optimization框架构思.md` | Six design principles |
| `开发日记.md` | Development diary with Phase 2 record |
| `交接Prompt-P2完成.md` | Latest handoff (P2 complete, remaining gaps listed) |
| `已蒸馏文档.md` | Token registry — skip already-distilled docs before re-running pipeline |

## Cron Schedule

```bash
03:00 → self-opt-nightly   (Harvest → Mine → Gate → Daily Memory)
04:00 → self-opt-distill   (Daily → Core Memory 蒸馏)
05:00 → self-opt-router    (Rebuild index + gap scan)
# ⚠️ MISSING: knowledge-pipeline cron for normal/ → core/ auto-rebuild
#    Workaround: hermes self-opt run-pipeline -y (manual)
```
