# Phase 4: 用户反馈回流 — Implementation Plan

> **For Hermes:** TDD implementation, commit after each task.

**Goal:** 用户纠正信号 → 标记待审查 → 空闲时处理 → 自动修正 skill/knowledge

**Architecture:** 新模块 `feedback.py` + CLI 集成 + `~/.hermes/knowledge/self-opt/corrections/` 目录结构

**Tech Stack:** Python stdlib + json + pathlib + yaml

---

## 数据流

```
用户纠正 → capture_feedback() → pending/ JSON
                                   ↓
                    process_feedback() (手动或 cron)
                                   ↓
                    load skill → LLM patch → Gate-Lite → write
                                   ↓
                           processed/ 或 rejected/
```

## 存储结构

```
~/.hermes/knowledge/self-opt/corrections/
├── pending/
│   └── correction-20260628-001.json
├── processed/
│   └── correction-20260628-001.json
└── rejected/
    └── correction-20260628-002.json
```

## 纠错 JSON 格式

```json
{
  "id": "correction-20260628-001",
  "timestamp": "2026-06-28T22:00:00",
  "target_type": "skill",
  "target": "huawei-mac-auth-debug",
  "correction": "Step 3 应该先 dis aaa online-fail-record",
  "source": "user",
  "status": "pending",
  "applied_diff": null,
  "gate_result": null
}
```

---

### Task 1: feedback.py — 核心模块 (capture + list)

### Task 2: feedback.py — process_feedback (单条处理)

### Task 3: feedback.py — process_all (批量 + Gate-Lite)

### Task 4: CLI 集成 — feedback 子命令 (capture/list/process/reject)

### Task 5: 验证 — 非 LLM 路径测试 + git commit
