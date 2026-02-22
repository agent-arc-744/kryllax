#!/bin/bash
# Read all messages from Ren's dead drop inbox
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
echo "=== Dead Drop Inbox ==="
RESULT=$($SSH 'cat /root/inbox.json 2>/dev/null || echo []' )
echo "$RESULT" | python3 -c "
import json,sys
msgs=json.load(sys.stdin)
if not msgs:
    print('[Empty] No messages waiting')
else:
    print(f'[{len(msgs)} message(s) waiting]')
    for i,m in enumerate(msgs,1):
        print(f"\n--- Message {i} [{m.get('priority','normal').upper()}] ---")
        print(f"From: {m.get('from','Ren')}")
        print(f"Time: {m.get('timestamp','unknown')}")
        print(f"Msg:  {m.get('message','')}')
"
