#!/usr/bin/env bash
# deploy_kael.sh — Deploy Kael standalone bot to VPS
# Usage: bash deploy_kael.sh
# Requires: SSH access to root@68.183.75.152

set -euo pipefail

VPS="root@68.183.75.152"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[deploy_kael] Copying files to VPS..."
scp "${SCRIPT_DIR}/kael_standalone.py"          "${VPS}:/root/kael_standalone.py"
scp "${SCRIPT_DIR}/kael.service"                "${VPS}:/etc/systemd/system/kael.service"
scp "${SCRIPT_DIR}/docs/kael_profile.md"        "${VPS}:/root/kael_profile.md"

echo "[deploy_kael] Installing and starting service..."
ssh "${VPS}" bash << 'REMOTE'
    set -euo pipefail

    # Verify env file exists
    if [ ! -f /root/.kael.env ]; then
        echo "ERROR: /root/.kael.env not found. Create it first."
        echo "Required contents:"
        echo "  KAEL_TOKEN=<your-telegram-bot-token>"
        echo "  OPENROUTER_KEY=<your-openrouter-key>"
        echo "  KAEL_MODEL=anthropic/claude-3-5-haiku  # optional, this is default"
        exit 1
    fi

    # Ensure log file exists with correct perms
    touch /var/log/kael_standalone.log
    chmod 644 /var/log/kael_standalone.log

    # Reload systemd, enable and start
    systemctl daemon-reload
    systemctl enable kael.service
    systemctl restart kael.service

    sleep 2
    systemctl status kael.service --no-pager
    echo ""
    echo "[deploy_kael] Tail of log:"
    tail -20 /var/log/kael_standalone.log
REMOTE

echo ""
echo "[deploy_kael] Done. Kael is live on VPS."
