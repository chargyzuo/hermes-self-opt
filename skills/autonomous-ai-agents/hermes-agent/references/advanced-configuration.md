# Advanced Hermes Configuration Patterns

> This was formerly the standalone `hermes-configuration` skill, now consolidated as a reference under the `hermes-agent` umbrella. Covers provider fallbacks, MCP server creation, and backup/migration.

## Provider Fallback Configuration

When your primary provider hits rate limits or quota exhaustion:

```yaml
model:
  default: qwen3.7-plus
  provider: alibaba
  fallback_providers:
    - provider: alibaba-coding-plan
      model: qwen3.7-plus
```

**Key pattern**: Same API key, different endpoint. Hermes automatically tries fallbacks on 401/403/429/5xx and switches back when primary recovers.

**Config gotcha**: Use `hermes config set` with JSON, then manually edit YAML to ensure it's a list (not a string).

## Installing External Tools as Skills

1. Extract core rules from the tool's `AGENTS.md` or README
2. Create a Hermes skill with YAML frontmatter
3. Adapt instructions to Hermes skill format
4. Place in `~/.hermes/skills/<name>/SKILL.md`

## MCP Server Configuration

### Directory Convention
All MCP server scripts live under `~/mcp/<server-name>/` — one directory per server.

### Registering MCP Servers
**Always use `hermes mcp add`, never `hermes config set` for args** — the latter stores args as a YAML string or dict, not a list:

```bash
# ✓ CORRECT
echo 'Y' | hermes mcp add switch --command python3 --args /path/to/server.py

# ✗ WRONG — stored as string or dict, validation fails
hermes config set mcp_servers.switch.args '["/path/to/server.py"]'
```

### Creating Custom MCP Servers (FastMCP Pattern)
Minimal skeleton:
```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("server-name")

@mcp.tool()
def my_tool(param: Annotated[str, "Description"]) -> str:
    return "result"

if __name__ == "__main__":
    mcp.run()
```

Key patterns: monkey-patch defaults, handle interactive input, use descriptive tool names.

Full example: see `references/mcp-server-creation.md`.

## Skill Optimization Approaches
- **Manual:** conversation-driven evolution — patch skills during sessions
- **Automated (SkillOpt):** Microsoft's research tool treating skills as trainable parameters. SkillOpt-Sleep (June 2026) reviews past sessions overnight.

## Backup & Migration
Full-machine migration of Hermes Agent to a new computer. See `references/hermes-backup-migration.md`.

## Pitfalls
- `hermes config set` with JSON may store as strings instead of YAML lists
- Fallback only activates on specific HTTP codes (401/403/429/5xx), not timeouts
- Skills from external tools won't auto-update when upstream changes
