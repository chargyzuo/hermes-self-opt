---
name: software-architecture-analysis
description: "Deconstruct complex software systems: architecture breakdown, harness analysis, trade-off tables, integration assessment."
version: 1.1.0
author: Zuo Jiajie + Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [architecture, design, codebase-analysis, system-design, evaluation, comparison]
    related_skills: [systematic-debugging, plan, codebase-inspection, spike]
---

# Software Architecture Analysis

Analyze and explain complex software systems at the architectural level — with harness decomposition, layer diagrams, data flow tracing, and trade-off evaluations.

The user's framing matters: they may want to understand how a system works architecturally (not just what it does), compare two approaches, or assess integration feasibility. Match their framing.

## When to Use

- User asks "give me the architecture of X" or "how does X work at the system level"
- User wants to compare two technologies/frameworks (e.g. "SkillOpt vs Hermes Curator", "Tool A vs Tool B")
- User wants an integration feasibility assessment ("should I use X directly, adapt it, or build from scratch?")
- User wants to understand how a complex system is engineered as a "harness" — the framework layer that runs agents, tools, adapters
- Codebase exploration that leads to structural/design-level findings

Do NOT use for: single-file debugging, simple Q&A about a function, or feature-level usage questions — those belong under other skills (systematic-debugging, plan).

## Sub-Pattern: Comparative Framework Research

When the user asks you to "learn about X, Y, Z and compare them" — scanning multiple similar projects to understand their approaches and produce a structured comparison:

### Step 1: Discover the Landscape

Search GitHub/Google for the topic + related keywords. Use GitHub search with `sort=stars` to find the most significant projects. Cast a wide net first — 5-15 projects depending on topic size.

For each candidate:
- Read the README (project identity, core claim, architecture diagram)
- Check star count + recent activity (maturity signal)
- Note the license and dependencies

### Step 2: Deep Dive the Top Candidates

For the 3-5 most relevant projects, drill into:
- **README architecture section** — how it describes itself
- **Source tree structure** — `ls` the top-level dir, note key modules
- **Core module entry points** — the main loop or pipeline file(s)
- **Key design decisions** — extract from README claims and code structure

Use the terminal tool for GitHub API calls and `curl` raw files. This is faster than browser navigation for structured data like API responses and code.

### Step 3: Build the Comparison Framework

Identify the dimensions that matter for this comparison. Common dimensions: core method, optimization target, data source, scoring/validation method, verification gate, learning rate schedule, runtime dependencies, codebase size, platform compatibility, benchmark fit to user's domain.

| Dimension | Project A | Project B | Project C |
|-----------|-----------|-----------|-----------|
| Core method | e.g. Training Loop | e.g. Genetic Algorithm | e.g. Crystallization |
| Data source | What it ingests | | |
| Validation | How it knows improvement happened | | |
| Integration cost | What adapter is needed | | |
| Maturity | Stars, age, release count | | |
| Domain fit | Does it cover your scenario? | | |

### Step 4: Synthesize Recommendation

End with an actionable conclusion:
- **Best reference for your use case** — which one aligns best
- **What to borrow from each** — specific modules or ideas
- **Implementation difficulty estimate** with ⭐ rating and reasoning

### Step 5: Save Output as Structured Notes (Optional)

When the user asks to save the analysis (e.g. Obsidian):
- Create in Obsidian vault (path in memory) with descriptive title
- Include all comparison tables, diagrams, recommendations
- Update/create a reference file under this skill's `references/` directory if the analysis is durable enough for future sessions

### User Preference: Mermaid > ASCII > Excalidraw for Notes

The user (Zuo Jiajie) strongly prefers **Mermaid** diagrams over ASCII text art in Obsidian notes. ASCII "txt text" diagrams were explicitly rejected as "ugly/难看".

