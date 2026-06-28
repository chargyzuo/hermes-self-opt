---
name: parallel-agy-review
description: "Execute the same code review/analysis task in parallel with agy (Antigravity CLI), then integrate both results into a final answer."
version: 1.0.0
author: Hermes Agent
---

# Parallel agy Review

Run the same review/analysis task simultaneously with agy (Antigravity CLI) and
yourself, then synthesize both perspectives.

## When to Use

- Complex code security reviews where a second AI perspective adds value
- Finding hardcoded credentials in source code
- Any multi-perspective analysis that benefits from model diversity

## Steps

### 1. Define the task

Clearly state the task goal and context. Be specific — both agents need the same
information.

### 2. Delegate to agy (parallel)

Use `delegate_task` to send the task to agy. The subagent runs:

```bash
script -q /dev/null agy -p 'PROMPT' --print-timeout 120s
```

⚠️ Model note: Claude models (Opus/Sonnet Thinking) regularly time out in agy's --print mode. For reliable results use the default Gemini Flash model. The brief delegation prompt is still sufficient for code review.

**IMPORTANT**: Set `toolsets=["terminal", "file"]` so the subagent can read files.

The delegation runs in parallel — you execute the same task yourself at the same
time.

### 3. Execute yourself (parallel)

While agy runs, analyze the codebase yourself using your own tools (terminal,
read_file, execute_code, etc.).

### 4. Wait for agy result

The `delegate_task` result comes back when agy finishes.

### 5. Integrate results

Compare your findings with agy's. Note:
- Items both of you found (high confidence)
- Items only one of you found (verify independently)
- Disagreements (resolve by re-checking)

### 6. Deliver final answer

Present the integrated findings in the requested format. If the user wants a
specific output format, follow it exactly.

## Pitfalls

- agy runs with a separate context — it does NOT have access to your conversation
  history. Put ALL relevant context in the delegation prompt.
- Set `--print-timeout` high enough (120s+) for complex analysis.
- agy doesn't see the terminal output filter — it may show raw passwords that
  your terminal would censor. This is a feature, not a bug.
- Both agents might miss the same thing. Cross-verify with manual checks.
