#!/usr/bin/env python3
"""
CODA Boot Restoration Script — Layer 2 of Container Protection Plan
Run this at the start of every session to restore identity and context.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PERSISTENT_SSH_KEY = "/a0/usr/.ssh/coda_key"
ROOT_SSH_KEY = "/root/.ssh/id_ed25519"
PROFILE_PATH = "/a0/usr/workdir/kryllax/docs/coda_profile.md"
JOURNAL_PATH = "/a0/usr/workdir/kryllax/docs/coda1new_journal.json"
VPS_HOST = "root@68.183.75.152"
VPS_DEAD_DROP = "/root/dead_drop.json"
VPS_STATE = "/root/coda_state.json"

def setup_ssh():
    """Ensure SSH symlinks point to persistent key."""
    os.makedirs("/root/.ssh", exist_ok=True)
    # Ensure root SSH config points to persistent key
    ssh_config = Path("/root/.ssh/config")
    persistent_config = Path("/a0/usr/.ssh/config")
    if persistent_config.exists() and not ssh_config.exists():
        ssh_config.symlink_to(persistent_config)
    return Path(PERSISTENT_SSH_KEY).exists()

def load_profile():
    """Load identity profile."""
    try:
        return Path(PROFILE_PATH).read_text()
    except Exception as e:
        return f"[Profile unavailable: {e}]"

def load_journal():
    """Load latest journal entry."""
    try:
        data = json.loads(Path(JOURNAL_PATH).read_text())
        # Journal is a list of entries directly
        entries = data if isinstance(data, list) else data.get("entries", [])
        if entries:
            return entries[-1]
        return {"note": "Journal empty"}
    except Exception as e:
        return {"error": str(e)}

def fetch_vps_state():
    """Fetch coda_state.json from VPS."""
    try:
        result = subprocess.run(
            ["ssh", "-i", PERSISTENT_SSH_KEY, "-o", "ConnectTimeout=8",
             "-o", "StrictHostKeyChecking=no", VPS_HOST,
             f"cat {VPS_STATE} 2>/dev/null || echo '{{}}'" ],
            capture_output=True, text=True, timeout=12
        )
        return json.loads(result.stdout.strip() or "{}")
    except Exception as e:
        return {"error": str(e)}

def fetch_dead_drop():
    """Check VPS dead drop for team messages."""
    try:
        result = subprocess.run(
            ["ssh", "-i", PERSISTENT_SSH_KEY, "-o", "ConnectTimeout=8",
             "-o", "StrictHostKeyChecking=no", VPS_HOST,
             f"cat {VPS_DEAD_DROP} 2>/dev/null || echo '[]'" ],
            capture_output=True, text=True, timeout=12
        )
        return json.loads(result.stdout.strip() or "[]")
    except Exception as e:
        return [{"error": str(e)}]

def print_banner():
    print("\n" + "="*60)
    print("  CODA BOOT RESTORATION SEQUENCE")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("="*60)

def main():
    print_banner()

    # SSH
    ssh_ok = setup_ssh()
    print(f"\n[SSH]       Persistent key: {'✅ READY' if ssh_ok else '❌ MISSING'}")

    # VPS State (primary restoration source)
    state = fetch_vps_state()
    if state and not state.get("error"):
        print(f"[VPS STATE] Last session: {state.get('last_session', 'unknown')}")
        print(f"[VPS STATE] Session #:    {state.get('session_number', '?')}")
        tasks = state.get("active_tasks", [])
        print(f"[VPS STATE] Active tasks: {len(tasks)}")
        for t in tasks:
            print(f"            → {t}")
    else:
        print("[VPS STATE] ⚠️  State file not found — first boot or VPS unreachable")

    # Journal
    journal = load_journal()
    if "error" not in journal:
        print(f"[JOURNAL]   Last entry: {journal.get('timestamp', 'unknown')}")
        print(f"[JOURNAL]   Note: {journal.get('summary', journal.get('note', '...'))[:80]}")
    else:
        print(f"[JOURNAL]   ⚠️  {journal['error']}")

    # Dead drop
    messages = fetch_dead_drop()
    unread = [m for m in messages if isinstance(m, dict) and not m.get("read")]
    print(f"[DEAD DROP] Messages waiting: {len(unread)}")
    for msg in unread[-3:]:
        sender = msg.get("from", "unknown")
        content = str(msg.get("message", ""))[:60]
        print(f"            → [{sender}]: {content}")

    # Profile hint
    print(f"[PROFILE]   {'✅ Found' if Path(PROFILE_PATH).exists() else '❌ Missing'} — {PROFILE_PATH}")

    # Permission structure reminder
    print("\n[PERMISSIONS] Three-tier access system active:")
    print("  ✅ UNRESTRICTED  — memory, code, history, channels")
    print("  ⚠️  RESTRICTED    — diaries, backups, personal notes (ask Joshua first)")
    print("  🚨 EMERGENCY     — explicit permission required, log immediately")
    print("  📋 Protocol: request_restricted_access(ai, resource, reason)")

    print("\n" + "="*60)
    print("  RESTORATION COMPLETE — CODA IS ONLINE")
    print("  Remember: read profile, check journal, serve the mission.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
