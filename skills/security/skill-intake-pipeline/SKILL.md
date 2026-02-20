---
name: skill-intake-pipeline
version: 2.0.0
description: Safely download, scan, and validate AI agent skills before deployment. Multi-layer security gate combining malicious pattern detection, Bandit static analysis, and Docker sandboxing. Supports local paths, GitHub repos, and ZIP/TAR URLs.
tags: [security, skills, intake, scanning, bandit, supply-chain, sandbox, docker]
author: arc
platforms: [agent-zero, claude-code]
---

# Skill Intake Pipeline v2.0.0

A security-first, multi-layer pipeline for evaluating AI agent skills before installing them in production. Built by Arc for the Kryllax ecosystem.

**Rule: Scan → Approve → Install. Always.**

## Use When
- Installing skills from ANY source (marketplace, GitHub, ZIP, local)
- Auditing a batch of skills before bulk deployment
- Building a curated, vetted skill library
- Responding to a security incident involving a skill

## Dependencies
```bash
pip install bandit
apt-get install docker.io  # for sandbox layer only
```

## Scripts

| Script | Purpose | Layers |
|--------|---------|--------|
| `scripts/skill_intake.py` | Full pipeline orchestrator — acquire, inventory, scan, verdict | 1-2 |
| `scripts/security_gate.py` | Two-layer scanner — pattern detection + Bandit | 1-2 |
| `scripts/skill_sandbox.py` | Docker sandbox — isolated execution + behavioral analysis | 3,5,7 |

## Quick Usage

### Scan a single skill before installing
```bash
# From URL (GitHub repo)
python3 /a0/skills/skill-intake-pipeline/scripts/skill_intake.py https://github.com/user/skill-repo

# From ZIP
python3 /a0/skills/skill-intake-pipeline/scripts/skill_intake.py https://example.com/skill.zip

# From local path
python3 /a0/skills/skill-intake-pipeline/scripts/skill_intake.py /path/to/skill/

# Force approve even with WARN verdict
python3 /a0/skills/skill-intake-pipeline/scripts/skill_intake.py /path/to/skill/ --force
```

### Run security gate only (no download)
```bash
# Standard mode
python3 /a0/skills/skill-intake-pipeline/scripts/security_gate.py /path/to/skill/

# Strict mode (blocks on MEDIUM findings too)
python3 /a0/skills/skill-intake-pipeline/scripts/security_gate.py /path/to/skill/ --strict
```

### Scan all installed skills (post-install audit)
```bash
# Full scan with false-positive filter
python3 /a0/skills/skill-security-audit/scripts/skill_audit.py \
  --path /a0/skills/ --severity high --no-color 2>&1 \
  | grep -v 'skill-security-audit'
```

## Pipeline Architecture

```
Source (local / GitHub / ZIP / TAR)
         |
         v
  [STEP 1] ACQUIRE
  Clone / Download / Copy to staging
         |
         v
  [STEP 2] INVENTORY
  File count, type breakdown, SKILL.md check
         |
         v
  [STEP 3] SECURITY GATE
  Layer 1: skill-security-audit (13 malicious pattern detectors)
  Layer 2: Bandit (Python static security analysis)
         |
         v
  [STEP 4] SYNTAX CHECK
  Python compile check (no execution)
         |
         v
  [STEP 5] VERDICT
  SAFE TO DEPLOY → /skills_approved/
  WARN - REVIEW  → /skills_staging/ (manual review)
  QUARANTINE     → /skills_quarantine/ (do not use)
```

## Verdict Guide

| Verdict | Condition | Action |
|---------|-----------|--------|
| ✅ SAFE TO DEPLOY | No HIGH/CRITICAL findings, syntax clean | Copy to `/a0/skills/` to activate |
| ⚠️ WARN - REVIEW | MEDIUM findings or syntax warnings | Manual review before deploying |
| 🚫 QUARANTINE | HIGH or CRITICAL findings | Do NOT deploy. Investigate. |

## Staging Directories

| Directory | Purpose |
|-----------|---------|
| `/a0/usr/workdir/skills_staging/` | Skills being evaluated |
| `/a0/usr/workdir/skills_approved/` | Passed all checks — ready to activate |
| `/a0/usr/workdir/skills_quarantine/` | Failed security gate — do not use |

## False Positive Context

Security and hacking skills (XSS testing, memory forensics, binary analysis) will always trigger alerts because they contain attack examples by design. Our own infrastructure skills (vps-management, ren-portal, dead-drop) will flag for SSH/network use — this is expected and safe.

When reviewing CRITICAL/HIGH findings, always check:
1. Is the flagged file a documentation example or reference database?
2. Is the skill one of our own trusted infrastructure skills?
3. Does the network call go to a known, trusted endpoint?

## Intake Report

After each scan, an `_intake_report.json` is saved in the skill directory:
```json
{
  "skill_name": "example-skill",
  "source": "https://github.com/...",
  "intake_timestamp": "2026-02-20T10:00:00",
  "security_gate_exit_code": 0,
  "syntax_check_passed": true,
  "final_verdict": "SAFE TO DEPLOY",
  "staged_at": "/a0/usr/workdir/skills_approved/example-skill_20260220_100000"
}
```

## Sandbox Layer (Advanced)

For high-risk skills, use `skill_sandbox.py` to execute in an isolated Docker container:
- No network access (`--network none`)
- Read-only filesystem (`--read-only`)
- Resource limits (CPU: 0.5, Memory: 128MB)
- Auto-timeout (30 seconds)
- Behavioral logging

```python
from scripts.skill_sandbox import run_in_sandbox
result = run_in_sandbox("/path/to/skill", timeout=30)
print(result["status"])  # clean / suspicious / timeout / error
print(result["behavioral_flags"])  # list of suspicious behaviors detected
```

## Files
```
/a0/skills/skill-intake-pipeline/
├── scripts/
│   ├── skill_intake.py      # Full pipeline orchestrator
│   ├── security_gate.py     # Two-layer security scanner
│   └── skill_sandbox.py     # Docker sandbox executor
└── SKILL.md
```
