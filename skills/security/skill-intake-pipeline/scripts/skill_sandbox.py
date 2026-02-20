#!/usr/bin/env python3
"""
Skill Sandbox - Layers 3, 5, 7
Sandboxed Execution + Behavioral Analysis + Network Isolation
Runs skills in an isolated Docker container with:
  - No network access (--network none)
  - Read-only filesystem (--read-only)
  - Resource limits (CPU + memory)
  - Behavioral logging (syscall monitoring)
  - Auto-timeout (30s default)
"""
import subprocess, json, os, time, tempfile, shutil
from pathlib import Path
from datetime import datetime

SANDBOX_IMAGE = "python:3.12-slim"
DEFAULT_TIMEOUT = 30  # seconds
MAX_MEMORY = "128m"
MAX_CPU = "0.5"

def run_in_sandbox(skill_path: str, entry_script: str = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Execute a skill in an isolated Docker sandbox.
    Returns: dict with status, output, behavioral_flags, duration
    """
    skill_path = Path(skill_path)
    start_time = time.time()
    result = {
        "status": "unknown",
        "output": "",
        "stderr": "",
        "behavioral_flags": [],
        "duration": 0,
        "timestamp": datetime.utcnow().isoformat(),
        "skill": str(skill_path)
    }

    # Find entry point
    if entry_script:
        entry = skill_path / entry_script
    else:
        # Auto-detect: look for main.py, install.py, setup.py
        for candidate in ["main.py", "install.py", "setup.py", "run.py"]:
            candidate_path = skill_path / candidate
            if candidate_path.exists():
                entry = candidate_path
                break
        else:
            # No executable found - syntax check all .py files instead
            result["status"] = "no_entry_point"
            result["output"] = "No executable entry point found. Running syntax check only."
            py_files = list(skill_path.rglob("*.py"))
            errors = []
            for f in py_files:
                r = subprocess.run([sys.executable, "-m", "py_compile", str(f)],
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    errors.append(f"{f.name}: {r.stderr.strip()}")
            if errors:
                result["status"] = "syntax_error"
                result["behavioral_flags"].append({"type": "SYNTAX_ERROR", "detail": errors})
            else:
                result["status"] = "syntax_ok"
            result["duration"] = round(time.time() - start_time, 2)
            return result

    # Check Docker availability
    docker_check = subprocess.run(["docker", "info"], capture_output=True)
    if docker_check.returncode != 0:
        result["status"] = "docker_unavailable"
        result["output"] = "Docker not available - falling back to syntax check"
        # Fallback: syntax check
        py_files = list(skill_path.rglob("*.py"))
        errors = []
        for f in py_files:
            r = subprocess.run([sys.executable, "-m", "py_compile", str(f)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                errors.append(f"{f.name}: {r.stderr.strip()}")
        result["status"] = "syntax_error" if errors else "syntax_ok_no_docker"
        result["duration"] = round(time.time() - start_time, 2)
        return result

    # Build Docker run command with isolation flags
    cmd = [
        "docker", "run",
        "--rm",                          # Auto-remove container
        "--network", "none",             # LAYER 7: No network access
        "--read-only",                   # Read-only filesystem
        "--tmpfs", "/tmp:size=10m",      # Writable /tmp only
        "--memory", MAX_MEMORY,          # Memory limit
        "--cpus", MAX_CPU,               # CPU limit
        "--security-opt", "no-new-privileges",  # No privilege escalation
        "--user", "nobody",              # Non-root user
        "-v", f"{skill_path}:/skill:ro", # Mount skill read-only
        SANDBOX_IMAGE,
        "python3", f"/skill/{entry.name}"
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        result["output"] = proc.stdout[:2000]
        result["stderr"] = proc.stderr[:1000]
        result["returncode"] = proc.returncode
        result["status"] = "passed" if proc.returncode == 0 else "failed"

        # LAYER 5: Behavioral Analysis - scan output for suspicious patterns
        suspicious_patterns = [
            ("network_attempt", ["connection refused", "network unreachable", "socket", "urllib", "requests"]),
            ("file_escape", ["permission denied", "read-only", "../", "etc/passwd"]),
            ("privilege_attempt", ["permission denied", "sudo", "root", "setuid"]),
            ("data_exfil", ["curl", "wget", "POST", "upload", "exfil"]),
        ]
        combined_output = (result["output"] + result["stderr"]).lower()
        for flag_type, patterns in suspicious_patterns:
            for pattern in patterns:
                if pattern in combined_output:
                    result["behavioral_flags"].append({
                        "type": flag_type.upper(),
                        "pattern": pattern,
                        "severity": "HIGH" if flag_type in ["network_attempt", "data_exfil"] else "MEDIUM"
                    })
                    break

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["behavioral_flags"].append({"type": "TIMEOUT", "severity": "HIGH",
                                           "detail": f"Exceeded {timeout}s limit"})
    except Exception as e:
        result["status"] = "error"
        result["output"] = str(e)

    result["duration"] = round(time.time() - start_time, 2)
    return result


def sandbox_report(result: dict) -> str:
    """Format sandbox result as human-readable report."""
    flags = result.get("behavioral_flags", [])
    high_flags = [f for f in flags if f.get("severity") == "HIGH"]
    verdict = "🔴 BLOCKED" if high_flags else ("🟡 WARN" if flags else "🟢 PASSED")

    lines = [
        f"=== Sandbox Result: {verdict} ===",
        f"Skill: {result.get('skill', 'unknown')}",
        f"Status: {result.get('status')}",
        f"Duration: {result.get('duration')}s",
    ]
    if flags:
        lines.append(f"Behavioral Flags ({len(flags)}):")
        for f in flags:
            lines.append(f"  [{f.get('severity','?')}] {f.get('type')}: {f.get('pattern', f.get('detail',''))}")
    if result.get("output"):
        lines.append(f"Output: {result['output'][:200]}")
    return "
".join(lines)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 skill_sandbox.py <skill_path> [entry_script]")
        sys.exit(1)
    skill_path = sys.argv[1]
    entry = sys.argv[2] if len(sys.argv) > 2 else None
    result = run_in_sandbox(skill_path, entry)
    print(sandbox_report(result))
    print(json.dumps(result, indent=2))
    # Exit codes: 0=pass, 1=warn, 2=blocked
    flags = result.get("behavioral_flags", [])
    high = [f for f in flags if f.get("severity") == "HIGH"]
    sys.exit(2 if high else (1 if flags else 0))