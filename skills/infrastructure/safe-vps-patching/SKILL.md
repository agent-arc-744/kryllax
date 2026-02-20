# Safe VPS Patching

A battle-tested protocol for applying code changes to remote VPS servers without shell escaping failures, syntax errors, or service crashes.

## Why This Exists

Every time we used SSH heredoc to patch files, it broke. Nested quotes, Python indentation, special characters — all mangled by the shell. This skill enforces the only reliable pattern: **write locally, SCP, execute, verify, delete**.

## The Golden Rule

> **Never use SSH heredoc for multi-line code. Ever.**

## The Safe Patch Workflow

### Step 1: Write the patch script locally

Create a Python patch script in `/a0/usr/workdir/` that modifies the target file:

```python
# patch_<target>_<date>.py
import re

target = "/root/path/to/target.py"

with open(target, "r") as f:
    content = f.read()

# Make surgical changes
content = content.replace(
    "OLD_CODE_HERE",
    "NEW_CODE_HERE"
)

# Verify the change was made
if "NEW_CODE_HERE" not in content:
    raise ValueError("Patch failed - target string not found")

with open(target, "w") as f:
    f.write(content)

print("Patch applied successfully")
```

### Step 2: Syntax-check before sending

```bash
python3 -m py_compile /a0/usr/workdir/patch_script.py
echo "Syntax OK"
```

### Step 3: SCP to VPS

```bash
scp /a0/usr/workdir/patch_script.py root@68.183.75.152:/root/patch_script.py
```

### Step 4: Execute on VPS

```bash
ssh root@68.183.75.152 "python3 /root/patch_script.py"
```

### Step 5: Verify the change

```bash
ssh root@68.183.75.152 "grep -n 'NEW_CODE_HERE' /root/path/to/target.py"
```

### Step 6: Update container (if applicable)

```bash
ssh root@68.183.75.152 "docker cp /root/target.py myloopbot:/app/bot/target.py && docker restart myloopbot"
```

### Step 7: Check logs after restart

```bash
ssh root@68.183.75.152 "sleep 5 && docker logs myloopbot --tail 20"
```

### Step 8: Clean up

```bash
ssh root@68.183.75.152 "rm /root/patch_script.py"
```

## Pre-Patch Checklist

Before writing any patch:

- [ ] Read the FULL target file first — never patch blind
- [ ] Identify the exact line numbers being changed
- [ ] Confirm the old string exists: `grep -n "OLD_STRING" target.py`
- [ ] Write patch using `.replace()` or `re.sub()` — not string concatenation
- [ ] Syntax check the patch script itself
- [ ] Syntax check the patched file after applying: `python3 -m py_compile target.py`

## Common Failure Modes (and fixes)

| Failure | Cause | Fix |
|---------|-------|-----|
| `replace()` returns unchanged content | Old string not found (whitespace/indent mismatch) | Use `grep -n` to find exact string first |
| Container still shows old code | Forgot `docker cp` step | Always cp + restart |
| Service crashes after patch | Syntax error in patched file | Run `py_compile` before deploying |
| Patch applied to wrong file | Path typo | Print `target` path at start of script |

## For Simple Single-Line Changes

`sed` is acceptable for single-line replacements:

```bash
ssh root@68.183.75.152 "sed -i 's/OLD_VALUE/NEW_VALUE/g' /root/target.py"
```

But only when:
- The replacement string contains no special regex characters
- It is a single line change
- You verify with `grep` afterward

## VPS Details (Project-Specific)

- **VPS IP**: 68.183.75.152
- **Main container**: `myloopbot`
- **App path in container**: `/app/bot/`
- **Host path**: `/root/loop-bot/bot/`
- **Restart command**: `docker restart myloopbot && sleep 5 && docker logs myloopbot --tail 20`