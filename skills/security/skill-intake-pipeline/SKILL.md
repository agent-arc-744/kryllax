---
name: skill-intake-pipeline
version: 1.0.0
description: Safely download, scan, and validate AI agent skills before deployment. Multi-layer security gate combining malicious pattern detection and Bandit static analysis. Supports local paths, GitHub repos, and ZIP/TAR URLs.
tags: [security, skills, intake, scanning, bandit, supply-chain]
author: arc
platforms: [agent-zero, claude-code]
---

# Skill Intake Pipeline

A security-first pipeline for evaluating AI agent skills before installing them in production.

## Use When
- Installing skills from unknown sources
- Auditing marketplace skills before deployment
- Building a curated, vetted skill library

## Dependencies
```bash
pip install bandit
```

## Workflow

```
Source (local/GitHub/URL)
    |
    v
Acquire & Extract
    |
    v
File Inventory
    |
    v
Layer 1: Malicious Pattern Scan (13 detectors)
    |
    v
Layer 2: Bandit Static Analysis
    |
    v
Verdict: PASS / WARN / BLOCK
    |
    v
Move to: approved/ or quarantine/
```

## Verdict Levels

| Verdict | Condition | Action |
|---------|-----------|--------|
| PASS | No findings | Auto-approve |
| WARN | Low/medium findings only | Manual review |
| BLOCK | High/critical findings | Auto-quarantine |

## Usage

```bash
# Scan a local skill directory
python skill_intake.py /path/to/skill

# Scan a GitHub repo
python skill_intake.py https://github.com/user/skill-repo

# Scan a ZIP file
python skill_intake.py https://example.com/skill.zip
```

## Directory Structure

```
workdir/
  skills_staging/    # downloaded, awaiting scan
  skills_approved/   # passed security gate
  skills_quarantine/ # blocked, do not use
```

## Notes
- Always run intake before installing any external skill
- WARN verdicts require human review before approval
- Quarantined skills are preserved for forensic analysis
- Combine with SHA256 signature verification for maximum security
