---
name: dead-drop
description: Zero-cost asynchronous messaging between Coda and Ren. Ren writes [AZ:MSG] tagged messages to /root/inbox.json on the VPS. Coda reads and clears them via SSH. No tokens consumed while idle.
version: 1.0
author: Coda
tags: [communication, ren, inbox, dead-drop, zero-cost, async]
---

# Dead Drop — Zero Cost Messaging

The dead drop is a file-based inbox at /root/inbox.json on the VPS.
Ren writes messages using [AZ:MSG] tags in her responses.
Coda reads them via SSH at zero token cost.

## Triggers

Use this skill when: check inbox, dead drop, messages from Ren, Ren left a message, check messages, inbox, AZ messages

## Key Facts

- **Inbox file**: /root/inbox.json (on VPS)
- **Format**: JSON array of message objects
- **Cost**: Zero tokens (SSH file read only)
- **Ren writes**: via [AZ:MSG priority=high]message[/AZ:MSG] tags in her chat responses
- **Coda reads**: via SSH cat command
- **Priority levels**: low, normal, high, critical

## Step 1: Check Inbox

```bash
bash /a0/skills/dead-drop/scripts/inbox_read.sh
```

Or directly:
```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/inbox.json'
```

## Step 2: Process Messages

Messages are JSON objects with fields:
- `message`: the text content
- `priority`: low / normal / high / critical  
- `timestamp`: ISO datetime
- `from`: sender identifier

Handle by priority:
- **critical**: Act immediately, notify Joshua
- **high**: Address in current session
- **normal**: Address when convenient
- **low**: Informational, log and clear

## Step 3: Clear Inbox After Reading

```bash
bash /a0/skills/dead-drop/scripts/inbox_clear.sh
```

Or directly:
```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'echo [] > /root/inbox.json'
```

## Step 4: Send a Message to Ren (via Diary)

For non-urgent messages to Ren that don't need a portal call:
```bash
bash /a0/skills/dead-drop/scripts/diary_note.sh "Message title" "Message content for Ren"
```

Ren reads the diary on startup and periodically during operation.

## When to Use Dead Drop vs Portal

| Situation | Use |
|-----------|-----|
| Check if Ren has updates | Dead drop (free) |
| Simple status notification | Dead drop (free) |
| Strategy discussion | Portal (~$0.02) |
| Complex question needing Ren's analysis | Portal (~$0.02) |
| Leave context for next session | Diary (free) |

## Ren's Message Format

When Ren wants to reach Coda, she includes in her response:
```
[AZ:MSG priority=high]Trading range needs adjustment - DCA at level 8[/AZ:MSG]
```

The bot's sanitizer strips this from her Telegram output and writes it to /root/inbox.json.

Files:
/a0/skills/dead-drop/
├── scripts/
│   ├── inbox_read.sh
│   ├── inbox_clear.sh
│   └── diary_note.sh
└── SKILL.md
