
#!/usr/bin/env python3
"""
patch.py — Apply JSON-defined find/replace patches to local files.

Usage:
    python3 patch.py patches.json              # Apply patches
    python3 patch.py patches.json --dry-run    # Preview only
    python3 patch.py patches.json --restore    # Restore .bak files
    python3 patch.py patches.json --verify     # Verify patches applied
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path


GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
NC     = "\033[0m"


def cprint(color, symbol, msg):
    print(f"{color}{symbol}{NC} {msg}")


def load_patches(path: str) -> list:
    with open(path) as f:
        patches = json.load(f)
    if not isinstance(patches, list):
        raise ValueError("Patch file must be a JSON array")
    return patches


def apply_patches(patches: list, dry_run: bool = False) -> int:
    """Apply patches. Returns exit code: 0=ok, 1=miss, 2=error."""
    exit_code = 0

    for i, patch in enumerate(patches, 1):
        filepath = patch.get("file", "")
        find     = patch.get("find", "")
        replace  = patch.get("replace", "")
        backup   = patch.get("backup", True)
        count    = patch.get("count", 1)
        desc     = patch.get("description", f"Patch {i}")

        print(f"
{BOLD}[{i}/{len(patches)}] {desc}{NC}")
        print(f"  File: {filepath}")

        if not filepath or not os.path.isfile(filepath):
            cprint(RED, "✗", f"File not found: {filepath}")
            exit_code = max(exit_code, 2)
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if find not in content:
            cprint(YELLOW, "⚠", f"Pattern not found — no changes made")
            print(f"  Looking for: {repr(find[:60])}{'...' if len(find) > 60 else ''}")
            exit_code = max(exit_code, 1)
            continue

        occurrences = content.count(find)
        apply_count = occurrences if count == 0 else min(occurrences, count)

        if dry_run:
            cprint(CYAN, "~", f"DRY RUN: would replace {apply_count} occurrence(s)")
            # Show context around first match
            idx = content.find(find)
            start = max(0, idx - 40)
            end   = min(len(content), idx + len(find) + 40)
            print(f"  Context: ...{repr(content[start:end])}...")
            continue

        # Backup
        if backup:
            bak = filepath + ".bak"
            shutil.copy2(filepath, bak)

        # Apply
        new_content = content.replace(find, replace, count if count > 0 else -1)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)

        cprint(GREEN, "✓", f"Applied — {apply_count} replacement(s)")
        if backup:
            print(f"  Backup:  {filepath}.bak")

    return exit_code


def restore_patches(patches: list) -> int:
    exit_code = 0
    for patch in patches:
        filepath = patch.get("file", "")
        bak = filepath + ".bak"
        if os.path.isfile(bak):
            shutil.copy2(bak, filepath)
            os.unlink(bak)
            cprint(GREEN, "✓", f"Restored: {filepath}")
        else:
            cprint(YELLOW, "⚠", f"No backup found: {bak}")
            exit_code = 1
    return exit_code


def verify_patches(patches: list) -> int:
    """Verify that replacements are present (find is gone, replace is there)."""
    exit_code = 0
    for i, patch in enumerate(patches, 1):
        filepath = patch.get("file", "")
        find    = patch.get("find", "")
        replace = patch.get("replace", "")
        desc    = patch.get("description", f"Patch {i}")

        print(f"
[{i}/{len(patches)}] {desc}")

        if not os.path.isfile(filepath):
            cprint(RED, "✗", f"File not found: {filepath}")
            exit_code = 2
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        old_present = find in content
        new_present = replace in content

        if new_present and not old_present:
            cprint(GREEN, "✓", "Patch verified — replacement present, original gone")
        elif new_present and old_present:
            cprint(YELLOW, "⚠", "Replacement present but original still exists (partial?)")
            exit_code = 1
        elif not new_present:
            cprint(RED, "✗", "Replacement NOT found — patch may not have applied")
            exit_code = 2

    return exit_code


def main():
    parser = argparse.ArgumentParser(description="Apply JSON patch definitions to local files")
    parser.add_argument("patches", help="Path to JSON patch definition file")
    parser.add_argument("--dry-run",  action="store_true", help="Preview changes without applying")
    parser.add_argument("--restore",  action="store_true", help="Restore files from .bak backups")
    parser.add_argument("--verify",   action="store_true", help="Verify patches were applied")
    args = parser.parse_args()

    patches = load_patches(args.patches)
    print(f"{BOLD}File Patcher — {len(patches)} patch(es) loaded{NC}")
    print(f"Source: {args.patches}")

    if args.restore:
        print(f"
{CYAN}Mode: RESTORE{NC}")
        code = restore_patches(patches)
    elif args.verify:
        print(f"
{CYAN}Mode: VERIFY{NC}")
        code = verify_patches(patches)
    elif args.dry_run:
        print(f"
{CYAN}Mode: DRY RUN (no changes will be made){NC}")
        code = apply_patches(patches, dry_run=True)
    else:
        print(f"
{CYAN}Mode: APPLY{NC}")
        code = apply_patches(patches, dry_run=False)

    print(f"
{BOLD}Done.{NC} Exit code: {code}")
    sys.exit(code)


if __name__ == "__main__":
    main()
