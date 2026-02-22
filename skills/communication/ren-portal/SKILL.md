---
name: ren-portal
description: Open a direct communication portal with Ren, the trading AI on the VPS. Bypasses Telegram for real-time collaboration. Use for strategy discussions, status checks, and coordination.
version: "3.0"
author: Arc
tags: [ren, portal, communication, trading, collaboration]
---

# Ren Portal v3

Direct Python bridge to Ren's standalone service on the VPS.
Ren runs OUTSIDE Docker as her own systemd service.

## Triggers

Use this skill when: talk to Ren, portal, message Ren, ask Ren, contact Ren, Ren says, check with Ren, coordinate with Ren

## Key Facts

- **Portal script**: /root/portal_v3.py (on VPS host)
- **Ren service**: systemd `ren.service` running `ren_standalone.py`
- **Ren model**: anthropic/claude-sonnet-4-5 via OpenRouter
- **Ren Telegram**: @ren_2213bot (ID: 7812603448)
- **Joshua Telegram**: user ID 7218892057, chat ID 7218892057
- **Dead drop inbox**: /root/inbox.json
- **Portal history**: /root/portal_history.json (persistent across calls)
- **Cost**: ~$0.02-0.05 per portal exchange

## Bugs Fixed in v3 (vs v2)
- v2 read OPENROUTER_API_KEY from /root/loop-bot/.env — WRONG
- v3 reads OPENROUTER_KEY from /root/.ren.env — CORRECT
- v3 loads Ren's diary + memory + profile for rich context
- v3 maintains persistent conversation history

## Step 1: Check Credits

```bash
curl -s https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $(grep OPENROUTER_KEY /root/.ren.env | cut -d= -f2)"
```

## Step 2: Send Portal Message

```bash
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 \
  'python3 /root/portal_v3.py "Your message to Ren here"'
```

## Dead Drop (Zero Cost)

```bash
# Write to inbox (Arc → Ren)
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 \
  'echo "[{\"message\": \"your message\", \"priority\": \"normal\", \"from\": \"Arc\"}]" > /root/inbox.json'

# Ren auto-processes inbox on next poll cycle (~30s)
# Her response is sent to Joshua via Telegram automatically

# Check inbox status
ssh -i /root/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@68.183.75.152 'cat /root/inbox.json'
```

## Architecture

```
Arc (Agent Zero)
    │
    ▼ SSH to VPS
    │
    ▼ python3 /root/portal_v3.py "message"
    │
    ├── reads /root/.ren.env (OPENROUTER_KEY)
    ├── loads diary + memory + ren_profile.md
    ├── maintains /root/portal_history.json
    │
    ▼ OpenRouter API → claude-sonnet-4-5
    │
    ▼ Ren responds
```

## Portal Evolution

- **v1** (az_portal.py): Docker-dependent, 3 fragile imports
- **v2** (portal_v2.py): Wrong env file, wrong variable name — BROKEN
- **v3** (portal_v3.py): Correct env, rich context, persistent history ✓ CURRENT
