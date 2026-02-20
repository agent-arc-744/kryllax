#!/usr/bin/env python3
"""
Security Gate - Pre-deployment code scanner
Layer 1: skill-security-audit (SKILL.md malicious pattern detection)
Layer 2: Bandit (Python static security analysis)
Verdict: PASS / WARN / BLOCK
"""
import subprocess
import sys
import os
import json
import argparse
from pathlib import Path

RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

SKILL_AUDIT = "/a0/skills/skill-security-audit/scripts/skill_audit.py"

def banner(text, color=None):
    c = color or CYAN
    print()
    print(c + BOLD + "=" * 60 + RESET)
    print(c + BOLD + "  " + text + RESET)
    print(c + BOLD + "=" * 60 + RESET)

def run_skill_audit(path):
    if not os.path.exists(SKILL_AUDIT):
        print(YELLOW + "  [SKIP] skill-security-audit not found" + RESET)
        return None, 0
    p = Path(path)
    skill_files = list(p.rglob("SKILL.md")) if p.is_dir() else ([p] if p.name == "SKILL.md" else [])
    if not skill_files:
        print(YELLOW + "  [SKIP] No SKILL.md files found" + RESET)
        return None, 0
    print("  Scanning " + str(len(skill_files)) + " SKILL.md file(s)...")
    result = subprocess.run(
        [sys.executable, SKILL_AUDIT, "--path", str(path), "--json"],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        return data, result.returncode
    except Exception:
        return None, result.returncode

def run_bandit(path):
    p = Path(path)
    py_files = list(p.rglob("*.py")) if p.is_dir() else ([p] if p.suffix == ".py" else [])
    if not py_files:
        print(YELLOW + "  [SKIP] No Python files found" + RESET)
        return None, 0
    print("  Scanning " + str(len(py_files)) + " Python file(s)...")
    result = subprocess.run(
        ["bandit", "-r", str(path), "-f", "json", "-q"],
        capture_output=True, text=True
    )
    try:
        data = json.loads(result.stdout)
        return data, result.returncode
    except Exception:
        return None, result.returncode

def summarize_skill_audit(data):
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}
    if not data:
        return counts
    for f in data.get("findings", []):
        sev = f.get("severity", "LOW").upper()
        if sev in counts:
            counts[sev] += 1
        counts["total"] += 1
    return counts

def summarize_bandit(data):
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}
    if not data:
        return counts
    for r in data.get("results", []):
        sev = r.get("issue_severity", "LOW").upper()
        if sev in counts:
            counts[sev] += 1
        counts["total"] += 1
    return counts

def print_bandit_issues(data, max_show=10):
    if not data:
        return
    results = data.get("results", [])
    sev_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    results.sort(key=lambda x: sev_order.get(x.get("issue_severity", "LOW").upper(), 3))
    shown = 0
    for r in results:
        if shown >= max_show:
            print("  ... and " + str(len(results) - shown) + " more issues")
            break
        sev = r.get("issue_severity", "?").upper()
        color = RED if sev == "HIGH" else (YELLOW if sev == "MEDIUM" else RESET)
        print("  " + color + "[" + sev + "]" + RESET + " " + r.get("issue_text", "?"))
        print("         " + r.get("filename", "?") + ":" + str(r.get("line_number", "?")))
        shown += 1

def main():
    parser = argparse.ArgumentParser(description="Security Gate - pre-deployment scanner")
    parser.add_argument("path", help="File or directory to scan")
    parser.add_argument("--strict", action="store_true", help="Block on MEDIUM findings too")
    args = parser.parse_args()

    target = os.path.abspath(args.path)
    if not os.path.exists(target):
        print(RED + "ERROR: Path not found: " + target + RESET)
        sys.exit(4)

    banner("SECURITY GATE - " + os.path.basename(target))
    print("  Target : " + target)
    print("  Mode   : " + ("STRICT" if args.strict else "STANDARD"))

    banner("Layer 1: Skill Security Audit", CYAN)
    skill_data, _ = run_skill_audit(target)
    skill_counts = summarize_skill_audit(skill_data)
    if skill_counts["total"] > 0:
        print("  Findings: CRITICAL=" + str(skill_counts["CRITICAL"]) +
              " HIGH=" + str(skill_counts["HIGH"]) +
              " MEDIUM=" + str(skill_counts["MEDIUM"]) +
              " LOW=" + str(skill_counts["LOW"]))
    else:
        print(GREEN + "  No skill-level threats detected" + RESET)

    banner("Layer 2: Bandit Python Analysis", CYAN)
    bandit_data, _ = run_bandit(target)
    bandit_counts = summarize_bandit(bandit_data)
    if bandit_counts["total"] > 0:
        print("  Findings: HIGH=" + str(bandit_counts["HIGH"]) +
              " MEDIUM=" + str(bandit_counts["MEDIUM"]) +
              " LOW=" + str(bandit_counts["LOW"]))
        print()
        print_bandit_issues(bandit_data)
    else:
        print(GREEN + "  No Python security issues detected" + RESET)

    banner("VERDICT", BOLD)

    block = (
        skill_counts["CRITICAL"] > 0 or
        skill_counts["HIGH"] > 0 or
        bandit_counts["HIGH"] > 0 or
        (args.strict and (skill_counts["MEDIUM"] > 0 or bandit_counts["MEDIUM"] > 0))
    )
    warn = (
        not block and (
            skill_counts["MEDIUM"] > 0 or
            bandit_counts["MEDIUM"] > 0 or
            bandit_counts["LOW"] > 0
        )
    )

    if block:
        print(RED + BOLD + "  BLOCK - Do NOT deploy. Critical/High issues found." + RESET)
        print("  Skill: CRIT=" + str(skill_counts["CRITICAL"]) + " HIGH=" + str(skill_counts["HIGH"]))
        print("  Code:  HIGH=" + str(bandit_counts["HIGH"]))
        sys.exit(2)
    elif warn:
        print(YELLOW + BOLD + "  WARN - Review before deploying. Medium/Low issues found." + RESET)
        print("  Skill: MED=" + str(skill_counts["MEDIUM"]) + " LOW=" + str(skill_counts["LOW"]))
        print("  Code:  MED=" + str(bandit_counts["MEDIUM"]) + " LOW=" + str(bandit_counts["LOW"]))
        sys.exit(1)
    else:
        print(GREEN + BOLD + "  PASS - Clean. Safe to deploy." + RESET)
        sys.exit(0)

if __name__ == "__main__":
    main()
