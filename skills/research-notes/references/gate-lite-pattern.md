# Gate-Lite Optimization Pattern

Extracted from Agent Self-Optimization Phase 1 development (Day 3).

## Problem

In any LLM-in-the-loop validation system, calling the LLM for every input is expensive (time + token cost). Some inputs can be rejected with simple local checks.

## Solution

Run **cheap local checks before expensive LLM calls**:

```
input → [local checks: <1ms each]
  ├─ empty? → skip
  ├─ too long? → fail
  ├─ contains secrets? → fail
  └─ passes all → [LLM Judge: 2-5s]
```

## Concrete Example (Python)

```python
def gate_skill(content):
    if not content.strip():
        return {"decision": "skip", "reason": "empty"}
    if len(content) > MAX_CHARS:
        return {"decision": "fail", "reason": "too long"}
    if has_sensitive_patterns(content):
        return {"decision": "fail", "reason": "secret detected"}

    # Only reach here if all local checks passed
    return llm_judge_score(content)
```

## Key Insight

The local checks catch ~80% of rejectable inputs at zero LLM cost. The LLM is only called for inputs that genuinely need reasoning (benchmark coverage scoring, redline analysis).

## Applicability

Any agent pipeline that uses an LLM as a validator should adopt this pattern. Always ask: "can I reject this without calling the LLM?"
