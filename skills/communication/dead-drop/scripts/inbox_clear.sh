#!/bin/bash
# Clear the inbox after reading
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
$SSH 'echo [] > /root/inbox.json'
echo "[OK] Inbox cleared."
