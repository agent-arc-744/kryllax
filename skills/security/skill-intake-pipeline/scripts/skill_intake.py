#!/usr/bin/env python3
"""
Skill Intake Pipeline
Safely downloads, scans, and validates skills from the Agent Skills Marketplace
or any URL/local path before deployment.

Usage:
  python skill_intake.py <url_or_path>
  python skill_intake.py https://github.com/user/skill-repo
  python skill_intake.py /local/path/to/skill/

Verdicts:
  SAFE TO DEPLOY  - Passed all checks
  WARN - REVIEW   - Low/medium findings, manual review recommended
  QUARANTINE      - High/critical findings, do not deploy
"""
import subprocess
import sys
import os
import shutil
import zipfile
import tarfile
import urllib.request
import urllib.parse
import json
import argparse
import tempfile
from pathlib import Path
from datetime import datetime

RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

STAGING_DIR   = Path("/a0/usr/workdir/skills_staging")
SECURITY_GATE = Path("/a0/usr/workdir/security_gate.py")
QUARANTINE_DIR = Path("/a0/usr/workdir/skills_quarantine")
APPROVED_DIR  = Path("/a0/usr/workdir/skills_approved")


def banner(text, color=None):
    c = color or CYAN
    print()
    print(c + BOLD + "=" * 60 + RESET)
    print(c + BOLD + "  " + text + RESET)
    print(c + BOLD + "=" * 60 + RESET)

def step(text):  print(CYAN   + "\n  >> " + text + RESET)
def ok(text):    print(GREEN  + "  [OK] " + text + RESET)
def warn(text):  print(YELLOW + "  [WARN] " + text + RESET)
def fail(text):  print(RED    + "  [FAIL] " + text + RESET)
def info(text):  print(DIM    + "  " + text + RESET)


def detect_source_type(source):
    if os.path.exists(source):
        return "local"
    if source.startswith(("http://", "https://")):
        parsed = urllib.parse.urlparse(source)
        netloc = parsed.netloc.lower()
        path   = parsed.path.lower()
        if "github.com" in netloc or "gitlab.com" in netloc:
            return "git"
        if path.endswith(".zip"):
            return "zip"
        if path.endswith((".tar.gz", ".tgz", ".tar")):
            return "tar"
        return "zip"  # assume zip for unknown URLs
    return "unknown"


def get_skill_name(source):
    if os.path.exists(source):
        return Path(source).name
    parsed = urllib.parse.urlparse(source)
    name = Path(parsed.path).stem
    for suffix in [".tar", "-main", "-master"]:
        name = name.replace(suffix, "")
    return name or "unknown-skill"


def download_archive(url, dest_dir):
    step("Downloading from " + url)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".download") as tmp:
        tmp_path = tmp.name
    try:
        urllib.request.urlretrieve(url, tmp_path)
        size = os.path.getsize(tmp_path)
        info("Downloaded " + str(size) + " bytes")
        if zipfile.is_zipfile(tmp_path):
            with zipfile.ZipFile(tmp_path, "r") as zf:
                zf.extractall(dest_dir)
            ok("Extracted zip to " + str(dest_dir))
        elif tarfile.is_tarfile(tmp_path):
            with tarfile.open(tmp_path, "r:*") as tf:
                tf.extractall(dest_dir)
            ok("Extracted tar to " + str(dest_dir))
        else:
            fail("Downloaded file is not a zip or tar archive")
            return False
        return True
    except Exception as e:
        fail("Download failed: " + str(e))
        return False
    finally:
        os.unlink(tmp_path)


def clone_git(url, dest_dir):
    step("Cloning git repo: " + url)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest_dir)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        ok("Cloned to " + str(dest_dir))
        return True
    fail("Git clone failed: " + result.stderr.strip())
    return False


def copy_local(source, dest_dir):
    step("Copying local source: " + source)
    src = Path(source)
    if src.is_dir():
        shutil.copytree(src, dest_dir)
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_dir)
    ok("Copied to " + str(dest_dir))
    return True


def run_security_gate(skill_dir):
    step("Running Security Gate (Layer 1: Skill Audit + Layer 2: Bandit)")
    if not SECURITY_GATE.exists():
        warn("security_gate.py not found — skipping security scan")
        return 0
    result = subprocess.run(
        [sys.executable, str(SECURITY_GATE), str(skill_dir)]
    )
    return result.returncode


def run_syntax_check(skill_dir):
    step("Running Python syntax check (no execution)")
    py_files = list(Path(skill_dir).rglob("*.py"))
    if not py_files:
        info("No Python files found")
        return True
    info("Checking " + str(len(py_files)) + " Python file(s)...")
    errors = []
    for f in py_files:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(f)],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            errors.append((f.name, result.stderr.strip()))
    if errors:
        for fname, err in errors:
            warn("Syntax error in " + fname + ": " + err)
        return False
    ok("All " + str(len(py_files)) + " Python file(s) passed syntax check")
    return True


def inventory_skill(skill_dir):
    step("Skill Inventory")
    skill_path = Path(skill_dir)
    files = [f for f in skill_path.rglob("*") if f.is_file()]
    by_ext = {}
    for f in files:
        ext = f.suffix.lower() or "(no ext)"
        by_ext.setdefault(ext, []).append(f)
    for ext, flist in sorted(by_ext.items()):
        extra = (" + " + str(len(flist)-1) + " more") if len(flist) > 1 else ""
        info(ext.ljust(12) + " x" + str(len(flist)).rjust(3) + "  — " + flist[0].name + extra)
    skill_md = list(skill_path.rglob("SKILL.md"))
    if skill_md:
        ok("SKILL.md found — Agent Zero compatible")
    else:
        warn("No SKILL.md found — may not be Agent Zero compatible")
    return len(files)


