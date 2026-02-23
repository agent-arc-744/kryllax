"""AI Permission & Access Control System — Phase 1 (Honor System + Audit Trail)

This module implements the diary privacy framework designed by Ren and Joshua.
All AI agents must use this module before accessing restricted resources.

Permission Tiers:
  UNRESTRICTED  — search freely (memory, code, conversation history)
  RESTRICTED    — ask Joshua first (diaries, backups, personal notes)
  EMERGENCY     — explicit permission only (system recovery scenarios)

Usage:
    from request_access import request_restricted_access, emergency_access
    msg = request_restricted_access("coda", "data/diary.json", "need context for recovery")
    print(msg)  # Logs request, returns pending message
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# Access log location (VPS + local)
ACCESS_LOG_PATHS = [
    Path("/root/loop-bot/data/access_log.json"),
    Path("data/access_log.json"),
]

# Restricted resource list (canonical paths and keywords)
RESTRICTED_RESOURCES = [
    "diary.json",
    "coda1new_journal.json",
    "coda0ld_journal.json",
    "joshua_journal.json",
    "arc_journal.json",
    "arc-backups",
    "personal",
]


def _find_log_path() -> Path:
    """Find the writable access log path."""
    for p in ACCESS_LOG_PATHS:
        if p.parent.exists():
            return p
    # Fallback: current directory
    return Path("access_log.json")


def log_access_request(
    ai_name: str,
    resource: str,
    reason: str,
    permission_granted: bool = False,
    emergency: bool = False,
) -> dict:
    """Append an access request entry to the audit log."""
    log_path = _find_log_path()
    log = []
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text())
        except Exception:
            log = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ai_name": ai_name,
        "resource": resource,
        "reason": reason,
        "permission_granted": permission_granted,
        "emergency": emergency,
    }
    log.append(entry)
    log_path.write_text(json.dumps(log, indent=2))
    return entry


def request_restricted_access(ai_name: str, resource: str, reason: str) -> str:
    """Request access to a restricted resource. Logs the attempt automatically."""
    log_access_request(ai_name, resource, reason, permission_granted=False)
    return (
        f"ACCESS REQUEST LOGGED — Awaiting Joshua's permission.\n"
        f"AI: {ai_name}\n"
        f"Resource: {resource}\n"
        f"Reason: {reason}\n"
        f"Status: Pending approval. Do not proceed until granted."
    )


def grant_access(ai_name: str, resource: str, reason: str) -> str:
    """Mark access as granted (Joshua calls this after approving)."""
    log_access_request(ai_name, resource, reason, permission_granted=True)
    return f"Access granted: {ai_name} may access {resource}."


def emergency_access(ai_name: str, resource: str, reason: str) -> str:
    """Emergency access — logs immediately. Use ONLY in catastrophic scenarios."""
    entry = log_access_request(ai_name, resource, reason, permission_granted=True, emergency=True)
    return (
        f"EMERGENCY ACCESS LOGGED — Notify Joshua immediately.\n"
        f"AI: {ai_name}\n"
        f"Resource: {resource}\n"
        f"Reason: {reason}\n"
        f"Timestamp: {entry['timestamp']}\n"
        f"You MUST report this access to Joshua as soon as possible."
    )


def view_log(limit: int = 20) -> list:
    """Return the last N access log entries."""
    log_path = _find_log_path()
    if not log_path.exists():
        return []
    try:
        log = json.loads(log_path.read_text())
        return log[-limit:]
    except Exception:
        return []
