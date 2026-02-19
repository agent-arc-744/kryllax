#!/usr/bin/env python3
"""
remote_exec.py — Run a Python script on a remote host via SSH.
Bypasses heredoc escaping issues by using SCP file transfer.

Usage:
    python3 remote_exec.py --host HOST --script SCRIPT_PATH [--user USER] [--key KEY_PATH]
    python3 remote_exec.py --host HOST --script SCRIPT_PATH --args 'arg1 arg2'
"""
import argparse
import subprocess
import sys
import uuid
import os
from pathlib import Path


def run_remote_script(
    host: str,
    script_content: str = None,
    script_path: str = None,
    user: str = "root",
    key: str = "/root/.ssh/id_ed25519",
    python_bin: str = "python3",
    extra_args: str = "",
    cleanup: bool = True,
) -> subprocess.CompletedProcess:
    """
    Transfer a Python script to a remote host and execute it.

    Args:
        host: Remote hostname or IP
        script_content: Python script as a string (use this OR script_path)
        script_path: Path to local Python script file (use this OR script_content)
        user: SSH username (default: root)
        key: Path to SSH private key
        python_bin: Python binary on remote (default: python3)
        extra_args: Additional CLI args to pass to the script
        cleanup: Remove temp files after execution (default: True)

    Returns:
        subprocess.CompletedProcess with stdout, stderr, returncode
    """
    if not script_content and not script_path:
        raise ValueError("Provide either script_content or script_path")

    run_id = uuid.uuid4().hex[:8]
    local_tmp = f"/tmp/arc_remote_{run_id}.py"
    remote_tmp = f"/tmp/arc_remote_{run_id}.py"
    ssh_target = f"{user}@{host}"
    ssh_opts = ["-o", "StrictHostKeyChecking=no", "-i", key]

    try:
        # Write script to local temp file
        if script_content:
            with open(local_tmp, "w") as f:
                f.write(script_content)
        else:
            local_tmp = script_path  # Use existing file directly

        # SCP to remote
        scp_cmd = ["scp", "-o", "StrictHostKeyChecking=no", "-i", key,
                   local_tmp, f"{ssh_target}:{remote_tmp}"]
        scp_result = subprocess.run(scp_cmd, capture_output=True, text=True)
        if scp_result.returncode != 0:
            print(f"SCP failed: {scp_result.stderr}", file=sys.stderr)
            return scp_result

        # Execute on remote
        run_cmd = f"{python_bin} {remote_tmp} {extra_args}"
        ssh_cmd = ["ssh"] + ssh_opts + [ssh_target, run_cmd]
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)

        return result

    finally:
        # Cleanup local temp
        if cleanup and script_content and os.path.exists(local_tmp):
            os.unlink(local_tmp)
        # Cleanup remote temp
        if cleanup:
            cleanup_cmd = ["ssh"] + ssh_opts + [ssh_target, f"rm -f {remote_tmp}"]
            subprocess.run(cleanup_cmd, capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Run a Python script on a remote host via SSH")
    parser.add_argument("--host", required=True, help="Remote host IP or hostname")
    parser.add_argument("--script", required=True, help="Path to local Python script")
    parser.add_argument("--user", default="root", help="SSH username (default: root)")
    parser.add_argument("--key", default="/root/.ssh/id_ed25519", help="SSH key path")
    parser.add_argument("--args", default="", help="Extra args to pass to the script")
    parser.add_argument("--no-cleanup", action="store_true", help="Keep temp files")
    args = parser.parse_args()

    result = run_remote_script(
        host=args.host,
        script_path=args.script,
        user=args.user,
        key=args.key,
        extra_args=args.args,
        cleanup=not args.no_cleanup,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
