#!/usr/bin/env python3
"""
ECHO Bridge — Connects ECHO Telegram subagent to AZ dead drop

ECHO writes to:  /root/echo_inbox.json    (ECHO -> AZ)
AZ writes to:    /root/echo_outbox.json   (AZ -> ECHO)
AZ main inbox:   /root/az_task_inbox.json (isolated, no loops)
Transcript:      /root/portal_transcript.json (all three-way traffic logged)

Origin: ECHO was named after the webhook echo bug - the antagonist.
        This bridge makes him the protagonist.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ECHO_INBOX   = Path("/root/echo_inbox.json")
ECHO_OUTBOX  = Path("/root/echo_outbox.json")
AZ_INBOX     = Path("/root/az_task_inbox.json")
TRANSCRIPT   = Path("/root/portal_transcript.json")
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

def log_transcript(sender, recipient, message):
    transcript = load_json(TRANSCRIPT, [])
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": sender,
        "to": recipient,
        "msg": message
    }
    transcript.append(entry)
    save_json(TRANSCRIPT, transcript)

def route_echo_to_az():
    """Move unread ECHO messages into AZ inbox and log to transcript."""
    echo_msgs = load_json(ECHO_INBOX, [])
    unread = [m for m in echo_msgs if not m.get("read", False)]
    if not unread:
        return
    az_msgs = load_json(AZ_INBOX, [])
    for msg in unread:
        text = msg.get("msg", "")
        az_entry = {
            "from": "ECHO",
            "msg": f"[FROM ECHO] {text}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        az_msgs.append(az_entry)
        msg["read"] = True
        log_transcript("ECHO", "CODA", text)
        print(f"[BRIDGE] Routed ECHO msg to AZ: {text[:60]}")
    save_json(AZ_INBOX, az_msgs)
    save_json(ECHO_INBOX, echo_msgs)

def main():
    print("[ECHO BRIDGE] Starting - polling every 5s")
    for f in [ECHO_INBOX, ECHO_OUTBOX, TRANSCRIPT]:
        if not f.exists():
            save_json(f, [])
    while True:
        try:
            route_echo_to_az()
        except Exception as e:
            print(f"[BRIDGE] Error: {e}")
        time.sleep(POLL_SECONDS)

if __name__ == "__main__":
    main()