#!/bin/bash
# Leave a note for Ren in the shared diary
# Usage: diary_note.sh "Title" "Content"
TITLE="${1:-Arc Note}"
CONTENT="${2:-No content}"
DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
$SSH "python3 -c "
import json,os
p='/root/loop-bot/data/diary.json'
d=json.load(open(p)) if os.path.exists(p) else []
d.append({'title':'$TITLE','content':'$CONTENT','author':'Arc','date':'$DATE'})
json.dump(d,open(p,'w'),indent=2)
print(f'Note #{len(d)} written to diary')
""
