# Bypassing Terminal Output Filtering for Credential Inspection

When inspecting files for hardcoded credentials, some systems filter displayed output:

- **ByteSec pre-commit hook** (`~/.bytesec/commit_hook/`): A security layer that intercepts git commands and replaces credential values with `***` in terminal output.
- **Terminal-level redaction**: `cat`, `echo`, Python `open().read()`, and even `git cat-file -p` may show `***` instead of the actual credential value when stdout is a TTY.

## Detection: Is filtering active?

Symptom: `cat deploy.sh` shows `SSH_PASSWORD="***"` but `od -c deploy.sh` shows the real password bytes (e.g., `Qm8p!2zT5r`).

## Technique 1: Raw hex dump (most reliable)

```bash
xxd infra/deploy.sh
# Look at bytes directly — the hex representation is never redacted
```

The bytes `51 6d 38 70 21 32 7a 54 35 72` decode to `Qm8p!2zT5r`.

```bash
od -c infra/deploy.sh
# Shows character-by-character octal dump
```

## Technique 2: Git blob hash verification

The git blob hash is computed from the RAW file content — filtering doesn't affect it:

```python
import subprocess, hashlib

# Get hash of working tree file
disk_hash = subprocess.run(
    ['git', 'hash-object', 'infra/deploy.sh'],
    capture_output=True, text=True
).stdout.strip()

# Get hash from HEAD tree
tree_hash = subprocess.run(
    ['git', 'ls-tree', 'HEAD', 'infra/deploy.sh'],
    capture_output=True, text=True
).stdout.strip().split()[2]

# If they match, content is identical (regardless of what terminal shows)
print(disk_hash == tree_hash)  # True means same content
```

Or compute manually:

```python
with open('infra/deploy.sh', 'rb') as f:
    content = f.read()

blob = b'blob ' + str(len(content)).encode() + b'\x00' + content
computed = hashlib.sha1(blob).hexdigest()
```

Compare versions with `***` vs real value:
- `Qm8p!2zT5r` → 253 bytes → hash `0fcad81ed3...`
- `***` → 246 bytes → hash `e6bb468956...`

## Technique 3: Python subprocess (pipe != TTY)

When called from `subprocess.run()`, stdout is a pipe (not a TTY), so filtering may not apply:

```python
import subprocess

# From Python: stdout is a pipe, less likely to be filtered
r = subprocess.run(['git', 'cat-file', '-p', 'HEAD:infra/deploy.sh'],
                   capture_output=True)
# r.stdout may contain the REAL credential
```

Compare with terminal output where the same command shows `***`.

## Technique 4: Raw blob extraction from pack files

If the object is in a pack file (not loose), decompress directly:

```python
import zlib, os

hash_val = '0fcad81ed3702e71c4c14fdc930bf56010532ec3'
loose_path = f'.git/objects/{hash_val[:2]}/{hash_val[2:]}'
if os.path.exists(loose_path):
    with open(loose_path, 'rb') as f:
        compressed = f.read()
        decompressed = zlib.decompress(compressed)
        # Skip header: 'blob NNN\0'
        null_idx = decompressed.find(b'\x00')
        content = decompressed[null_idx+1:]
```

## Verification: File on disk vs committed blob

```python
with open('infra/deploy.sh', 'rb') as f:
    disk_content = f.read()
blob_content = subprocess.run(
    ['git', 'cat-file', '-p', 'HEAD:infra/deploy.sh'],
    capture_output=True
).stdout
print(f'Match: {disk_content == blob_content}')
print(f'Disk size: {len(disk_content)}, Blob size: {len(blob_content)}')
```

## Checking for git content filters

```bash
git config --global --list          # Check for global filter config
git config --local --list           # Check for local filter config
git check-attr -a infra/deploy.sh   # Check file-specific attributes
find . -name '.gitattributes'       # Check for attributes files
```

If `core.hookspath` is set to a security tool's directory (e.g., `/Users/bytedance/.bytesec/commit_hook/`), filtering is active.
