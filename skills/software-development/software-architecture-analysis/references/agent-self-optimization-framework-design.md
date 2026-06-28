# Agent Self-Optimization Framework Design

Design decisions and architecture patterns established during the June 2026 research sessions with Zuo Jiajie.

## Knowledge Base: Staging → Review → Commit Pattern

The knowledge base (troubleshooting docs + case library) uses a Git-like staging workflow because it is the authoritative source for network fault diagnosis:

```
Mine Pipeline (auto-extract from sessions)
        │
        ▼
┌──────────────────────┐
│  📦 Staging (暂存区)  │  ← agent 排障时不可见
│  待审查的变更集        │
└──────────┬───────────┘
           │ You review
           ▼
┌──────────────────────┐
│  🤖 Gate 自动验证     │  ← Benchmark 不倒退才通过
└──────────┬───────────┘
     ┌────┴────┐
     ▼         ▼
  ✅ 通过     ❌ 失败 → 退回 Staging
     │
     ▼
┌──────────────────────┐
│  📚 正式知识库        │  ← agent 直接引用
│  (commit 后才更新)    │
└──────────────────────┘
```

### Key Rules
- Staging 中的变更 agent 不可见（不会引用未确认的知识）
- 用户可以编辑 Staging 内容（修正措辞、补充细节、合并重复案例）
- Gate 自动验证确保 Benchmark 不倒退（即使用户同意了也要过测试集）
- 每次 commit 自动备份（复用 Hermes curator backup）
- 人工导入的排障文档直接写入正式知识库（源头可信，不需要 Staging）

## Knowledge ≠ Memory Distinction

**Critical clarification** — these are separate concerns with different data flows:

| Aspect | Memory | Knowledge Database |
|--------|--------|-------------------|
| What it stores | User metadata (preferences, habits, env config) | Network troubleshooting procedures, fault cases |
| Source | Session → Deep Dream distillation | Troubleshooting docs (manual) + Session → Mine (auto) |
| Update cadence | Daily (idle-triggered distillation) | Per-incident (when new fault case resolved) |
| Affects | Agent interaction style (how it talks) | Agent diagnosis ability (what it knows) |
| Validation | None needed (personal, low risk) | Gate + Review required (high risk — lives depend on correct diagnosis) |
| Auto-update | Yes, fully automated | No — Staging → Review → Commit only |

**Memory does NOT generate knowledge.** Deep Dream distills user behavior patterns from sessions into core memory — it never produces troubleshooting knowledge. Knowledge comes only from: (a) manual troubleshooting documents, (b) Mine pipeline extracting fault cases from sessions.

## Pipeline Architecture

```
Trigger (cron/idle/manual)
    │
    ▼
Pipeline: Harvest → Mine → Edit
    │         │         │
    │         │         └──→ Skills (create/optimize)
    │         │              Knowledge (→ Staging)
    │         │              Memory (→ Deep Dream distillation)
    │         │
    │         └──→ Discover patterns from sessions
    │              Detect skill routing gaps
    │              Find un-documented fault types
    │
    └──────→ Collect recent sessions + usage stats + feedback signals
```

## Reference Projects Mapping

| Project | Where in this framework | What it contributes |
|---------|------------------------|---------------------|
| SkillOpt | Skills layer optimization logic | Training Loop + Validation Gate + LR Scheduler |
| Hermes Self-Evolution | Skills layer alternative optimizer | GEPA genetic algorithm as drop-in replacement |
| GenericAgent | Skills layer generation logic | Crystallization: discover→generate from session patterns |
| CowAgent | Memory layer + holistic evolution | Deep Dream distillation + 3-layer memory architecture |
| selftune | Routing layer + verification | Description rewriting + auto-rollback + trigger rate monitoring |
| Hermes Curator | Infrastructure | session DB, skill_usage stats, backup, lifecycle management |
| Troubleshooting docs (user asset) | Knowledge layer datasource | Structured procedures → Benchmark QA pairs → RAG context |
