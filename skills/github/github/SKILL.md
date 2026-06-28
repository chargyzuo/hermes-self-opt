---
name: github
description: "Complete GitHub workflow — auth, PRs, code review, issues, repo management. Covers gh CLI and git+curl fallback for every operation."
version: 1.0.0
author: Hermes Agent (consolidation)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, git, PRs, code-review, issues, repos, CI/CD, auth]
---

# GitHub Workflows

Complete GitHub workflow reference covering authentication, pull requests, code review, issue management, and repository administration. Every section shows `gh` CLI first, then `git` + `curl` fallback for environments without `gh`.

## Quick Auth Detection

Use this at the start of any GitHub workflow:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

# Extract owner/repo from git remote
REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

---

## 1. Authentication Setup

### Auto-detect what's available

```bash
git --version
gh --version 2>/dev/null || echo "gh not installed"
gh auth status 2>/dev/null || echo "gh not authenticated"
git config --global credential.helper 2>/dev/null || echo "no git credential helper"
```

**Decision tree:**
1. `gh auth status` shows authenticated → use `gh` for everything
2. `gh` installed but not authenticated → use `gh auth` method
3. `gh` not installed → use git-only method (no sudo needed)

### Git-only: HTTPS with Personal Access Token

1. User creates token at https://github.com/settings/tokens (scopes: `repo`, `workflow`, `read:org`)
2. Configure credential storage:

```bash
git config --global credential.helper store
# First operation prompts for username + token (paste token as password)
git ls-remote https://github.com/<user>/<any-repo>.git

git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```

### Git-only: SSH Key

```bash
ls -la ~/.ssh/id_*.pub 2>/dev/null || ssh-keygen -t ed25519 -C "email@example.com" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub  # Add to https://github.com/settings/keys
ssh -T git@github.com       # Verify: "Hi <username>!"
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

### gh CLI Authentication

```bash
gh auth login                  # Interactive browser login
echo "<token>" | gh auth login --with-token   # Headless
gh auth setup-git              # Set up git credentials via gh
gh auth status                 # Verify
```

### Using GitHub API without gh

```bash
export GITHUB_TOKEN="<token>"
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

Extract token from git credentials:
```bash
grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

---

## 2. Pull Request Lifecycle

### Branch and Commit

```bash
git checkout main && git pull origin main
git checkout -b feat/description    # or fix/, refactor/, docs/, ci/
# ... make changes with file tools ...
git add <files>
git commit -m "feat: short description

Longer explanation. Wrap at 72 chars."
```

**Conventional commit types:** `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

### Create PR

**gh:**
```bash
git push -u origin HEAD
gh pr create --title "feat: description" --body "## Summary\n...\n\nCloses #42"
# Options: --draft, --reviewer user1,user2, --label "enhancement", --base develop
```

**git + curl:**
```bash
BRANCH=$(git branch --show-current)
git push -u origin HEAD

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d "{\"title\": \"feat: description\", \"body\": \"...\", \"head\": \"$BRANCH\", \"base\": \"main\"}"
# Add "draft": true for draft PRs
```

### Monitor CI

**gh:** `gh pr checks` / `gh pr checks --watch`

**curl:**
```bash
SHA=$(git rev-parse HEAD)
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/commits/$SHA/status
# Also check check-runs at: /commits/$SHA/check-runs
```

### Auto-fix CI failures

1. `gh run list --branch $(git branch --show-current)` or curl to list runs
2. `gh run view <ID> --log-failed` or download logs zip via curl
3. Fix with `patch`/`write_file`
4. `git add . && git commit -m "fix: ..." && git push`
5. Re-check CI; repeat up to 3 attempts

### Merge

**gh:**
```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch   # auto-merge when checks pass
```

**curl:**
```bash
PR_NUMBER=<number>
curl -s -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/merge \
  -d "{\"merge_method\": \"squash\"}"
git push origin --delete $BRANCH
git checkout main && git pull origin main && git branch -d $BRANCH
```

### Complete workflow example

```bash
git checkout main && git pull origin main
git checkout -b fix/login-redirect
# ... make changes ...
git add src/auth.py tests/test_login.py
git commit -m "fix: correct redirect URL after login"
git push -u origin HEAD
# Create PR, monitor CI, merge when green
```

---

## 3. Code Review

### Review local changes (pre-push)

```bash
git diff --staged                  # What would be committed
git diff main...HEAD --stat        # Scope summary
git diff main...HEAD               # Full diff
git diff main...HEAD --name-only   # Just filenames
```

**Quick scans:**
```bash
# Debug statements, TODOs left behind
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|debugger"
# Secrets or credential patterns
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*=\|private_key"
# Merge conflict markers
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="
```

### Review output format

```
## Code Review Summary

### Critical
- **src/auth.py:45** — SQL injection: user input passed directly to query.

### Warnings
- **src/models/user.py:23** — Password stored in plaintext.

### Suggestions
- **src/utils/helpers.py:8** — Duplicates logic in src/core/utils.py:34.

### Looks Good
- Clean separation of concerns, good test coverage
```

### Review a GitHub PR

**Check out locally:**
```bash
git fetch origin pull/123/head:pr-123 && git checkout pr-123
# Full access to read_file, search_files, run tests
```

**gh:** `gh pr view 123`, `gh pr diff 123`, `gh pr checkout 123`

