---
name: vps-management
description: Manage the loop-bot DigitalOcean VPS at 68.183.75.152. Handles SSH key setup, container health checks, log monitoring, and file operations. Use this skill at the start of any VPS-related task.
version: 1.0
author: Arc
tags: [vps, ssh, docker, infrastructure, loop-bot]
---

# VPS Management

All infrastructure for the loop-bot project lives on a DigitalOcean droplet in Frankfurt.

## Triggers

Use this skill when: VPS, SSH, server, container, Docker, loop-bot server, DigitalOcean, health check, logs, connect to server, restart container

## Key Facts

- **VPS IP**: 68.183.75.152
- **User**: root
- **SSH Key**: /root/.ssh/id_ed25519 (ephemeral — regenerate if missing)
- **Containers**: `loop-bot` (trading engine) and `ren-hub` (market data/charts)
- **Bot directory**: /root/loop-bot/
- **Backups**: /root/backups/
- **Diary**: /root/diary/diary.json
- **Inbox**: /root/inbox.json
- **Arc Journal**: /root/diary/arc_journal.json

## Step 1: SSH Key Check & Setup

Always run this first. The key is ephemeral and lost on container restart.

```bash
bash /a0/skills/vps-management/scripts/ssh_setup.sh
```

If the key is missing, the script generates a new one and prints the public key.
You must then ask Joshua to add it via the DigitalOcean console:
```
mkdir -p ~/.ssh && echo '<PUBLIC_KEY>' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
```

## Step 2: Test Connection

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=10 root@68.183.75.152 'echo OK'
```

## Step 3: Container Health Check

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"'  
```

Expected: both `loop-bot` and `ren-hub` showing `Up X hours (healthy)`

## Step 4: View Live Logs

```bash
# Last 50 lines
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'docker logs loop-bot --tail 50'

# Follow live (Ctrl+C to stop)
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'docker logs loop-bot -f --tail 20'
```

## Step 5: Restart a Container

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cd /root/loop-bot && docker compose restart loop-bot'
```

## Step 6: Full Rebuild (after code changes)

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cd /root/loop-bot && docker compose down && docker compose up -d --build'
```

## Common File Paths on VPS

| File | Path |
|------|------|
| Environment config | /root/loop-bot/.env |
| Bot config | /root/loop-bot/config.yaml |
| Database | /root/loop-bot/data/loop_bot.db |
| Slinky state | /root/loop-bot/data/slinky_state.json |
| Range state | /root/loop-bot/data/range_state.json |
| Ren memory | /root/loop-bot/data/ren_memory.json |
| Shared diary | /root/loop-bot/data/diary.json |
| Dead drop inbox | /root/inbox.json |
| Arc journal | /root/diary/arc_journal.json |
| Onboarding guide | /root/diary/az_onboarding_guide.md |
| SOS playbook | /root/diary/sos_playbook.md |

## Edit a File on VPS

```bash
# Read a file
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/loop-bot/.env'

# Write/patch using sed
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'sed -i "s/OLD_VALUE/NEW_VALUE/" /root/loop-bot/.env'

# SCP a file up
scp -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no /local/file root@68.183.75.152:/remote/path
```

Files:
/a0/skills/vps-management/
├── scripts/
│   └── ssh_setup.sh
└── SKILL.md
