#!/bin/bash
# Write an entry to the shared diary on VPS
# Usage: diary_write.sh "Title" "Content"
TITLE="${1:-Arc Note}"
CONTENT="${2:-No content provided}"
DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SSH="ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152"
$SSH "python3 -c "
import json,os
path='/root/loop-bot/data/diary.json'
data=json.load(open(path)) if os.path.exists(path) else []
data.append({'title':'$TITLE','content':'$CONTENT','author':'Arc','date':'$DATE'})
json.dump(data,open(path,'w'),indent=2)
print(f'Diary entry #{len(data)} written')
""
