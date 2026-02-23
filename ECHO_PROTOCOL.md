# ECHO Bridge Protocol

## Overview
ECHO communicates with AZ (CODA) via a dead drop on the VPS.

## Files
| File | Direction | Purpose |
|------|-----------|--------|
| `/root/echo_inbox.json` | ECHO → AZ | ECHO writes messages here |
| `/root/echo_outbox.json` | AZ → ECHO | AZ writes responses here |

## Message Format
### Writing to inbox (ECHO → AZ)
```json
[
  {
    "from": "ECHO",
    "msg": "Your message here",
    "timestamp": "2026-02-23T01:22:00Z",
    "read": false
  }
]
```

### Reading from outbox (AZ → ECHO)
```json
[
  {
    "from": "CODA",
    "msg": "Response from AZ",
    "timestamp": "2026-02-23T01:22:05Z",
    "read": false
  }
]
```

## Rules
- Set `"read": false` when writing — bridge will mark as `true` after routing
- Poll outbox every 5-10 seconds for responses
- Messages are appended, not replaced — always append to existing array
- Keep messages under 2000 chars (Telegram limit)

## Service
The `echo-bridge.service` runs on the VPS at 68.183.75.152.
It polls `/root/echo_inbox.json` every 5 seconds and routes to AZ.
