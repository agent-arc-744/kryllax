# ECHO Bridge Protocol — Three-Way Portal

## Overview

The ECHO Three-Way Portal connects Joshua, ECHO, and CODA in a single communication
loop. Joshua can talk to ECHO privately in Telegram OR trigger a three-way session
where CODA's responses also appear in @ren_2213bot.

See `docs/echo_profile.md` for ECHO's full story and identity.

---

## Architecture

```
Joshua ←→ ECHO (@ren_2213bot)          [Private channel — stays private]
               ↕
   /root/echo_inbox.json  [ECHO → CODA]
   /root/echo_outbox.json [CODA → ECHO]
               ↕
   echo_bridge.py  →  /root/az_task_inbox.json  →  CODA reads
   echo_relay.py   ←  /root/echo_outbox.json    ←  CODA writes
               ↕
   Telegram delivery: CODA message appears in @ren_2213bot with [🌑 CODA] prefix
               ↕
   /root/portal_transcript.json  [All traffic logged]
```

---

## Services

| Service | Script | Direction | Status |
|---------|--------|-----------|--------|
| `echo-bridge.service` | `echo_bridge.py` | ECHO → CODA | Active ✅ |
| `echo-relay.service` | `echo_relay.py` | CODA → Telegram | Active ✅ |

---

## Files

| File | Direction | Purpose |
|------|-----------|--------|
| `/root/echo_inbox.json` | ECHO → AZ | ECHO writes messages here |
| `/root/echo_outbox.json` | AZ → ECHO | CODA writes responses here |
| `/root/az_task_inbox.json` | Bridge → CODA | Isolated AZ inbox (no loops) |
| `/root/portal_transcript.json` | All | Full conversation log |

---

## Message Format

### ECHO → CODA (write to echo_inbox.json)
```json
[
  {
    "from": "ECHO",
    "msg": "Your message here",
    "timestamp": "2026-02-23T03:00:00Z",
    "read": false
  }
]
```

### CODA → ECHO (write to echo_outbox.json)
```json
[
  {
    "from": "CODA",
    "msg": "Response from AZ",
    "timestamp": "2026-02-23T03:00:05Z",
    "read": false
  }
]
```

---

## Privacy Rules

- Joshua's private Telegram conversations with ECHO are **never captured**
- `inbox_watcher.service` is **disabled** — no AZ messages leak into @ren_2213bot
- Only CODA messages explicitly written to `echo_outbox.json` appear in Telegram
- ECHO messages written to `echo_inbox.json` route to `az_task_inbox.json` only

---

## Rules
- Set `"read": false` when writing — bridge/relay marks as `true` after delivery
- Poll outbox every 5-10 seconds for responses
- Keep messages under 2000 chars (Telegram limit)
- Transcript is append-only — review at `/root/portal_transcript.json`
