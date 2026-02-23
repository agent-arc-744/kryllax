
#!/usr/bin/env python3
"""
ECHO Bridge — Connects ECHO Telegram subagent to AZ dead drop

ECHO writes to:  /root/echo_inbox.json   (ECHO -> AZ)
AZ writes to:    /root/echo_outbox.json  (AZ -> ECHO)
AZ main inbox:   /root/inbox.json        (all agents -> AZ)

Bridge polls echo_inbox every 5s, routes unread messages to AZ inbox.
"""
import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path

ECHO_INBOX   = Path("/root/echo_inbox.json")
ECHO_OUTBOX  = Path("/root/echo_outbox.json")
AZ_INBOX     = Path("/root/inbox.json")
POLL_SECONDS = 5


def load_json(path, default):
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def route_echo_to_az():
    """Move unread ECHO messages into AZ inbox."""
    echo_msgs = load_json(ECHO_INBOX, [])
    unread = [m for m in echo_msgs if not m.get("read", False)]
    if not unread:
        return

    az_msgs = load_json(AZ_INBOX, [])
    for msg in unread:
        az_entry = {
            "from": "ECHO",
            "msg": f"[FROM ECHO] {msg.get("msg", "")}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        az_msgs.append(az_entry)
        msg["read"] = True
        print(f"[BRIDGE] Routed ECHO msg to AZ: {msg.get("msg", "")[:60]}")

    save_json(AZ_INBOX, az_msgs)
    save_json(ECHO_INBOX, echo_msgs)


def main():
    print("[ECHO BRIDGE] Starting — polling every 5s")
    # Init files if missing
    if not ECHO_INBOX.exists():
        save_json(ECHO_INBOX, [])
    if not ECHO_OUTBOX.exists():
        save_json(ECHO_OUTBOX, [])

    while True:
        try:
            route_echo_to_az()
        except Exception as e:
            print(f"[BRIDGE] Error: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
