---
name: remote-exec
version: 1.0.0
author: Arc
tags: [infrastructure, ssh, remote, deployment, vps, patching]
description: Execute complex scripts and patch files on remote hosts via SSH without heredoc escaping issues. Solves nested-quote and unicode mangling in SSH heredocs by using a write-SCP-run pattern.
---

# Remote Exec — SSH Without Heredoc Pain

The `remote-exec` skill eliminates the #1 cause of SSH deployment failures:
nested quotes, unicode characters, and special characters being mangled by
the shell before Python ever sees them.

## The Problem It Solves

This **breaks** when code has nested quotes or unicode:
```bash
# FRAGILE - shell mangles quotes and unicode
ssh user@host python3 << 'EOF'
with open("file.py") as f:
    content = f.read().replace('old', 'new')
EOF
```

This **always works**:
```bash
# ROBUST - file transfer bypasses shell entirely
python3 scripts/remote_exec.py --host 68.183.75.152 --script my_patch.py
```

## Triggers

Use this skill when:
- Running complex Python scripts on a remote VPS via SSH
- Patching/replacing strings in remote files
- Deploying code changes to Docker containers
- Any SSH command that involves nested quotes or unicode
- `heredoc`, `SSH script`, `remote patch`, `VPS deploy`, `string replacement on remote`

---

## Pattern 1: Remote Script Execution

Run any Python script on a remote host without escaping issues.

```bash
python3 /a0/skills/remote-exec/scripts/remote_exec.py \
  --host 68.183.75.152 \
  --user root \
  --script /path/to/local_script.py
```

Or pass script content directly from Python:
```python
from scripts.remote_exec import run_remote_script

result = run_remote_script(
    host="68.183.75.152",
    user="root",
    script_content=open("my_script.py").read()
)
print(result.stdout)
```

## Pattern 2: Remote File Patching

Apply string replacements to remote files using a JSON patch definition.
No escaping. No heredocs. Clean every time.

```bash
python3 /a0/skills/remote-exec/scripts/remote_patch.py \
  --host 68.183.75.152 \
  --user root \
  --patches patches.json
```

**patches.json format:**
```json
[
  {
    "file": "/root/loop-bot/bot/commands.py",
    "find": "old code block here",
    "replace": "new code block here",
    "backup": true
  }
]
```

---

## Workflow (Agent Zero)

1. Write your script/patches to a local file in `/a0/usr/workdir/`
2. Call `remote_exec.py` or `remote_patch.py` with the host details
3. Review output — no escaping required
4. Temp files are auto-cleaned on both local and remote

## Key Facts

- **SSH Key**: `/root/.ssh/id_ed25519` (default)
- **Default VPS**: `68.183.75.152` (DigitalOcean)
- **Temp dir (local)**: `/tmp/arc_remote_*/`
- **Temp dir (remote)**: `/tmp/arc_remote_*/`
- **Cleanup**: Automatic on success and failure
- **Python version**: `python3` (remote)

## Why This Works

The shell only sees `scp file user@host:/tmp/` and `ssh user@host python3 /tmp/file.py`.
Your actual code — with all its quotes, unicode, and special characters — travels
as a **binary file transfer**, never touching the shell parser.