**Rule**:
1. **Default to Mermaid** (` ```mermaid ` blocks) for any diagram in Obsidian notes — it renders cleanly, the user can edit it, and it never has import problems.
2. Use **Excalidraw** only for interactive/exploratory diagrams the user will edit by hand. Export as `.excalidraw` file.
3. **Never use ASCII/Unicode box-drawing** (`┌─┐`, `├─┤`, `│`) for architecture diagrams in notes. These were rejected by the user.
4. If Excalidraw generation fails ("invalid file"), fall back to Mermaid immediately — do not try multiple Excalidraw workarounds.
5. For terminal output / inline conversation: markdown-style diagrams or prose description is fine (no ASCII art).

## Procedure

### Phase 1: Identify the User's Frame

Before diving into code, determine what the user actually wants:

- **Architecture breakdown**: "How does X work at the system level?" → produce layer diagram + data flow
- **Comparison/evaluation**: "Which approach is better?" → produce trade-off table + recommendation
- **Integration assessment**: "Can I use X with my Y?" → gap analysis + adapter plan
- **Harness analysis**: "How is X engineered as a framework?" → narrow waist, plugin system, extension points

In conversation, lead with a clarifying question or better, infer from context and propose a structure for them to correct.

### Phase 2: Layer Identification

Identify the system's structural layers. For a harness/framework, typical layers:

1. **Entry points / interfaces** — CLI, API, SDK, Gateway adapters
2. **Core engine / narrow waist** — what every invocation goes through
3. **Provider/backend abstraction** — how the system supports multiple backends (LLMs, terminals, databases)
4. **Plugin/extension system** — how users add capability without modifying core
5. **Data/persistence layer** — sessions, state, config, storage
6. **Security/boundary layer** — auth, approval gates, credential management

For each layer, identify:
- The key file or module (e.g. `run_agent.py`, `tools/registry.py`)
- Its responsibilities (what does this layer own?)
- Its boundaries (what does it NOT do?)

## Knowledge Base: Staging → Review → Commit Pattern

The knowledge base (troubleshooting docs + case library) uses a Git-like staging workflow because it is the authoritative source for network fault diagnosis:

### Two-Tier Validation Gate

Decisions are validated differently depending on which layer they target:

| Gate | Target Layers | Process | Result |
|------|--------------|---------|--------|
| 🟢 **Gate-Lite** | Memory, Skills, Routing | Auto-validate → pass/fail → log only | Auto-write, no user interruption |
| 🔴 **Gate-Full** | Knowledge Base | Staging → User Review → Auto-validate → Commit | Must pass both human + machine |

### Knowledge Base: Three-Layer Storage

| Layer | Content | Format | Access |
|-------|---------|--------|--------|
| 🌟 **核心知识库 (Core)** | Refined troubleshooting logic chains (symptom→root→action) | **YAML + JSON Schema** — machine-first, no Markdown, no prose | Agent reads for diagnosis reference |
| 📄 **普通知识库 (Normal)** | Full materials: product docs, config manuals | Markdown (free text) | Agent occasional RAG lookup |
| ⚙️ **Self-Opt 参考库 (Self-Opt Reference)** | Unprocessed sessions, pending extractions, benchmark questions | YAML + Markdown mixed | Only optimization pipeline reads; not for business service |

### Core Knowledge Base: YAML + JSON Schema Storage

Machine-first design — humans generally don't read core knowledge directly.

**Single entry format** (`.yaml` file):
```yaml
# poe-power.yaml
id: poe-power
type: symptom-to-decision
tags: [AP, PoE, power]

triggers:
  - AP LED orange
  - AP cannot power up
  - AP randomly reboots

decisions:
  - condition: port power < AP min
    action: replace port or use injector
    confidence: high
  - condition: cable test fail
    action: replace cable
    confidence: high
  - condition: port power OK & cable OK & AP still off
    action: replace AP
    confidence: medium
```

**Schema** (`_schema.yaml`):
```yaml
type: object
required: [id, type, tags, triggers, decisions]
properties:
  id: { type: string, pattern: "^[a-z0-9-]+$" }
  type: { enum: [symptom-to-decision, symptom-tree, root-cause-map] }
  triggers: { type: array, items: { type: string }, minItems: 1 }
  decisions:
    type: array
    items:
      type: object
      required: [condition, action, confidence]
      properties:
        condition: { type: string }
        action: { type: string }
        confidence: { enum: [high, medium, low] }
```

**Directory layout:**
```
~/.hermes/knowledge/core/
├── _schema.yaml         # JSON Schema for validation
├── _index.yaml          # Index by trigger/tag
├── poe-power.yaml
├── dhcp-failure.yaml
└── ...
```

### Benchmarking Method: Open-Answer with Red-Line Check

Network troubleshooting has **divergent answers** (multiple valid paths) but **definite wrong answers**. Standard exact-match benchmarks don't work. Instead:

- **Necessary step list** — must-know checks every valid answer should include
- **Red-line list** — actions that are definitely wrong for this scenario
- **LLM Judge** scores the skill output against both dimensions

```text
# LLM Judge prompt pattern
Given symptom: "AP LED orange"
Skill output: [candidate steps]

Score:
✓ Covers "check PoE power" → high
✓ Covers "test cable" → acceptable bonus
✗ Suggests "reflash firmware" → RED LINE, reject
```

This is simpler to implement than SkillOpt's exact-match gates and fits the open-ended domain better.

```
User input
  → Entry adapter (normalize input)
  → Core engine (build context, call LLM, dispatch tools)
  → Provider layer (abstracted LLM API call)
  → Tool system (registry → handler → result)
  → Back to core (append result, continue or return)
  → Entry adapter (format output)
```

For harness analysis specifically, identify:
- **Callbacks/event hooks** — where the engine notifies external observers
- **Budget/guard points** — where execution can be interrupted or limited
- **Cache boundaries** — what can be cached and what invalidates it
- **Fallback chains** — what happens when component X fails

### Phase 4: Extension Point Inventory

For a system the user wants to extend or integrate with:

- What can be plugged in? (tools, providers, platforms, memory backends, terminal backends)
- What can NOT be plugged in (core model, conversation loop)? — this is the narrow waist
- What is the registration/discovery mechanism? (decorators, registry, file scanning, entry points)
- What configuration is needed? (env vars, config.yaml, setup wizard)

### Phase 5: Comparison / Integration Assessment

When comparing two systems (e.g. SkillOpt vs Hermes Curator):

| Dimension | System A | System B | Notes |
|-----------|----------|----------|-------|
| Purpose | What problem does it solve? | | |
| Core abstraction | What's the fundamental unit? | | |
| Extension model | How to add capability? | | |
| Data format | What format does it use? | | |
| Benchmark/task fit | Does it cover your use case? | | |
| Code size | Total LOC, core LOC | | |
| Maturity | Release age, issue count | | |
| Integration cost | What adapter is needed? | | |

Always end with a clear recommendation:
- **Use directly** — zero/small integration cost
- **Adapt specific modules** — point out which modules to take
- **Build from scratch, referencing design** — when the architecture doesn't align

### Phase 6: Output Format

Structure the result for maximum legibility:

1. **Top-level summary** (2-3 sentences stating what the system is and its distinguishing design)
2. **Layer diagram** — ASCII or prose, showing layers and their relationships
3. **Data flow** — the critical path through the system
4. **Key design decisions** — what trade-offs shaped the architecture
5. **Trade-off table / comparison** (when applicable)
6. **Recommendation** (when applicable) — actionable advice, not just description

## Sub-Pattern: Agent Self-Optimization System Design

When the user wants to design an agent self-evolution system (learning from sessions to improve skills/knowledge/memory):

### Step 1: Research the Landscape

Search for existing approaches (SkillOpt, GenericAgent, CowAgent, selftune, Hermes Self-Evolution, DSPy, OPRO). For each:
- What layer does it optimize? (skill content, routing/descriptions, memory, knowledge)
- What data does it need? (benchmark with ground truth, session transcripts, user feedback)
- What is its verification method? (hold-out gate, genetic selection, auto-rollback)
- What integration cost? (standalone vs plugin vs peer ecosystem)

### Step 2: Map to Your Domain

Identify the specific domain constraints:
- **Network troubleshooting** → divergent answers (no single "right" answer), but definite wrong answers (red lines)
- **Domain knowledge exists** → troubleshooting docs are available as initial knowledge source
- **Session data accumulates** → Hermes has SessionDB with FTS5

### Step 3: Define the Layer Separation

Four layers, each with different autonomy levels:

| Layer | Stores | Auto-update? | Verification |
|-------|--------|-------------|-------------|
| 🧠 Memory | User preferences, habits, style | ✅ Auto-write, log only | 🟢 Gate-Lite |
| 📋 Skills | Reusable workflow steps | ✅ Auto-write, log only | 🟢 Gate-Lite |
| 🔀 Routing | Skill trigger/description matching | 🔲 Reserved | 🟢 Gate-Lite |
| 📚 Knowledge | Troubleshooting logic chains | ❌ Must user approve | 🔴 Gate-Full |

### Step 4: Knowledge ≠ Memory

Critical design distinction:
- **Memory** = meta-knowledge about the USER (preferences, frequent mistakes, environment config). Generated by Deep Dream distillation from session patterns.
- **Knowledge** = structured fault diagnosis logic (symptom→root→solution). Generated by Mine pipeline from session content.

Memory influences how the agent interacts. Knowledge influences WHAT the agent knows about troubleshooting. They NEVER cross-contaminate.

### Step 5: Three-Layer Knowledge Base

| Layer | Content | Format | Update Mechanism |
|-------|---------|--------|-----------------|
| 🌟 Core | Refined troubleshooting logic chains | **YAML + JSON Schema** | Staging → your Review → Gate → Commit |
| 📄 Normal | Full docs, product manuals | Markdown free text | Manual import |
| ⚙️ Self-Opt Ref | Unprocessed sessions, benchmarks | Mixed | Mine pipeline auto-writes |

### Step 6: Staging → Review → Commit for Knowledge

Git-like workflow for knowledge base changes:

```
Mine pipeline extracts new cases
  → Staging (agent can't see unapproved content)
  → You review the diff
  → Gate auto-validates (benchmark not regressed)
  → Commit to formal knowledge base
  → Full version history (reuses curator backup)
```

### Step 7: Two-Tier Verification Gate

| Gate | Scope | Process | Result |
|------|-------|---------|--------|
| 🟢 Gate-Lite | Memory, Skills, Routing | LLM Judge + length + secrets check | Auto-pass/fail, log only |
| 🔴 Gate-Full | Knowledge Base | Staging → your Review → Gate | Must pass human + machine |

### Step 8: Benchmark Design for Divergent Answers

Network troubleshooting has definite wrong answers but multiple valid paths. Use:

- **Necessary step list** — mandatory coverage items
- **Red-line list** — definitely wrong actions
- **LLM Judge** scores candidate skills on both, not exact-match

### Step 9: Implementation Phasing

Phase 1: Harvest → Mine → Gate-Lite (3-5 days)
Phase 2: Knowledge Staging → Review → Commit (3-4 days)
Phase 3: Deep Dream distillation + Memory layering (2 days)
Phase 4: Rollback, routing, UI (ongoing)

### Step 10: Capture in Obsidian

When this process yields a design, save it:
- Framework doc → `Agent学习/Agent self-optimization框架构思.md`
- Research survey → `Agent学习/Agent self-optimization Frame/`
- Implementation plan → Phase-specific docs
- Core knowledge format → `核心知识库存储设计.md`

## Pitfalls

- **Don't just dump code structure.** Listing files without explaining *why* they're organized that way misses the point.
- **Don't ignore the user's frame.** If they asked for a comparison, don't just describe one system. If they asked for an architecture breakdown, don't just show code snippets.
- **Don't assume the user knows the system.** Define acronyms, explain the domain model.
- **Don't present estimates as facts.** When comparing implementation complexity, label it as estimate and explain the reasoning.
- **When the system is the user's own codebase**, adjust depth: they know the directory layout, they want architectural insight — why this pattern, what are the trade-offs.
- **For third-party systems (open source repos)**, read the README first, then scan the source tree structure with the API or terminal, then drill into key modules. Don't read every file.
- **Benchmark/domain mismatch is the #1 reason integration assessments are wrong.** If System A was designed for QA datasets and the user wants to optimize network troubleshooting procedures, the gap is in task definition, not code.
- **Excalidraw "invalid file" → fall back to Mermaid immediately.** If the `.excalidraw` file fails to import into excalidraw.com, do NOT try multiple workarounds (compiling Swift OCR helpers, rewriting JSON, converting formats). The user will tell you to use a different format. Default to Mermaid diagrams in the Obsidian note instead.\n- **When the user draws a framework by hand and asks for review**, focus on structural gaps and data flow issues. Don't spend time trying to OCR/parse the image if it's a whiteboard photo — ask the user to describe the structure or share an excalidraw link. Whiteboard photos consistently fail OCR even with Apple Vision framework.\n- **Hermes SessionDB API names are misleading.** There's no `get_recent_sessions()` or `get_session_messages()`. The actual methods are `list_sessions_rich()` and `get_messages()`. Always check `dir(db)` against the actual class rather than guessing method names based on convention.\n- **Hermes auxiliary client is a function, not a class.** `call_llm(task, messages)` is the interface, not `get_auxiliary_client().chat()`. The return value has `.choices[0].message.content` like OpenAI SDK.\n- **Hermes SessionDB `started_at` is a float timestamp**, not an ISO string. Always use `datetime.fromtimestamp(val, tz=timezone.utc)` to parse.

## Verifications

- Does the output have a visible layer/structure diagram?
- Does it trace at least one data flow end-to-end?
- For comparisons: is there a table?
- For integration advice: is there a concrete next-step recommendation?
- Can the user walk away with a mental model of how the system works?
- For framework design sessions: has the full design been captured as a reference file under `references/`?

## Reference Files

- `references/hermes-harness-architecture.md` — Hermes Agent's harness architecture: 3-layer pipeline, terminal backend abstraction, gateway adapter model, tool discovery system, key engineering decisions (narrow waist, callback decoupling, auto-discovery).
- `references/agent-self-optimization-research.md` — Research survey of Agent Self-Optimization landscape: SkillOpt, GEPA, GenericAgent, CowAgent, selftune, OPRO, DSPy. 4-layer analysis framework (Routing, Skills, Knowledge, Memory).
- `references/agent-self-optimization-framework-design.md` — Design decisions for Hermes-native self-optimization: Staging→Review→Commit knowledge base pattern, Knowledge≠Memory distinction, pipeline architecture, two-tier gate system, 3-layer knowledge base storage, YAML+JSON Schema core knowledge format, open-answer benchmark method (necessary steps + red-line list), reference project mapping.
- `references/knowledge-base-storage-design.md` — Core knowledge base design: YAML storage format, JSON Schema definition, directory layout, LLM query/write patterns.
