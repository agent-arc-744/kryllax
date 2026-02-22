#!/bin/bash
# Check OpenRouter credit balance before expensive portal calls
KEY=$(ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'grep OPENROUTER_API_KEY /root/loop-bot/.env | cut -d= -f2' 2>/dev/null)
if [ -z "$KEY" ]; then
    echo "[WARN] Could not retrieve API key from VPS"
    exit 1
fi
curl -s https://openrouter.ai/api/v1/auth/key -H "Authorization: Bearer $KEY" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f"Credits: ${d.get('data',{}).get('limit_remaining','unknown')}")
print(f"Usage today: check dashboard at openrouter.ai")
"
