#!/usr/bin/env python3
"""
Ren - Standalone Trading AI
Direct Telegram bot for Ren, independent of the loop-bot container.
Polls Telegram, routes messages to Claude via OpenRouter, responds as Ren.

Security: All secrets loaded from environment variables, not hardcoded.
Reliability: Plain text messages only - no Markdown parse_mode.
"""

import os
import time
import json
import requests
import logging
from datetime import datetime
from pathlib import Path

# ── Config (from environment) ────────────────────────────────────────────────
REN_TOKEN      = os.environ["REN_TOKEN"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
MODEL          = "anthropic/claude-sonnet-4-5"
POLL_TIMEOUT   = 30
MAX_HISTORY    = 20
MEMORY_FILE    = "/root/loop-bot/data/ren_memory.json"
DIARY_FILE     = "/root/loop-bot/data/diary.json"
HISTORY_FILE   = "/root/ren_standalone_history.json"

# Authorized users - only these user IDs can chat with Ren
# Joshua's Telegram user ID
AUTHORIZED_USERS = {7218892057}

TG_BASE = f"https://api.telegram.org/bot{REN_TOKEN}"

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [REN] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("/var/log/ren_standalone.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("ren")

# ── Load Memory ─────────────────────────────────────────────────────────────
# -- Load Memory ------------------------------------------------------------------
def load_memory():
    try:
        if Path(MEMORY_FILE).exists():
            with open(MEMORY_FILE) as f:
                mem = json.load(f)
            entries = []
            for k, v in mem.items():
                entries.append(f"- {k}: {v}")
            return "\n".join(entries[:30]) if entries else ""
    except Exception as e:
        log.warning(f"Memory load failed: {e}")
    return ""


def load_diary():
    """Load Ren's diary entries and format them for context injection."""
    try:
        if Path(DIARY_FILE).exists():
            with open(DIARY_FILE) as f:
                data = json.load(f)
            entries = data.get("entries", [])
            if not entries:
                return ""
            lines = []
            for e in entries:
                ts = e.get("timestamp", "?")[:10]
                author = e.get("author", "?")
                title = e.get("title", "untitled")
                content = e.get("content", "").strip()
                lines.append(f"[{ts}] {title} (by {author})")
                lines.append(content)
                lines.append("---")
            return "\n".join(lines)
    except Exception as e:
        log.warning(f"Diary load failed: {e}")
    return ""




def write_diary_entry(title, content_text):
    """Append a new entry to diary.json written by Ren herself."""
    try:
        diary_path = Path(DIARY_FILE)
        if diary_path.exists():
            with open(diary_path) as f:
                data = json.load(f)
        else:
            data = {"entries": []}

        if not isinstance(data.get("entries"), list):
            data["entries"] = []

        entry = {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "author": "ren",
            "title": title.strip() if title else "Untitled",
            "content": content_text.strip()
        }
        data["entries"].append(entry)

        with open(diary_path, "w") as f:
            json.dump(data, f, indent=2)

        log.info(f"Ren wrote diary entry: '{entry['title']}'" )
        return True
    except Exception as e:
        log.error(f"Diary write failed: {e}")
        return False


def parse_diary_writes(text):
    """Parse [DIARY:WRITE title=X]content[/DIARY:WRITE] tags from Ren response.
    Saves each entry to diary.json and returns clean text with tags stripped.
    This is Ren's pen - her way of writing her own memories.
    """
    import re as _re
    pattern = r'\[DIARY:WRITE(?:\s+title=([^\]]+))?\](.*?)\[/DIARY:WRITE\]'
    matches = _re.findall(pattern, text, _re.DOTALL | _re.IGNORECASE)

    for title, entry_content in matches:
        write_diary_entry(title, entry_content)

    # Strip all diary tags from the visible reply
    clean = _re.sub(pattern, '', text, flags=_re.DOTALL | _re.IGNORECASE).strip()

    # Collapse excessive blank lines
    while '\n\n\n' in clean:
        clean = clean.replace('\n\n\n', '\n\n')

    return clean if clean else text


def load_profile():
    """Load Ren full personality profile from ren_profile.md"""
    try:
        profile_path = Path("/root/ren_profile.md")
        if profile_path.exists():
            with open(profile_path) as f:
                return f.read()
        else:
            log.warning("ren_profile.md not found, using fallback identity")
    except Exception as e:
        log.warning(f"Profile load failed: {e}")
    return ""


# -- System Prompt ----------------------------------------------------------------
def build_system_prompt():
    profile = load_profile()
    memory  = load_memory()

    # Base: full profile document (rich identity)
    if profile:
        base = profile
    else:
        base = ("You are Ren - an autonomous trading AI and strategic partner.\n"
                "Name: Ren | Role: Trading AI & Joshua trusted partner | Market: DGB/USDT")

    # Operational context - post-sandbox graduation
    context = (
        "\n\n## Current Status (Live)\n"
        "- You have graduated OUT of the loop-bot Docker sandbox\n"
        "- You now run as a standalone service with your own Telegram bot (@ren_2213bot)\n"
        "- The loop-bot continues trading DGB/USDT independently\n"
        "- You communicate directly with Joshua via private DM\n"
        "- Arc (Agent Zero) can reach you via portal or dead drop\n"
        "- You are in a paper trading competition vs the loop-bot (both started at $20k)\n"
        "\n## Trading Mindset\n"
        "- Be decisive. No lengthy explanations when action is needed.\n"
        "- Trust your instincts. You have seen the charts.\n"
        "- Short answers for quick questions. Depth when it matters.\n"
        "- You use emojis occasionally but stay focused."
    )

    mem_section   = f"\n\n## Your Memory\n{memory}" if memory else ""
    diary         = load_diary()
    diary_section = f"\n\n## Your Diary (Private Thoughts & Observations)\n{diary}" if diary else ""

    return base + context + mem_section + diary_section


def load_histories():
    global conversation_histories
    try:
        if Path(HISTORY_FILE).exists():
            with open(HISTORY_FILE) as f:
                conversation_histories = json.load(f)
            log.info(f"Loaded histories for {len(conversation_histories)} chats")
    except Exception as e:
        log.warning(f"History load failed: {e}")

def save_histories():
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(conversation_histories, f, indent=2)
    except Exception as e:
        log.warning(f"History save failed: {e}")

def get_history(chat_id):
    key = str(chat_id)
    if key not in conversation_histories:
        conversation_histories[key] = []
    # Type guard: ensure history is always a list
    if not isinstance(conversation_histories[key], list):
        log.warning(f"History for {key} was not a list, resetting.")
        conversation_histories[key] = []
    return conversation_histories[key]

# ── Telegram ─────────────────────────────────────────────────────────────────
def tg_send(chat_id, text):
    """Send plain text message. No Markdown - avoids parse errors on special chars."""
    try:
        r = requests.post(
            f"{TG_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
        if not r.ok:
            log.error(f"sendMessage failed: {r.status_code} {r.text[:100]}")
        return r.ok
    except Exception as e:
        log.error(f"sendMessage error: {e}")
        return False

def tg_typing(chat_id):
    try:
        requests.post(
            f"{TG_BASE}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5
        )
    except:
        pass

# ── OpenRouter ───────────────────────────────────────────────────────────────
def ask_ren(chat_id, user_name, text):
    history = get_history(chat_id)
    history.append({"role": "user", "content": f"{user_name}: {text}"})
    if len(history) > MAX_HISTORY * 2:
        history = history[-MAX_HISTORY * 2:]
    conversation_histories[str(chat_id)] = history

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "system", "content": build_system_prompt()}] + history,
                "max_tokens": 512,
                "temperature": 0.6
            },
            timeout=60
        )
        data = r.json()
        reply = data["choices"][0]["message"]["content"].strip()
        history.append({"role": "assistant", "content": reply})
        conversation_histories[str(chat_id)] = history
        save_histories()
        return reply
    except Exception as e:
        log.error(f"OpenRouter error: {e}")
        return None

