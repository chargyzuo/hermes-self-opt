# Phase 3 SkillOpt Architecture

> Implemented 2026-06-28, commit `8bf160d`

## Module: `skillopt.py` (578 lines)

### Core Loop

```
optimize_skill(skill_name, max_iterations=3)
  │
  ├── Load skill SKILL.md via _find_skill_file() (frontmatter name + dir name fallback)
  ├── Load benchmark entries via _load_benchmark_for_skill() (skill_execution_benchmark.json)
  │
  └── For iteration 1..max_iterations:
        │
        ├── ROLLOUT: For each benchmark entry
        │     └── run_rollout(skill_content, scenario)
        │           └── LLM prompt: "你是网络排障 agent，加载此 skill，遇到此场景..."
        │           └── Output: trace (逐步执行的排障操作文本)
        │
        ├── REFLECT: For each benchmark entry
        │     └── run_reflect(skill_content, trace, benchmark)
        │           └── LLM prompt: compare trace vs required_steps + redlines
        │           └── Output: {coverage_score, redline_pass, missed_steps, bad_guidance, suggestions}
        │
        ├── If all benchmarks pass (score >= 3, redline_pass=true) → BREAK
        │
        └── EDIT:
              └── run_edit(skill_content, reflect_summary)
                    └── LLM prompt: "根据反馈修改 skill，只改有问题部分"
                    └── Output: modified SKILL.md content
  │
  └── GATE-LITE (final validation):
        └── gate.py::gate_skill(modified_content, skill_name=skill_name)
              └── Skill Execution Benchmark scoring (same as Phase 1 Gate-Lite)
              └── Only write if decision == "pass"
```

### Key Functions

| Function | Lines | Description |
|----------|-------|-------------|
| `_find_skill_file(name)` | ~20 | Find SKILL.md by frontmatter name or directory name under `self-opt/skills/` |
| `_read_skill(name)` | ~5 | Read SKILL.md content |
| `_write_skill(name, content)` | ~15 | Backup then write; creates `.bak` alongside original |
| `_load_benchmark_for_skill(name)` | ~20 | Load from `skill_execution_benchmark.json`, filter by `skill` field |
| `_format_benchmark(bm)` | ~15 | Format single entry for LLM consumption |
| `run_rollout(skill, scenario)` | ~10 | LLM-simulated skill execution |
| `run_reflect(skill, trace, bm)` | ~20 | Compare trace against benchmark |
| `run_edit(skill, reflect)` | ~20 | Generate skill modifications |
| `optimize_skill(name)` | ~100 | Driver: orchestrates the full loop |
| `optimize_all()` | ~25 | Batch: all skills with benchmark entries |

### CLI

```bash
hermes self-opt optimize                          # All 8 skills with benchmark entries
hermes self-opt optimize --skill-name <name>      # Single skill
hermes self-opt optimize --dry-run                # Report only, no writes
hermes self-opt optimize --max-iters 5            # Up to 5 iterations
hermes self-opt optimize --json                   # Machine-readable output
```

### Design Decisions

1. **Backup-before-write**: `_write_skill()` always renames current file to `.bak` before writing new content. No automatic rollback — user must manually restore if needed.
2. **Max 3 iterations by default**: matches `MAX_ITERATIONS = 3` constant. Can be overridden via `--max-iters`.
3. **PASS_THRESHOLD = 3**: coverage_score >= 3 AND redline_pass = true required to skip Edit step.
4. **Combined feedback**: When multiple benchmarks fail, missed_steps/bad_guidance/suggestions are combined (deduped via set) into one Edit prompt. This avoids redundant LLM calls.
5. **Gate-Lite as final gate**: Reuses existing `gate.py::gate_skill()` with Skill Execution Benchmark. Same validation as Phase 1 skill generation.
6. **Frontmatter name priority**: `_find_skill_file()` first tries YAML frontmatter `name:` field, then falls back to directory name. This aligns with router.py's indexing strategy.

### Testability

Non-LLM paths are independently testable (31 ad-hoc verification checks passed):
- `_find_skill_file` — name resolution
- `_read_skill` / `_write_skill` — file I/O
- `_load_benchmark_for_skill` — JSON filtering
- `_format_benchmark` — text formatting
- `_parse_json` — response parsing (plain JSON, code blocks, invalid)
- `_load_all_benchmark_skills` — skill enumeration

LLM paths require Hermes runtime (agent.auxiliary_client).

### Benchmark Coverage

8 skills in `skill_execution_benchmark.json`:
- `huawei-mac-auth-debug` (1 entry: sb-001)
- `ap-yellow-led-troubleshoot` (1 entry)
- `安卓wifi受限排查skill` (1 entry)
- `MAB Fallback 802.1X 故障诊断` (1 entry)
- `mihomo-fake-ip-dns-hijack-troubleshoot` (1 entry)
- `swg-connectivity-troubleshooting` (1 entry)
- `aruba-ap-troubleshooting` (1 entry)
- `huawei-switch-auth-troubleshooting` (1 entry)

Each entry has: scenario, required_steps (list), redlines (list), difficulty.
