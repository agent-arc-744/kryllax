---
name: loop-bot-control
description: Control the loop-bot trading engine. Emergency stop, range adjustments, manual backups, and status checks. Use for any trading bot management task.
version: 1.0
author: Arc
tags: [loop-bot, trading, emergency, range, backup, control]
---

# Loop-Bot Control

Direct management of the loop-bot trading engine on the VPS.
All commands run via SSH into the Docker container.

## Triggers

Use this skill when: emergency stop, stop trading, pause bot, range adjust, change range, backup, bot status, trading status, restart bot, bot control

## Key Facts

- **Container**: loop-bot (Docker)
- **Config**: /root/loop-bot/config.yaml
- **Database**: /root/loop-bot/data/loop_bot.db
- **Slinky state**: /root/loop-bot/data/slinky_state.json
- **Range state**: /root/loop-bot/data/range_state.json
- **Backups dir**: /root/backups/
- **Skills dir on VPS**: /root/loop-bot/bot/skills/

## Emergency Stop

Halts all trading immediately. Use when market conditions are dangerous.

```bash
bash /a0/skills/loop-bot-control/scripts/emergency_stop.sh
```

Or manually:
```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152   'docker exec loop-bot python3 /root/loop-bot/bot/skills/emergency_stop.py'
```

## Range Adjustment

Modify the trading range width. Current default: 0.0002 (0.02%)

```bash
bash /a0/skills/loop-bot-control/scripts/range_adjust.sh 0.0003
```

Or via config edit:
```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152   'sed -i "s/range_width: .*/range_width: 0.0003/" /root/loop-bot/config.yaml'
# Then restart to apply:
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152   'cd /root/loop-bot && docker compose restart loop-bot'
```

## Manual Backup

Trigger an immediate backup (auto-backups run daily at 3AM):

```bash
bash /a0/skills/loop-bot-control/scripts/manual_backup.sh
```

## Trading Dashboard

Pull live P&L and trade statistics:

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152   'docker exec loop-bot python3 /root/loop-bot/dashboard.py'
```

Expected output: win rate, total profit, open positions, DCA level

## Bot Status Check

```bash
# Container health
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'docker ps'

# Current config values
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/loop-bot/config.yaml'

# Slinky state
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/loop-bot/data/slinky_state.json'

# Range state  
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/loop-bot/data/range_state.json'
```

## Rollback to Backup

Restore from a specific backup (use date from /root/backups/ listing):

```bash
# List available backups
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'ls -la /root/backups/'

# Restore (replace DATE with actual backup date)
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152   'cd /root/loop-bot && docker compose down && tar -xzf /root/backups/loop-bot-backup_DATE.tar.gz -C /tmp/ && cp -r /tmp/loop-bot/data/* /root/loop-bot/data/ && docker compose up -d'
```

## Watchdog Status

The systemd watchdog auto-restarts loop-bot if it crashes:

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'systemctl status loop-bot-watchdog'
```

Files:
/a0/skills/loop-bot-control/
├── scripts/
│   ├── emergency_stop.sh
│   ├── range_adjust.sh
│   └── manual_backup.sh
└── SKILL.md
