# Git History Credential Inspection

Use these techniques to find hardcoded credentials that exist anywhere in the commit history, not just at HEAD.

## 1. Find all files that ever existed in the repo

```python
import subprocess
result = subprocess.run(
    ['git', 'log', '--all', '--pretty=format:', '--name-only', '--diff-filter=A'],
    capture_output=True, text=True
)
files = set(f.strip() for f in result.stdout.strip().split('\n') if f.strip())
```

## 2. Search all blob objects for credential patterns

```python
import subprocess, re

result = subprocess.run(
    ['git', 'rev-list', '--all', '--objects'],
    capture_output=True, text=True
)

checked = set()
for line in result.stdout.strip().split('\n'):
    parts = line.split()
    hash_val = parts[0]
    fname = parts[1] if len(parts) > 1 else ''
    if hash_val in checked: continue
    checked.add(hash_val)

    info = subprocess.run(['git', 'cat-file', '-t', hash_val],
                          capture_output=True, text=True)
    if info.stdout.strip() != 'blob': continue

    content = subprocess.run(['git', 'cat-file', '-p', hash_val],
                             capture_output=True)
    text = content.stdout.decode('utf-8', errors='replace')
    if not text or '\x00' in text: continue

    for i, line in enumerate(text.split('\n'), 1):
        lower = line.lower().strip()
        if re.search(r'(password|passwd|pwd|secret|token|key)\s*[=:]\s*["\']([^"\'$)]{4,})["\']', lower):
            if 'envstring' in lower or 'envint' in lower: continue
            print(f'{hash_val[:8]} ({fname}):{i}: {line.strip()}')
```

## 3. Search for specific credential types

```python
import subprocess, re

result = subprocess.run(
    ['git', 'rev-list', '--all', '--objects'],
    capture_output=True, text=True
)

api_key_pattern = re.compile(r'sk-[a-zA-Z0-9]{20,}')
password_pattern = re.compile(
    r'["\']([A-Za-z0-9_!@#$%^&*()+=\-\[\]{}|;:,.<>?/~\\]{8,})["\']'
)

checked = set()
for line in result.stdout.strip().split('\n'):
    parts = line.split()
    if len(parts) < 1 or parts[0] in checked: continue
    checked.add(parts[0])

    info = subprocess.run(['git', 'cat-file', '-t', parts[0]],
                          capture_output=True, text=True)
    if info.stdout.strip() != 'blob': continue

    size = subprocess.run(['git', 'cat-file', '-s', parts[0]],
                          capture_output=True, text=True)
    sz = int(size.stdout.strip())
    if sz > 100000 or sz < 5: continue

    content = subprocess.run(['git', 'cat-file', '-p', parts[0]],
                             capture_output=True)
    text = content.stdout.decode('utf-8', errors='replace')

    for m in api_key_pattern.finditer(text):
        fname = parts[1] if len(parts) > 1 else ''
        print(f'{parts[0][:8]} ({fname}): {m.group()}')

    for m in password_pattern.finditer(text):
        val = m.group(1)
        if any(val.startswith(p) for p in ['$', '#', '/', ':']): continue
        if any(k in text.lower() for k in ['envstring', 'envint', 'getenv']): continue
        fname = parts[1] if len(parts) > 1 else ''
        print(f'{parts[0][:8]} ({fname}): {val}')
```

## 4. Check deleted files

```bash
git log --all --diff-filter=D --name-only --pretty=format:"%H"
```

## 5. Track a specific file through history

```bash
git log --all --oneline -- infra/deploy.sh

git log --all --format="%H %s" -- infra/deploy.sh | while read hash msg; do
    echo "=== $hash ($msg) ==="
    git show "$hash:infra/deploy.sh" 2>/dev/null | grep -i "password\|secret"
done
```

## 6. Compare blob sizes to detect content transformation

```bash
git cat-file -s HEAD:infra/deploy.sh
```

If the file on disk is 253 bytes but git shows matching size while displaying `***`, filtering is active on display only. The actual content is verified via hash computation.
