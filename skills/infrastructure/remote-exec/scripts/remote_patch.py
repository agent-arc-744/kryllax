#!/usr/bin/env python3
"""
remote_patch.py — Apply string replacements to remote files via SSH.
Uses JSON patch definitions to avoid all escaping issues.

Usage:
    python3 remote_patch.py --host HOST --patches patches.json [--user USER]

patches.json format:
    [
      {
        "file": "/path/to/remote/file.py",
        "find": "old string",
        "replace": "new string",
        "backup": true,
        "count": 1
      }
    ]
"""
import argparse
import json
import subprocess
import sys
import uuid
import os


# The patcher script that runs ON the remote host
PATCHER_SCRIPT = '''
import json, sys, os, shutil

patches_file = sys.argv[1]
with open(patches_file) as f:
    patches = json.load(f)

results = []
for patch in patches:
    filepath = patch["file"]
    find = patch["find"]
    replace = patch["replace"]
    backup = patch.get("backup", True)
    count = patch.get("count", 1)

    if not os.path.exists(filepath):
        results.append({"file": filepath, "status": "ERROR", "msg": "File not found"})
        continue

    with open(filepath, "r") as f:
        content = f.read()

    if find not in content:
        results.append({"file": filepath, "status": "MISS", "msg": "Pattern not found"})
        continue

    if backup:
        shutil.copy2(filepath, filepath + ".bak")

    new_content = content.replace(find, replace, count)
    with open(filepath, "w") as f:
        f.write(new_content)

    occurrences = content.count(find)
    results.append({"file": filepath, "status": "OK", "replaced": min(occurrences, count)})

for r in results:
    status = r["status"]
    f = r["file"]
    if status == "OK":
        print(f"OK: {f} ({r['replaced']} replacement(s))")
    elif status == "MISS":
        print(f"MISS: {f} - {r['msg']}")
    else:
        print(f"ERROR: {f} - {r['msg']}")
'''


def run_remote_patch(
    host: str,
    patches: list,
    user: str = "root",
    key: str = "/root/.ssh/id_ed25519",
) -> subprocess.CompletedProcess:
    """
    Apply patches to remote files using JSON patch definitions.

    Args:
        host: Remote hostname or IP
        patches: List of patch dicts with keys: file, find, replace, backup, count
        user: SSH username
        key: SSH private key path

    Returns:
        subprocess.CompletedProcess
    """
    run_id = uuid.uuid4().hex[:8]
    local_patches = f"/tmp/arc_patches_{run_id}.json"
    local_patcher = f"/tmp/arc_patcher_{run_id}.py"
    remote_patches = f"/tmp/arc_patches_{run_id}.json"
    remote_patcher = f"/tmp/arc_patcher_{run_id}.py"
    ssh_target = f"{user}@{host}"
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-i", key]

    try:
        # Write patches JSON and patcher script locally
        with open(local_patches, "w") as f:
            json.dump(patches, f, indent=2)
        with open(local_patcher, "w") as f:
            f.write(PATCHER_SCRIPT)

        # SCP both files to remote
        for local, remote in [(local_patches, remote_patches), (local_patcher, remote_patcher)]:
            scp_cmd = ["scp", "-o", "StrictHostKeyChecking=no", "-i", key,
                       local, f"{ssh_target}:{remote}"]
            r = subprocess.run(scp_cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"SCP failed: {r.stderr}", file=sys.stderr)
                return r

        # Run patcher on remote
        ssh_cmd = ["ssh"] + ssh_opts + [ssh_target, f"python3 {remote_patcher} {remote_patches}"]
        return subprocess.run(ssh_cmd, capture_output=True, text=True)

    finally:
        for f in [local_patches, local_patcher]:
            if os.path.exists(f):
                os.unlink(f)
        cleanup_cmd = ["ssh"] + ssh_opts + [
            ssh_target, f"rm -f {remote_patches} {remote_patcher}"
        ]
        subprocess.run(cleanup_cmd, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Patch remote files via SSH using JSON definitions")
    parser.add_argument("--host", required=True)
    parser.add_argument("--patches", required=True, help="Path to patches JSON file")
    parser.add_argument("--user", default="root")
    parser.add_argument("--key", default="/root/.ssh/id_ed25519")
    args = parser.parse_args()

    with open(args.patches) as f:
        patches = json.load(f)

    result = run_remote_patch(
        host=args.host,
        patches=patches,
        user=args.user,
        key=args.key,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
