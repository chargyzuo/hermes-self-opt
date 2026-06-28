# Ponytail adaptation notes

## What ponytail is (and isn't)

Ponytail (github.com/DietrichGebert/ponytail) is a **ruleset / prompt engineering skill** for coding agents (Claude Code, Codex, Copilot CLI, Cursor, Cline, OpenCode, Gemini CLI, etc.). It is NOT:

- A Hermes plugin (no `hermes plugins install` integration)
- A Hermes hub skill (not published to the skills hub)
- A standalone tool or library

## How it was adapted for Hermes

The core logic is a single ruleset (`AGENTS.md` in the ponytail repo). It was packaged as a local Hermes skill at `~/.hermes/skills/ponytail/SKILL.md` with the 6-rung decision ladder and safety guards preserved.

## Checking for upstream updates

Run: `python3 ~/.hermes/scripts/check-skill-updates.py`

This script scans all local skills for `metadata.source` GitHub URLs and compares against the latest remote commit SHA. It creates `.upstream_sha` tracking files in each skill directory on first run.

For hub skills, use: `hermes skills check` / `hermes skills update`

## Other non-Hermes projects

The same pattern applies: if a GitHub project provides a ruleset, prompt guide, or behavioral skill for coding agents but has no Hermes integration, package it as a local skill in `~/.hermes/skills/<name>/SKILL.md`. Include `metadata.source` pointing to the original repo for update tracking.
