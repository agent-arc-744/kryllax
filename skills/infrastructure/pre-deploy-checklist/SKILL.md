# Pre-Deploy Checklist

A mandatory verification protocol before deploying any code change to a live system. Prevents crashes, data loss, and the embarrassment of breaking production with a typo.

## Why This Exists

We crashed Ren multiple times by deploying code without checking it first. The dict.append bug, the portal import error, the systemd Restart= in the wrong section — all preventable with a 2-minute checklist.

## The Non-Negotiable Rule

> **Never deploy code you haven't read in full. Never skip the post-deploy log check.**

## The Checklist

### Phase 1: Blueprint (Before Writing Code)

- [ ] What is the exact problem being solved?
- [ ] What is the minimal change required? (Surgical, not sweeping)
- [ ] What could go wrong? (List 2-3 failure modes)
- [ ] Is there an existing skill or script that already does this?
- [ ] Read the FULL target file before touching it

### Phase 2: Write (During Coding)

- [ ] No placeholder values or demo data in the code
- [ ] No hardcoded credentials or API keys
- [ ] Variable names are descriptive, not `x`, `tmp`, `data`
- [ ] Error handling exists for the main failure modes
- [ ] Print/log statements confirm the change was applied

### Phase 3: Verify (Before Deploying)

```bash
# Syntax check
python3 -m py_compile /path/to/script.py && echo "SYNTAX OK"

# Confirm target string exists (for patches)
grep -n "TARGET_STRING" /path/to/target.py

# Check for obvious issues
python3 -c "import ast; ast.parse(open('/path/to/script.py').read()); print('AST OK')"
```

- [ ] Syntax check passes
- [ ] Target strings confirmed present
- [ ] No obvious logic errors on re-read

### Phase 4: Deploy

Follow the `safe-vps-patching` skill protocol:
1. SCP patch script to VPS
2. Execute
3. Verify change applied
4. Copy to container
5. Restart service

### Phase 5: Verify Post-Deploy (MANDATORY)

```bash
# Check service is running
ssh root@68.183.75.152 "systemctl status <service>"

# Check logs for errors
ssh root@68.183.75.152 "docker logs myloopbot --tail 30"
# OR
ssh root@68.183.75.152 "journalctl -u <service> -n 30"

# Confirm the specific fix is working
ssh root@68.183.75.152 "grep -n 'EXPECTED_OUTPUT' /var/log/..."
```

- [ ] Service shows `active (running)`
- [ ] No new errors in logs
- [ ] The specific bug is confirmed fixed
- [ ] Clean up temp files

## Rollback Plan

Before every deploy, know your rollback:

```bash
# Option A: Restore from backup
ssh root@68.183.75.152 "cp /root/target.py.bak /root/target.py"

# Option B: Git revert
git revert HEAD && git push

# Option C: Restore from VPS backup
tar -xzf /root/backups/loop-bot-backup_<date>.tar.gz
```

Always create a backup before patching:
```bash
ssh root@68.183.75.152 "cp /root/target.py /root/target.py.bak"
```

## Severity Levels

| Change Type | Risk | Extra Steps Required |
|-------------|------|---------------------|
| Config value change | Low | Log check only |
| Single function patch | Medium | Full checklist |
| New file deployment | Medium | Full checklist + integration test |
| Core bot logic change | High | Full checklist + backup + staged test |
| Database schema change | Critical | Full checklist + backup + migration script |