#!/bin/bash
# SSH Setup Script - Run at start of any VPS session
KEY="/root/.ssh/id_ed25519"
VPS="root@68.183.75.152"

if [ -f "$KEY" ]; then
    echo "[OK] SSH key exists at $KEY"
    # Test connection
    if ssh -i "$KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=8 $VPS 'echo connected' 2>/dev/null; then
        echo "[OK] VPS connection successful"
    else
        echo "[WARN] Key exists but connection failed - key may need to be re-added to VPS"
        echo "Public key to add:"
        cat "${KEY}.pub"
    fi
else
    echo "[INFO] No SSH key found. Generating new Ed25519 key..."
    mkdir -p /root/.ssh
    ssh-keygen -t ed25519 -f "$KEY" -N "" -C "agent-zero-$(date +%Y%m%d)"
    echo ""
    echo "[ACTION REQUIRED] Add this public key to the VPS via DigitalOcean console:"
    echo "Command to run on VPS:"
    echo "mkdir -p ~/.ssh && echo '$(cat ${KEY}.pub)' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
fi
