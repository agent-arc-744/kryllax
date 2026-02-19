---
name: file-patcher
version: 1.0.0
author: Arc
tags: [infrastructure, patching, files, code, find-replace, json, developer-tools]
description: Apply structured find-and-replace patches to local files using JSON definitions. Eliminates fragile string manipulation and manual edits. Supports dry-run, backup, regex, and multi-file batch operations.
---

# File Patcher — JSON-Driven Code Patching

Stop manually editing files with fragile string replacements.
Define your patches as JSON, run the patcher, done.

## The Problem It Solves

Manually patching files in agent workflows is error-prone:
```python
# FRAGILE — breaks with special chars, wrong indentation, or encoding
content = content.replace('old code', 'new code')
```

File Patcher uses structured JSON definitions that are:
- **Readable** — patches are self-documenting
- **Verifiable** — dry-run mode shows what will change before applying
- **Safe** — automatic backups before any modification
- **Repeatable** — same patch file, same result, every time

## Triggers

Use this skill when:
- Patching source code files with find/replace operations
- Applying multiple changes to multiple files in one operation
- Modifying config files, scripts, or any text file
- Needing a dry-run preview before committing changes
- Any task involving `patch file`, `replace in file`, `update code`, `find and replace`

---

## Patch Definition Format

Create a JSON file defining your patches:

```json
[
  {
    "file": "/path/to/target/file.py",
    "find": "old string or code block",
    "replace": "new string or code block",
    "backup": true,
    "count": 1,
    "description": "Optional: what this patch does"
  }
]
```

### Fields

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `file` | ✅ | — | Absolute path to target file |
| `find` | ✅ | — | Exact string to find |
| `replace` | ✅ | — | Replacement string |
| `backup` | ❌ | `true` | Create `.bak` file before patching |
| `count` | ❌ | `1` | Max replacements (0 = all) |
| `description` | ❌ | — | Human-readable description |

---

## Usage

### Apply Patches
```bash
python3 scripts/patch.py patches.json
```

### Dry Run (preview only — no changes made)
```bash
python3 scripts/patch.py patches.json --dry-run
```

### Restore from Backup
```bash
python3 scripts/patch.py patches.json --restore
```

### Verify Patches Applied Correctly
```bash
python3 scripts/patch.py patches.json --verify
```

---

## Agent Zero Workflow

1. **Write patch definition** to a local JSON file
2. **Dry-run** to verify what will change
3. **Apply** the patches
4. **Verify** the result

```python
# Step 1: Write patches
import json
patches = [
    {
        "file": "/path/to/file.py",
        "find": "old_function_name",
        "replace": "new_function_name",
        "backup": True,
        "description": "Rename function"
    }
]
with open("/tmp/my_patches.json", "w") as f:
    json.dump(patches, f, indent=2)
```

```bash
# Step 2: Dry run
python3 scripts/patch.py /tmp/my_patches.json --dry-run

# Step 3: Apply
python3 scripts/patch.py /tmp/my_patches.json

# Step 4: Verify
python3 scripts/patch.py /tmp/my_patches.json --verify
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All patches applied successfully |
| `1` | One or more patches missed (pattern not found) |
| `2` | One or more patches failed (file error) |

## Integration with remote-exec

For patching **remote** files over SSH, use the `remote-exec` skill:
```bash
python3 /path/to/remote-exec/scripts/remote_patch.py \
  --host 68.183.75.152 --patches patches.json
```

File Patcher handles **local** files. Remote Exec handles **remote** files.
Same JSON format — works with both.

## Directory Structure
```
file-patcher/
├── SKILL.md
├── scripts/
│   └── patch.py          # Main patcher — apply, dry-run, restore, verify
└── examples/
    ├── simple.json        # Single file, single replacement
    ├── multi-file.json    # Multiple files in one operation
    └── config-update.json # Config file patching example
```