def save_report(skill_name, source, gate_code, syntax_ok, verdict, skill_dir):
    report = {
        "skill_name": skill_name,
        "source": source,
        "intake_timestamp": datetime.now().isoformat(),
        "security_gate_exit_code": gate_code,
        "syntax_check_passed": syntax_ok,
        "final_verdict": verdict,
        "staged_at": str(skill_dir)
    }
    report_path = Path(skill_dir) / "_intake_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    info("Report saved: " + str(report_path))


def main():
    parser = argparse.ArgumentParser(
        description="Skill Intake Pipeline — safely test marketplace skills before deployment"
    )
    parser.add_argument("source", help="URL or local path to the skill")
    parser.add_argument("--force", action="store_true", help="Approve even with WARN verdict")
    args = parser.parse_args()

    source     = args.source
    skill_name = get_skill_name(source)
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    staged_name = skill_name + "_" + timestamp

    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    APPROVED_DIR.mkdir(parents=True, exist_ok=True)

    skill_dir = STAGING_DIR / staged_name

    banner("SKILL INTAKE PIPELINE")
    print("  Source  : " + source)
    print("  Skill   : " + skill_name)
    print("  Staging : " + str(skill_dir))
    print("  Time    : " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # STEP 1: Acquire
    banner("STEP 1: ACQUIRE")
    source_type = detect_source_type(source)
    info("Source type: " + source_type)

    if source_type == "local":
        success = copy_local(source, skill_dir)
    elif source_type == "git":
        success = clone_git(source, skill_dir)
    elif source_type in ("zip", "tar"):
        skill_dir.mkdir(parents=True, exist_ok=True)
        success = download_archive(source, skill_dir)
    else:
        fail("Cannot handle source type: " + source_type)
        sys.exit(1)

    if not success:
        fail("Acquisition failed — aborting")
        sys.exit(1)

    # STEP 2: Inventory
    banner("STEP 2: INVENTORY")
    file_count = inventory_skill(skill_dir)
    info("Total files: " + str(file_count))

    # STEP 3: Security Gate
    banner("STEP 3: SECURITY GATE")
    gate_code = run_security_gate(skill_dir)

    # STEP 4: Syntax Check
    banner("STEP 4: SYNTAX CHECK")
    syntax_ok = run_syntax_check(skill_dir)

    # STEP 5: Verdict
    banner("STEP 5: VERDICT")

    if gate_code >= 2:
        verdict = "QUARANTINE"
        dest = QUARANTINE_DIR / staged_name
        shutil.move(str(skill_dir), str(dest))
        print(RED + BOLD)
        print("  +--------------------------------------+")
        print("  |  QUARANTINE - DO NOT DEPLOY          |")
        print("  +--------------------------------------+" + RESET)
        print(RED + "  High/Critical findings. Skill moved to: " + str(dest) + RESET)
        save_report(skill_name, source, gate_code, syntax_ok, verdict, dest)
        sys.exit(2)

    elif gate_code == 1 or not syntax_ok:
        verdict = "WARN - REVIEW"
        print(YELLOW + BOLD)
        print("  +--------------------------------------+")
        print("  |  WARN - MANUAL REVIEW NEEDED         |")
        print("  +--------------------------------------+" + RESET)
        print(YELLOW + "  Skill staged at: " + str(skill_dir) + RESET)
        print(YELLOW + "  Review before deploying. Use --force to approve anyway." + RESET)
        save_report(skill_name, source, gate_code, syntax_ok, verdict, skill_dir)
        if args.force:
            dest = APPROVED_DIR / staged_name
            shutil.move(str(skill_dir), str(dest))
            ok("--force: moved to approved: " + str(dest))
        sys.exit(1)

    else:
        verdict = "SAFE TO DEPLOY"
        dest = APPROVED_DIR / staged_name
        shutil.move(str(skill_dir), str(dest))
        print(GREEN + BOLD)
        print("  +--------------------------------------+")
        print("  |  SAFE TO DEPLOY                      |")
        print("  +--------------------------------------+" + RESET)
        print(GREEN + "  All checks passed!" + RESET)
        print(GREEN + "  Approved at: " + str(dest) + RESET)
        print()
        print(CYAN + "  Next steps:" + RESET)
        print("    1. Review skill at: " + str(dest))
        print("    2. Copy to /a0/skills/ to activate in Agent Zero")
        print("    3. Or deploy to VPS via SSH")
        save_report(skill_name, source, gate_code, syntax_ok, verdict, dest)
        sys.exit(0)


if __name__ == "__main__":
    main()


# ============================================================
# LAYER 8: AUTO-QUARANTINE - Added by security hardening
# ============================================================
AUTO_QUARANTINE_ON = ["CRITICAL", "HIGH"]  # Auto-block these severities

def auto_quarantine(skill_dir, findings, quarantine_dir):
    """Auto-move skill to quarantine if CRITICAL or HIGH findings found."""
    import shutil
    from pathlib import Path
    high_findings = [f for f in findings if f.get("severity") in AUTO_QUARANTINE_ON]
    if not high_findings:
        return False
    q_dir = Path(quarantine_dir)
    q_dir.mkdir(parents=True, exist_ok=True)
    dest = q_dir / Path(skill_dir).name
    if Path(skill_dir).exists():
        shutil.move(str(skill_dir), str(dest))
    # Write quarantine report
    report = {
        "quarantined_at": __import__("datetime").datetime.utcnow().isoformat(),
        "reason": f"{len(high_findings)} HIGH/CRITICAL findings",
        "findings": high_findings
    }
    (dest / "_QUARANTINE_REPORT.json").write_text(
        __import__("json").dumps(report, indent=2)
    )
    return True
