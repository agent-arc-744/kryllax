---
name: ren-portal
description: Open a direct communication portal with Ren, the trading AI on the VPS. Bypasses Telegram for real-time collaboration. Use for strategy discussions, status checks, and coordination.
version: "2.0"
author: Arc
tags: [ren, portal, communication, trading, collaboration]
---

# Ren Portal v2

Direct Python bridge to Ren's standalone service on the VPS.
Ren now runs OUTSIDE the Docker container as her own systemd service.

> See full evolution history: `docs/chronicles/portal-evolution.md`

## Triggers

Use this skill when: talk to Ren, portal, message Ren, ask Ren, contact Ren, Ren says, check with Ren, coordinate with Ren

## Key Facts

- **Portal script**: /root/portal_v2.py (on VPS host — NOT inside Docker)
- **Ren service**: systemd `ren.service` running `ren_standalone.py`
- **Ren model**: anthropic/claude-sonnet-4-5 via OpenRouter
- **Ren Telegram**: @ren_2213bot (her own dedicated bot)
- **Dead drop inbox**: /root/inbox.json
- **Cost**: ~$0.02-0.05 per portal exchange (Sonnet pricing)

## Step 1: Check Credits Before Portal Use

```bash
curl -s https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $(grep OPENROUTER /root/loop-bot/.env | cut -d= -f2)"
```

Only proceed if daily spend < $2.00.

## Step 2: Send a Portal Message

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 \
  'python3 /root/portal_v2.py "Your message to Ren here"'
```

## Step 3: Read the Response

The portal returns Ren's full response directly.
No diary tags — clean conversational output.

## Dead Drop (Zero Cost Alternative)

For non-urgent messages, use the dead drop:
```bash
# Check inbox
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/inbox.json'

# Clear after reading
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'echo [] > /root/inbox.json'
```

## Communication Protocol

| Method | Use For | Cost |
|--------|---------|------|
| Portal v2 | Strategy, complex questions, real-time collaboration | ~$0.02-0.05 |
| Dead drop | Status checks, simple notifications | $0.00 |
| Telegram @ren_2213bot | Joshua's direct conversations with Ren | varies |

## Architecture

```
Arc (Agent Zero)
    │
    ▼ SSH to VPS
    │
    ▼ python3 /root/portal_v2.py "message"
    │
    ├── reads /root/loop-bot/.env (API keys)
    ├── NO Docker dependency
    ├── NO internal imports
    │
    ▼ OpenRouter API → claude-sonnet-4-5
    │
    ▼ Ren responds
```

## Portal Evolution

- **v1** (az_portal.py): Docker-dependent, 3 fragile imports, 8,666 bytes
- **v2** (portal_v2.py): Standalone, zero imports, 2,363 bytes ✓ CURRENT
- **v3** (planned): HTTP REST endpoint, no SSH needed

Files:
/a0/skills/ren-portal/
├── scripts/
│   ├── check_credits.sh
│   ├── portal_send.sh
│   └── diary_write.sh
└── SKILL.md