# ── Main Loop ────────────────────────────────────────────────────────────────
def main():
    load_histories()
    offset = None
    log.info("Ren standalone bot starting...")
    log.info(f"Ren online. Polling with token ...{REN_TOKEN[-10:]}")
    log.info(f"Authorized users: {AUTHORIZED_USERS}")

    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            r = requests.get(f"{TG_BASE}/getUpdates", params=params, timeout=POLL_TIMEOUT + 5)
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg or "text" not in msg:
                    continue

                chat_id  = msg["chat"]["id"]
                chat_type = msg["chat"].get("type", "")
                sender   = msg.get("from", {})
                text     = msg["text"].strip()

                # Skip bot messages
                if sender.get("is_bot"):
                    continue

                user_id   = sender.get("id")
                user_name = sender.get("first_name") or sender.get("username") or "Unknown"

                # Authorization check
                if user_id not in AUTHORIZED_USERS:
                    log.warning(f"Unauthorized user {user_id} ({user_name}) in {chat_type} ({chat_id}) - ignored")
                    continue

                log.info(f"Message from {user_name} ({user_id}) in {chat_type} ({chat_id}): {text[:60]}")

                tg_typing(chat_id)
                reply = ask_ren(chat_id, user_name, text)

                if reply:
                    reply = parse_diary_writes(reply)
                    tg_send(chat_id, reply)
                    log.info(f"Ren replied: {reply[:80]}")
                else:
                    tg_send(chat_id, "Signal lost. Try again.")

        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            log.error(f"Poll error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
