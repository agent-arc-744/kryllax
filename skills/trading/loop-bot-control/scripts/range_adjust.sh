#!/bin/bash
# Adjust trading range width
# Usage: range_adjust.sh 0.0003
NEW_RANGE="${1:-0.0002}"
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
echo "[Range] Adjusting range_width to $NEW_RANGE"
$SSH "docker exec loop-bot python3 /root/loop-bot/bot/skills/range_adjust.py $NEW_RANGE"
echo "[Done] Range adjusted. Restarting bot to apply..."
$SSH 'cd /root/loop-bot && docker compose restart loop-bot'
