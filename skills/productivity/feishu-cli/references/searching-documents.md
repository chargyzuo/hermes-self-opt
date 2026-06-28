# Feishu Cross-Document Search

## Commands

### Basic keyword search

```shell
lark-cli docs +search --query "AP 部署 高密" --page-size 10
```

Returns: document titles, tokens, types, and content snippets matching the query.
Default page size is 15, max 20.

The `--query` field supports case-insensitive substring search. Multi-word queries use AND semantics.

### Filtered search by metadata

```shell
lark-cli drive +search \
  --query "Internet 区 割接" \
  --doc-types docx,wiki,sheet \
  --created-since 90d \
  --page-size 10
```

Available filters:

| Flag | Description | Example |
|------|-------------|---------|
| `--doc-types` | Filter by type (comma-separated) | `docx,wiki,sheet,doc` |
| `--created-since` | Relative or absolute time window | `30d`, `2026-01-01` |
| `--created-until` | End of time window | `2026-06-01` |
| `--edited-since` | Recently edited by me | `7d` |
| `--mine` | Only docs I created | flag only |
| `--creator-ids` | By owner open_id | `ou_xxx,ou_yyy` |
| `--folder-tokens` | Within specific folders | `fold_xxx,fold_yyy` |
| `--space-ids` | Within specific wiki spaces | `wiki_space_xxx` |

### Output formats

```shell
# JSON (default — best for programmatic use)
lark-cli docs +search --query "..." --json

# Pretty-printed table
lark-cli docs +search --query "..." --format pretty

# jq filtering
lark-cli docs +search --query "..." -q '.data.entries[].title'
```

## Scope requirement

Search uses the `search:docs:read` scope (Search v2: `doc_wiki/search` API).
This scope is **NOT** granted by default in `lark-cli auth login --recommend`.

Check if scope is present:

```shell
lark-cli auth status 2>&1 | python3 -c "
import sys,json
d=json.load(sys.stdin)
scopes = d['identities']['user']['scope']
print('search:docs:read' in scopes)
"
```

If `False`, add it:

```shell
lark-cli auth login --scope "search:docs:read"
```

This is idempotent — running it again with the same scope is a no-op. Adding a scope preserves all existing scopes.

## Pitfalls

1. **Output truncation**: Search results include only snippets, not full document content. Use `lark-cli docs +fetch --doc <token>` to read the full document after finding it.

2. **No regex in query**: The `--query` parameter is a plain keyword search, not regex. Use `|` for OR (e.g., `foo|bar`).

3. **Page size max**: Hard limit of 20 per page. Use `--page-token` for pagination through large result sets.

4. **Scope adds are per-session**: If the auth login times out before the user opens the browser URL, kill the process and retry. The device code has a ~10 minute expiry.
