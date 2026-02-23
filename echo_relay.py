#!/usr/bin/env python3
"""
ECHO Relay — Delivers CODA messages into @ren_2213bot Telegram channel

This script completes the three-way portal:
  CODA  → /root/echo_outbox.json → echo_relay.py → Telegram (@ren_2213bot)
  ECHO  → /root/echo_inbox.json  → echo_bridge.py → /root/az_task_inbox.json → CODA

All traffic is logged to /root/portal_transcript.json

Origin: ECHO was named after the webhook echo bug — the antagonist.
        This script makes him the protagonist.
"""
import json
import time
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Load token from .ren.env
def load_env(path="/root/.ren.env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except Exception as e:
        print(f"[RELAY] Failed to load env: {e}")
    return env

ENV            = load_env()
REN_TOKEN      = ENV.get("REN_TOKEN", "")
JOSHUA_CHAT_ID = 7218892057  # Joshua private DM with @ren_2213bot
ECHO_OUTBOX    = Path("/root/echo_outbox.json")
TRANSCRIPT     = Path("/root/portal_transcript.json")
POLL_SECONDS   = 5
TG_API         = f"https://api.telegram.org/bot{REN_TOKEN}"


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


def tg_send(text):
    """Send message to Joshua via @ren_2213bot."""
    if not REN_TOKEN:
        print("[RELAY] No REN_TOKEN — cannot send Telegram message")
        return False
    try:
        payload = json.dumps({
            "chat_id": JOSHUA_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(
            f"{TG_API}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        print(f"[RELAY] Telegram send error: {e}")
        return False


def relay_coda_to_telegram():
    """Deliver unread CODA messages from outbox to Telegram."""
    outbox = load_json(ECHO_OUTBOX, [])
    unread = [m for m in outbox if not m.get("read", False)]
    if not unread:
        return

    for msg in unread:
        text = msg.get("msg", "").strip()
        if not text:
            msg["read"] = True
            continue

        # Format with CODA signature so Joshua sees who's speaking
        formatted = f"\U0001f311 *[CODA → ECHO Portal]*\n\n{text}"

        success = tg_send(formatted)
        if success:
            msg["read"] = True
            log_transcript("CODA", "ECHO", text)
            print(f"[RELAY] Delivered CODA msg to Telegram: {text[:60]}")
        else:
            print(f"[RELAY] Failed to deliver: {text[:40]}")

    save_json(ECHO_OUTBOX, outbox)


def main():
    print("[ECHO RELAY] Starting — polling outbox every 5s")
    print(f"[ECHO RELAY] Token loaded: {'YES' if REN_TOKEN else 'NO'}")
    if not ECHO_OUTBOX.exists():
        save_json(ECHO_OUTBOX, [])
    if not TRANSCRIPT.exists():
        save_json(TRANSCRIPT, [])

    while True:
        try:
            relay_coda_to_telegram()
        except Exception as e:
            print(f"[RELAY] Error: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