**curl:**
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123/files
```

### Submit review

**gh:** `gh pr review 123 --approve|--request-changes|--comment --body "..."`

**curl — atomic review with inline comments:**
```bash
HEAD_SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews \
  -d "{\"commit_id\": \"$HEAD_SHA\", \"event\": \"REQUEST_CHANGES\",
    \"body\": \"## Review Summary\n...\",
    \"comments\": [
      {\"path\": \"src/auth.py\", \"line\": 45, \"body\": \"Use parameterized queries.\"}
    ]}"
```

### Review checklist

- **Correctness:** Edge cases, error handling
- **Security:** No hardcoded secrets, input validation, no SQL injection/XSS
- **Code Quality:** Clear naming, DRY, focused functions
- **Testing:** Happy path + edge cases covered
- **Performance:** No N+1 queries, appropriate caching
- **Documentation:** Public APIs documented, non-obvious logic commented

---

## 4. Issues Management

### View/List

**gh:** `gh issue list`, `gh issue list --label "bug" --assignee @me`, `gh issue view 42`

**curl:**
```bash
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20"
# Filter by label: &labels=bug
# Search: GET /search/issues?q=term+repo:$OWNER/$REPO
```

### Create

**gh:**
```bash
gh issue create --title "Title" --body "## Description\n..." \
  --label "bug,backend" --assignee "username"
```

**curl:**
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d '{"title": "Title", "body": "...", "labels": ["bug"], "assignees": ["user"]}'
```

### Triage

1. List untriaged: `gh issue list --label "needs-triage"`
2. Read and categorize each issue
3. Add labels: `gh issue edit 42 --add-label "priority:high,bug"`
4. Assign: `gh issue edit 42 --add-assignee username`
5. Comment: `gh issue comment 42 --body "Investigated — root cause is..."`

### State management

**gh:** `gh issue close 42`, `gh issue close 42 --reason "not planned"`, `gh issue reopen 42`

**curl:**
```bash
# Close: PATCH /repos/$OWNER/$REPO/issues/42 -d '{"state":"closed","state_reason":"completed"}'
# Reopen: PATCH ... -d '{"state":"open"}'
```

### Linking to PRs

Use `Closes #42`, `Fixes #42`, or `Resolves #42` in the PR body — auto-closes on merge.

---

## 5. Repository Management

### Clone

```bash
git clone https://github.com/owner/repo.git
git clone --depth 1 https://github.com/owner/repo.git      # Shallow
gh repo clone owner/repo                                     # gh shortcut
```

### Create

**gh:** `gh repo create my-project --public --clone`

**curl:**
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/user/repos \
  -d '{"name": "my-project", "private": false, "auto_init": true}'
# Under org: POST /orgs/<org>/repos
```

### Fork

**gh:** `gh repo fork owner/repo --clone`

**curl + git:**
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/owner/repo/forks
sleep 3 && git clone https://github.com/$GH_USER/repo.git
cd repo && git remote add upstream https://github.com/owner/repo.git
```

**Keep fork in sync:** `git fetch upstream && git checkout main && git merge upstream/main && git push origin main`

### Releases

**gh:**
```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release list
```

**curl:**
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/releases \
  -d '{"tag_name": "v1.0.0", "name": "v1.0.0", "generate_release_notes": true}'
```

### Secrets (GitHub Actions)

**gh:** `gh secret set API_KEY --body "value"`, `gh secret list`, `gh secret delete API_KEY`

**curl:** Requires encryption with repo's public key — prefer `gh secret set` if possible.

### Branch protection

```bash
curl -s -X PUT -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/branches/main/protection \
  -d '{"required_status_checks": {"strict": true, "contexts": ["ci/test"]},
       "required_pull_request_reviews": {"required_approving_review_count": 1}}'
```

---

## Quick Reference

| Action | gh | git + curl endpoint |
|--------|-----|---------------------|
| Clone | `gh repo clone o/r` | `git clone https://github.com/o/r.git` |
| Create repo | `gh repo create name` | `POST /user/repos` |
| Create PR | `gh pr create --title ...` | `POST /repos/o/r/pulls` |
| View PR | `gh pr view N` | `GET /repos/o/r/pulls/N` |
| PR diff | `gh pr diff N` | `git diff main...HEAD` |
| List issues | `gh issue list` | `GET /repos/o/r/issues` |
| Create issue | `gh issue create ...` | `POST /repos/o/r/issues` |
| Comment | `gh issue comment N ...` | `POST /repos/o/r/issues/N/comments` |
| Approve PR | `gh pr review N --approve` | `POST /repos/o/r/pulls/N/reviews` |
| Merge PR | `gh pr merge --squash` | `PUT /repos/o/r/pulls/N/merge` |
| CI status | `gh pr checks` | `GET /repos/o/r/commits/SHA/status` |
| Create release | `gh release create v1.0` | `POST /repos/o/r/releases` |
| Set secret | `gh secret set KEY` | `PUT /repos/o/r/actions/secrets/KEY` |

## Common Pitfalls

- **`git push` asks for password** — GitHub disabled password auth. Use a PAT as the password.
- **`remote: Permission denied`** — Token may lack `repo` scope.
- **Credentials not persisting** — Check `git config --global credential.helper` is `store` or `cache`.
- **RDAUTHDOWN/RDAUTHUP confusion** — These are switch RADIUS logs, not GitHub. Use the `huawei-switch-auth-troubleshooting` skill for switch auth.
- **GitHub API returns PRs in `/issues` endpoint** — Filter with `'pull_request' not in i` when listing issues.
- **Secrets via curl require encryption** — `gh secret set` is dramatically simpler. If `gh` isn't available, recommend installing it just for secret management.
