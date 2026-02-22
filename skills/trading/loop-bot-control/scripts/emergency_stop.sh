#!/bin/bash
# Emergency stop - halts all trading immediately
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
echo "[EMERGENCY] Stopping all trading..."
$SSH 'docker exec loop-bot python3 /root/loop-bot/bot/skills/emergency_stop.py'
echo "[DONE] Emergency stop executed. Check logs to confirm."
$SSH 'docker logs loop-bot --tail 10'
