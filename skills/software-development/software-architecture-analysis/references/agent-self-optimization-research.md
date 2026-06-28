# Agent Self-Optimization — Research Survey Pattern

A structured approach for surveying the Agent Self-Optimization landscape: comparing projects that automatically improve agent skills, memory, knowledge, and routing.

## Context

The user (Zuo Jiajie, Network Ops) is doing research on Agent Self-Optimization frameworks, anchored to the Hermes Agent ecosystem. The deliverable is a structured research document saved to Obsidian vault (`Agent学习/` directory).

## Projects to Survey

### Tier 1 — Core References

| Project | Focus | Method | Stars |
|---------|-------|--------|-------|
| **SkillOpt** (Microsoft) | Skill content optimization | Training Loop + Validation Gate | 9.4k |
| **Hermes Self-Evolution** (Nous) | Skill/DSPy optimization | GEPA genetic algorithm | 4.3k |
| **GenericAgent** (lsdefine) | Skill generation from scratch | Crystallization from execution paths | 13.1k |
| **CowAgent** (zhayujie) | Integrated self-evolution | Deep Dream distillation + holistic evolution | 45.6k |
| **selftune** | Skill routing layer optimization | Observability-driven + auto-rollback | ~100 |

### Tier 2 — Foundational

| Project | Focus | Method |
|---------|-------|--------|
| **OPRO** (Google DeepMind) | Prompt optimization | LLM as Optimizer |
| **DSPy** (Stanford) | Programmatic prompt compilation | Compilation framework |

## The 4-Layer Analysis Framework

Analyze every project against these layers of agent "self":

| Layer | What it covers | Key Questions |
|-------|---------------|---------------|
| **Routing** | Skill descriptions, trigger conditions, intent matching | Does it optimize when a skill gets invoked? |
| **Skills** | SKILL.md content, procedures, SOPs | Does it improve existing skills or create new ones? |
| **Knowledge** | Troubleshooting docs, configuration manuals, case studies | Does it structure unstructured knowledge? |
| **Memory** | User preferences, cross-session context, patterns | Does it distill session data into durable memory? |

## Research Deliverable Structure

The output document has this structure:

1. **Background & Problem Definition** — What is Agent Self-Optimization, why now
2. **Related Work** — Surveyed projects, grouped by layer
3. **Comparison Analysis** — Coverage table, maturity, key gaps
4. **Research Gaps** — What's missing (unified benchmark, session utilization, open-scenario gates)
5. **Research Positioning** — Your proposed design decisions
6. **Pipeline Design** — Nightly pipeline (Harvest → Mine → Edit → Gate → Stage → Dream → Report)
7. **References**

## Key Insights from Prior Survey

- **CowAgent Deep Dream** is the best reference for session→pattern→skill distillation. Three-layer memory (context→daily→core) with LLM-driven compression.
- **selftune** is the only project with auto-rollback. Every other project lacks regression safety.
- **SkillOpt** has the most rigorous validation (hold-out gate) but depends on standard-answer benchmarks.
- **GenericAgent** solves "discovery" not "optimization" — how to find new skill-worthy tasks from raw sessions.
- **No project covers all 4 layers simultaneously.** CowAgent comes closest (3/4).
- **The user's troubleshooting documents can serve dual purpose:** knowledge source (RAG) and benchmark dataset (necessary steps + red-line list for LLM Judge).
- **No existing project has a Staging→Review→Commit workflow for knowledge bases.** This is a unique design contribution.
- **No existing project separates Knowledge from Memory at the architectural level.** Most conflate the two.

## Framework Design Decisions (June 2026)

The user's framework design established several architectural decisions:

| Decision | Current projects | This framework |
|----------|----------------|----------------|
| Coverage | 1-3 layers max | All 4 (Routing/Skills/Knowledge/Memory) |
| Knowledge KB update | Direct write | Staging → Review → Commit (Git-like) |
| Knowledge ≠ Memory | Conflated | Separate data flows, separate validation |
| Gate system | Single gate (or none) | Two-tier (Lite auto/Full manual) |
| Knowledge storage | Markdown / free text | YAML + JSON Schema (machine-first) |
| Benchmark scoring | Exact match accuracy | LLM Judge + necessary steps + red-line list |
| Knowledge layers | One flat storage | Three-layer (Core/Normal/Self-Opt Reference) |

## Pitfalls

- **Don't skip the "why now" context.** Agents accumulating session data + LLM-as-optimizer capability + agent framework maturity are the three converging trends.
- **Don't confuse generation with optimization.** SkillOpt doesn't generate new skills; GenericAgent doesn't optimize existing ones.
- **Benchmark mismatch is the #1 trap.** SkillOpt's SearchQA/GSM8K benchmarks are irrelevant to network troubleshooting. The user's domain expertise (troubleshooting docs) is the actual asset — and no existing project uses domain-specific docs as a knowledge source.
- **When writing to Obsidian**, use the path in memory: `~/Library/Mobile Documents/com~apple~CloudDocs/笔记/Obsidian Vault/Agent学习/`.
- **Diagrams**: For architecture diagrams, generate `.excalidraw` files. For the 4-layer comparison table, markdown is sufficient.
