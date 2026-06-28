# CJK Skill Routing Optimization Pattern

From Phase 4 Router accuracy fix (commit `79267e1`): improved Chinese query matching from 40.8% → 53.1% top-1, reduced no_results from 17/49 to 4/49.

## Problem

Chinese text routing via character-level overlap alone gives ~41% accuracy. Short queries (3-8 characters) with sparse keyword overlap get filtered out by MIN_SCORE threshold.

## Root Causes

1. **MIN_SCORE too high**: 0.3 threshold blocks queries where character overlap is partial
2. **Split fails on Chinese**: `str.split()` on Chinese text with no spaces produces one giant token, term matching scores zero
3. **Description mismatch**: Skill descriptions use technical English, user queries use colloquial Chinese

## Solution: Hybrid Character-Level + jieba

### Step 1 — Install jieba

```
pip install jieba
```

### Step 2 — Pre-tokenize CJK queries

```python
try:
    import jieba
except ImportError:
    jieba = None  # graceful degradation

# In query():
jieba_tokens = []
if has_cjk and jieba:
    jieba_tokens = [t.lower() for t in jieba.cut(user_input) if len(t.strip()) >= 1]
```

### Step 3 — Hybrid scoring (primary: char-level, bonus: jieba)

```python
if has_cjk:
    # Primary: character-level overlap (weight 0.5)
    cjk_query_chars = [ch for ch in lower if '\u4e00' <= ch <= '\u9fff']
    cjk_desc_chars = set(ch for ch in dl if '\u4e00' <= ch <= '\u9fff')
    if cjk_query_chars and cjk_desc_chars:
        char_hits = sum(1 for ch in cjk_query_chars if ch in cjk_desc_chars)
        score += (char_hits / len(cjk_query_chars)) * 0.5

    # Bonus: jieba multi-char tokens (len>=2, weight 0.15)
    if jieba_tokens:
        jieba_hits = 0.0
        for tok in jieba_tokens:
            if len(tok) >= 2 and tok in dl:
                jieba_hits += 1.0
            elif len(tok) >= 2 and tok in nl:
                jieba_hits += 0.5
        if jieba_hits > 0:
            score += min(jieba_hits / len(jieba_tokens), 1.0) * 0.15
```

### Step 4 — Lower MIN_SCORE

```python
MIN_SCORE = 0.2  # was 0.3
```

## What Did NOT Work

- **Pure jieba only**: Replacing character-level entirely with jieba caused a REGRESSION (40.8% → 26.5%). jieba tokens like "黄灯" don't appear as substrings in English-heavy descriptions.
- **Hybrid with balanced weights (0.35 char + 0.25 jieba)**: Still worse than original. Character-level needs to be the dominant signal.

## Key Insight

Character-level overlap is the **dominant signal** for CJK matching because it catches any shared characters regardless of tokenization. jieba works as a **small bonus** for multi-character tokens that happen to match. Never let jieba replace character-level overlap — always additive.

## Benchmark Results

| Metric | Before | After |
|--------|--------|-------|
| top-1 | 40.8% | 53.1% |
| top-3 | 46.9% | 61.2% |
| no_results | 17/49 | 4/49 |

Remaining 4 misses are description gaps (user terms not in skill descriptions) — handled by `find_description_gap()` + `rewrite_description()`.
