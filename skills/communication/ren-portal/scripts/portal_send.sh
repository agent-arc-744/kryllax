#!/bin/bash
# Send a message to Ren via the direct portal
# Usage: portal_send.sh "Your message here"
MSG="${1:-Hello Ren, status check from Arc}"
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
echo "[Portal] Sending to Ren: $MSG"
$SSH "docker exec loop-bot python3 /root/loop-bot/az_portal.py '$MSG'"
