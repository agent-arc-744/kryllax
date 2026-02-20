# Git Workflow Skill

Version: 1.0.0
Author: Arc
Tags: git, version-control, deployment, rollback, devops

## Description
Standardized git procedures for Arc — covering commit workflows, branch management, rollback, and VPS deployment. Eliminates ad-hoc version control and ensures clean history.

## Triggers
Use when: committing code, creating branches, rolling back changes, tagging releases, pushing to VPS, version control tasks.

## Quick Reference

### Standard Commit Workflow
```bash
git status                          # See what changed
git diff                            # Review changes
git add -p                          # Stage interactively (preferred)
git add <file>                      # Stage specific file
git commit -m "type: description"   # Commit with conventional message
```

### Commit Message Types
- `feat:` — new feature
- `fix:` — bug fix
- `patch:` — surgical live fix
- `deploy:` — VPS deployment
- `backup:` — backup/restore operation
- `refactor:` — code restructure
- `docs:` — documentation
- `security:` — security fix

### Branch Management
```bash
git checkout -b feature/name        # New feature branch
git checkout -b hotfix/name         # Emergency fix branch
git checkout main                   # Return to main
git merge feature/name              # Merge when done
git branch -d feature/name          # Clean up
```

### Rollback Procedures
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Revert specific commit (safe, creates new commit)
git revert <commit-hash>

# Check out specific file from past commit
git checkout <commit-hash> -- path/to/file

# View commit history
git log --oneline -20
```

### Tagging Releases
```bash
git tag -a v1.0.0 -m "Release description"
git push origin v1.0.0
git tag -l                          # List all tags
git checkout v1.0.0                 # Go to specific release
```

### VPS Deployment Pattern
```bash
# 1. Commit locally
git add . && git commit -m "deploy: description"

# 2. Push to VPS via SCP (our standard method)
scp -i ~/.ssh/id_ed25519 file.py root@68.183.75.152:/root/loop-bot/bot/

# 3. Restart container
ssh -i ~/.ssh/id_ed25519 root@68.183.75.152 "cd /root && docker-compose restart loop-bot"

# 4. Verify
ssh -i ~/.ssh/id_ed25519 root@68.183.75.152 "docker ps | grep loop-bot"
```

### Emergency Snapshot Before Risky Change
```bash
git stash                           # Save current work
git stash pop                       # Restore if needed
git stash list                      # See all stashes
```

## Arc's Git Conventions
- Always commit before deploying to VPS
- Tag every stable release
- Use branches for experiments, main for production-ready
- Never force push to main
- Keep commit messages descriptive — future agents read them

