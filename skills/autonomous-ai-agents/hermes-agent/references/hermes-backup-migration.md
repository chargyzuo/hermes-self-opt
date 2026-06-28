# Hermes Profile Backup & Migration

Full Hermes Agent backup for migrating to a new machine. Covers the core
profile export plus the three pieces `hermes profile export` excludes.

## What profile export covers

```bash
hermes profile export default -o backup.tar.gz
# → Includes: skills, memories, config.yaml, cron, SOUL.md, sessions, plugins, lsp, scripts, hooks
# → Excludes: state.db, .env, ~/.lark-cli/, custom scripts outside ~/.hermes/
```

## Complete backup script

Save as `~/hermes-backup.sh`:

```bash
#!/bin/bash
set -e
BACKUP_DIR="$HOME/hermes-backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. Export profile
hermes profile export default -o /tmp/hermes-core.tar.gz

# 2. Unpack
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
tar xzf /tmp/hermes-core.tar.gz -C "$BACKUP_DIR"
rm /tmp/hermes-core.tar.gz

# 3. Add state.db (excluded by profile export)
cp "$HOME/.hermes/state.db" "$BACKUP_DIR/default/state.db" 2>/dev/null || true

# 4. Add lark-cli config (Feishu auth tokens)
if [ -d "$HOME/.lark-cli" ]; then
    rm -rf "$BACKUP_DIR/lark-cli"
    cp -r "$HOME/.lark-cli" "$BACKUP_DIR/lark-cli"
fi

# 5. Add MCP servers (~/mcp/<name>/ convention)
if [ -d "$HOME/mcp" ]; then
    rm -rf "$BACKUP_DIR/mcp"
    cp -r "$HOME/mcp" "$BACKUP_DIR/mcp"
fi

# 6. Add personal scripts
mkdir -p "$BACKUP_DIR/scripts"
cp "$HOME/script/shift-schedule.json" "$BACKUP_DIR/scripts/" 2>/dev/null || true
cp "$HOME/script/fitness-plan.md" "$BACKUP_DIR/scripts/" 2>/dev/null || true
# Add more personal paths as needed

# 7. Warn about path mismatches on new machine
echo "⚠️  New machine: update mcp_servers paths in config.yaml (username differs)"
echo "Backup: $BACKUP_DIR ($(du -sh "$BACKUP_DIR" | cut -f1))"
```

## Git sync for periodic backup

```bash
cd ~/hermes-backup
git init
echo "state.db" >> .gitignore           # optional: state.db is large, bin
echo "lark-cli/hermes/cache/" >> .gitignore

# Create private GitHub repo, then:
git remote add origin git@github.com:USER/private-repo.git
git add -A && git commit -m "backup $(date +%Y-%m-%d)" && git push
```

Run the script before switching machines or periodically (manually or via launchd on macOS).

## What's NOT included (must recreate on new machine)

| Item | Why excluded | How to restore |
|------|-------------|----------------|
| `.env` | Contains API keys (plaintext secrets) | Manually copy or re-enter API keys |
| `state.db` | 22MB+ SQLite binary; may contain PII | Included in custom script above if user opts in |
| `~/.lark-cli/` | Feishu OAuth tokens (separate from Hermes) | Included in custom script above |
| npm global packages | `@larksuite/cli` is at `/opt/homebrew/lib/node_modules/` | `npm install -g @larksuite/cli` on new machine |

## Restore on new machine

```bash
# 1. Install Hermes
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# 2. Clone backup repo
git clone <private-repo-url> ~/hermes-backup

# 3. Install lark-cli
npm install -g @larksuite/cli

# 4. Restore Hermes data
# Option A: Full manual copy (recommended — includes state.db, lark-cli, mcp)
cp -r ~/hermes-backup/default/* ~/.hermes/
cp -r ~/hermes-backup/lark-cli ~/.lark-cli/
cp -r ~/hermes-backup/mcp ~/mcp/
cp -r ~/hermes-backup/scripts ~/scripts/

# Option B: profile import (does not include state.db / lark-cli / mcp)
# hermes profile import ~/hermes-backup/default/

# 5. Fix MCP paths in config (username differs on new machine)
# Edit ~/.hermes/config.yaml → update mcp_servers.switch.args[0] path

# 6. Restore .env (API keys) — do NOT commit this to git
# Manually create ~/.hermes/.env with your API keys

# 6. Verify
hermes doctor
lark-cli auth status
```
