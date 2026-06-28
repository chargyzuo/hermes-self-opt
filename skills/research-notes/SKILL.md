---
name: research-notes
description: Create research and architecture notes for this user's Obsidian vault. Covers diagramming preferences, vault structure, and note formatting conventions.
category: productivity
---

# Research & Architecture Notes

This user maintains research and architecture documentation in an Obsidian vault on iCloud Drive. Use this skill when asked to create, update, or extend research notes, architecture diagrams, framework documentation, or development diaries.

## Vault Path

The vault is always at:

```
~/Library/Mobile Documents/com~apple~CloudDocs/笔记/Obsidian Vault/
```

Never use `~/Documents/Obsidian Vault/` — that is a common default but NOT the correct path for this user. The vault lives on iCloud Drive.

## Diagramming

**Use Mermaid for all architecture diagrams, flowcharts, and framework overviews.** Never use ASCII art or box-drawing characters (`┌─┐│`) when a Mermaid diagram can convey the same structure. Mermaid renders natively in Obsidian's preview mode and is far more legible.

When a Mermaid export fails or is impractical (e.g. Excalidraw `.excalidraw` files that won't load on excalidraw.com), describe the diagram structure in text, then offer to create a Mermaid version in the note. Prefer the Mermaid version.

## Note Structure

Research notes follow this convention:

```
Note Title (descriptive, Chinese + English mixed as appropriate)
  > One-line summary of what this note contains

## Section 1 — with Mermaid diagram if applicable
Content with tables, lists, and reference links.

## Section 2
...

## References
Numbered list of external sources, papers, repos.
```

Use `write_file` to create notes, `patch` for targeted edits. Prefer file tools over shell heredocs.

## Directory Convention

The user organizes research under subdirectories inside the vault:

```
Agent学习/
  SomeTopic/
    Note1.md
    Note2.md
```

When starting a new research topic, create a subdirectory under `Agent学习/` (or the appropriate top-level category) with a descriptive English + Chinese name. Group related notes inside that directory.

## Pitfalls

- Do NOT use `~/Documents/Obsidian Vault/` — the vault is on iCloud Drive.
- Do NOT use ASCII art for architecture diagrams — use Mermaid.
- When a diagram tool fails (e.g. Excalidraw), fall back to Mermaid in the note, not raw text.
- The user prefers Chinese + English mixed in note titles and content. Week 1 of English transition (Jun 25–Jul 2): mostly Chinese with key English terms.
- **Development diary (开发日记.md) is APPEND-ONLY.** Never use `write_file` on it — it will overwrite and destroy all historical entries. Always use `read_file` + `patch` to append at the end. Same rule applies to any file that looks like a chronological log (dated entries, diary/journal naming patterns).

## Related References

- `references/gate-lite-pattern.md` — cheap-local-checks-before-LLM optimization pattern (from Agent Self-Optimization development)
