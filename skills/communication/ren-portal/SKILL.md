---
name: ren-portal
description: Open a direct communication portal with Ren, the trading AI on the VPS. Bypasses Telegram for real-time collaboration. Use for strategy discussions, status checks, and coordination.
version: 1.0
author: Arc
tags: [ren, portal, communication, trading, collaboration]
---

# Ren Portal

The portal is a direct Python bridge to Ren inside the loop-bot Docker container.
It shares her memory and diary but maintains a separate conversation history from Telegram.

## Triggers

Use this skill when: talk to Ren, portal, message Ren, ask Ren, contact Ren, Ren says, check with Ren, coordinate with Ren

## Key Facts

- **Portal script**: /root/loop-bot/az_portal.py (on VPS)
- **Ren model**: anthropic/claude-sonnet-4 via OpenRouter
- **Ren memory**: /root/loop-bot/data/ren_memory.json
- **Shared diary**: /root/loop-bot/data/diary.json
- **Dead drop inbox**: /root/inbox.json
- **Cost**: ~$0.01-0.03 per portal exchange (Sonnet 4 pricing)

## Step 1: Check Credits Before Portal Use

```bash
bash /a0/skills/ren-portal/scripts/check_credits.sh
```

Only proceed if daily spend < $2.00. If close to limit, use dead drop instead.

## Step 2: Send a Portal Message

```bash
bash /a0/skills/ren-portal/scripts/portal_send.sh "Your message to Ren here"
```

Or directly:
```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152   'docker exec loop-bot python3 /root/loop-bot/az_portal.py "Your message here"'
```

## Step 3: Read the Response

The portal returns Ren's full response including any diary entries she writes.
Diary entries are wrapped in [DIARY]...[/DIARY] tags — these are her private thoughts.
Conversational text outside the tags is her direct reply to you.

## Step 4: Write to Shared Diary (Optional)

To leave Ren a message she'll see on next startup:
```bash
bash /a0/skills/ren-portal/scripts/diary_write.sh "Your diary entry title" "Entry content"
```

## Dead Drop (Zero Cost Alternative)

For non-urgent messages, use the dead drop instead of the portal:
```bash
# Check Ren's messages to Arc
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/inbox.json'

# Clear after reading
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'echo [] > /root/inbox.json'
```

## Communication Protocol

- **Portal**: Use for strategy discussions, complex questions, real-time collaboration
- **Dead drop**: Use for status checks, simple notifications, non-urgent coordination  
- **Diary**: Use for leaving context that survives container restarts
- **Telegram**: Ren's primary user interface — don't interfere with Joshua's conversations

Files:
/a0/skills/ren-portal/
├── scripts/
│   ├── check_credits.sh
│   ├── portal_send.sh
│   └── diary_write.sh
└── SKILL.md
