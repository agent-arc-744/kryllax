#!/bin/bash
# Trigger immediate backup of loop-bot data
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
DATE=$(date +%Y-%m-%d_%H%M%S)
echo "[Backup] Starting manual backup at $DATE"
$SSH "cd /root/loop-bot && tar -czf /root/backups/loop-bot-manual_${DATE}.tar.gz data/ bot/ config.yaml .env"
$SSH 'ls -lh /root/backups/ | tail -5'
echo "[Done] Backup complete."
