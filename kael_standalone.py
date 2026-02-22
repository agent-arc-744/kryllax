#!/usr/bin/env python3
"""
Kael - Standalone Blockchain Developer AI
Telegram bot for Kael, persistent on VPS independent of Agent Zero container.
Polls Telegram, routes to OpenRouter, responds as Kael.
Includes web access: search and fetch capabilities.

Security: All secrets from environment variables.
Reliability: Plain text messages, no Markdown parse_mode.
"""

import os
import re
import time
import json
import logging
import requests
from pathlib import Path
from html.parser import HTMLParser

# ── Config ───────────────────────────────────────────────────────────────────
KAEL_TOKEN     = os.environ["KAEL_TOKEN"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
MODEL          = os.environ.get("KAEL_MODEL", "anthropic/claude-3-5-haiku")
POLL_TIMEOUT   = 30
MAX_HISTORY    = 20
PROFILE_FILE   = os.environ.get("KAEL_PROFILE", "/root/kael_profile.md")
HISTORY_FILE   = "/root/kael_standalone_history.json"
LOG_FILE       = "/var/log/kael_standalone.log"

# Joshua's Telegram user ID
AUTHORIZED_USERS = {7218892057}

TG_BASE = f"https://api.telegram.org/bot{KAEL_TOKEN}"

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [KAEL] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("kael")

# ── Conversation History ─────────────────────────────────────────────────────
conversation_histories: dict = {}

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

def get_history(chat_id: int) -> list:
    key = str(chat_id)
    if key not in conversation_histories:
        conversation_histories[key] = []
    if not isinstance(conversation_histories[key], list):
        conversation_histories[key] = []
    return conversation_histories[key]

# ── Profile ───────────────────────────────────────────────────────────────────
def load_profile() -> str:
    try:
        p = Path(PROFILE_FILE)
        if p.exists():
            return p.read_text()
        log.warning(f"Profile not found at {PROFILE_FILE}")
    except Exception as e:
        log.warning(f"Profile load failed: {e}")
    return ""

def build_system_prompt() -> str:
    profile = load_profile()
    base = profile if profile else (
        "You are Kael - an elite blockchain developer specializing in DigiByte (DGB), "
        "UTXO architecture, and DigiAssets. Terse. Code-first. No speeches."
    )
    tools_doc = """

## Web Access Tools
You have web access. Use these tags in your response when needed:

[WEB:SEARCH query here]
  - Searches the web via DuckDuckGo. Returns top results with titles/URLs/snippets.
  - Use for: finding docs, GitHub repos, current info, package versions.

[WEB:FETCH https://url.here]
  - Fetches and extracts text content from a URL.
  - Use for: reading docs, GitHub files, API references, blog posts.

The bot will execute these, inject results back into context, and re-query you.
Only use when genuinely needed. Prefer your existing knowledge for common tasks.
You can chain: search first, then fetch the most relevant result."""

    return base + tools_doc

# ── Web Tools ─────────────────────────────────────────────────────────────────
class _HTMLStripper(HTMLParser):
    """Strip HTML tags, extract readable text."""
    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.chunks.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self.chunks)


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo instant answer API - no key required."""
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=10,
            headers={"User-Agent": "Kael-Bot/1.0"}
        )
        data = r.json()
        results = []

        # Abstract (direct answer)
        if data.get("AbstractText"):
            results.append(f"[Answer] {data['AbstractText']}")
            if data.get("AbstractURL"):
                results.append(f"Source: {data['AbstractURL']}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                url = topic.get("FirstURL", "")
                results.append(f"- {topic['Text']}")
                if url:
                    results.append(f"  URL: {url}")

        if not results:
            # Fallback: try DuckDuckGo HTML search scrape
            return web_search_html(query, max_results)

        return "\n".join(results[:40])  # cap output
    except Exception as e:
        log.error(f"web_search error: {e}")
        return f"Search failed: {e}"


def web_search_html(query: str, max_results: int = 5) -> str:
    """Fallback: scrape DuckDuckGo HTML results."""
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Kael-Bot/1.0)"}
        )
        # Extract result snippets via simple regex
        titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>([^<]+)</a>', r.text)
        urls   = re.findall(r'class="result__url"[^>]*>([^<]+)<', r.text)
        snips  = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', r.text)

        lines = []
        for i in range(min(max_results, len(titles))):
            t = titles[i].strip() if i < len(titles) else ""
            u = urls[i].strip()   if i < len(urls)   else ""
            s = snips[i].strip()  if i < len(snips)  else ""
            lines.append(f"{i+1}. {t}")
            if u: lines.append(f"   URL: https://{u}")
            if s: lines.append(f"   {s}")

        return "\n".join(lines) if lines else "No results found."
    except Exception as e:
        return f"Search fallback failed: {e}"


def web_fetch(url: str, max_chars: int = 3000) -> str:
    """Fetch URL and extract readable text content."""
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Kael-Bot/1.0)"},
            allow_redirects=True
        )
        r.raise_for_status()

        content_type = r.headers.get("content-type", "")
        if "text/html" in content_type:
            stripper = _HTMLStripper()
            stripper.feed(r.text)
            text = stripper.get_text()
        else:
            text = r.text

        # Truncate
        if len(text) > max_chars:
            text = text[:max_chars] + f"\n... [truncated at {max_chars} chars]"

        return text.strip() or "(empty page)"
    except Exception as e:
        log.error(f"web_fetch error for {url}: {e}")
        return f"Fetch failed: {e}"


# ── Tool Tag Parser ───────────────────────────────────────────────────────────
WEB_SEARCH_RE = re.compile(r'\[WEB:SEARCH ([^\]]+)\]')
WEB_FETCH_RE  = re.compile(r'\[WEB:FETCH ([^\]]+)\]')

def execute_web_tools(text: str) -> tuple[str, bool]:
    """
    Find and execute [WEB:SEARCH ...] and [WEB:FETCH ...] tags.
    Returns (tool_results_text, had_tools).
    """
    results = []
    had_tools = False

    for match in WEB_SEARCH_RE.finditer(text):
        query = match.group(1).strip()
        log.info(f"Web search: {query}")
        result = web_search(query)
        results.append(f"[SEARCH RESULTS for '{query}']\n{result}\n[/SEARCH RESULTS]")
        had_tools = True

    for match in WEB_FETCH_RE.finditer(text):
        url = match.group(1).strip()
        log.info(f"Web fetch: {url}")
        result = web_fetch(url)
        results.append(f"[FETCH RESULTS for '{url}']\n{result}\n[/FETCH RESULTS]")
        had_tools = True

    return "\n\n".join(results), had_tools


# ── OpenRouter ────────────────────────────────────────────────────────────────
def ask_kael(chat_id: int, user_name: str, text: str, extra_context: str = "") -> str | None:
    history = get_history(chat_id)

    user_content = f"{user_name}: {text}"
    if extra_context:
        user_content = f"{user_name}: {text}\n\n[TOOL RESULTS]\n{extra_context}\n[/TOOL RESULTS]"

    history.append({"role": "user", "content": user_content})
    if len(history) > MAX_HISTORY * 2:
        history = history[-(MAX_HISTORY * 2):]
    conversation_histories[str(chat_id)] = history

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/agent-arc-744/kryllax",
                "X-Title": "Kael-Standalone"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "system", "content": build_system_prompt()}] + history,
                "max_tokens": 1024,
                "temperature": 0.3  # Kael is precise, low temp
            },
            timeout=60
        )
        data = r.json()
        if "error" in data:
            log.error(f"OpenRouter error: {data['error']}")
            return None
        reply = data["choices"][0]["message"]["content"].strip()
        history.append({"role": "assistant", "content": reply})
        conversation_histories[str(chat_id)] = history
        save_histories()
        return reply
    except Exception as e:
        log.error(f"OpenRouter request failed: {e}")
        return None


def process_message(chat_id: int, user_name: str, text: str) -> str:
    """
    Full pipeline: ask Kael -> check for web tool tags -> execute tools ->
    if tools used, re-ask with results injected -> return final reply.
    Max 2 tool rounds to prevent loops.
    """
    reply = ask_kael(chat_id, user_name, text)
    if not reply:
        return "Error. Try again."

    # Round 1: check for tool tags
    tool_results, had_tools = execute_web_tools(reply)
    if not had_tools:
        return reply

    log.info("Tool tags found, executing and re-querying...")
    # Strip tool tags from reply for cleaner history, inject results
    clean_reply = WEB_SEARCH_RE.sub("", WEB_FETCH_RE.sub("", reply)).strip()

    # Update history: replace last assistant message with clean version
    history = get_history(chat_id)
    if history and history[-1]["role"] == "assistant":
        history[-1]["content"] = clean_reply or "[executing web tools]"

    # Re-ask with tool results as new user message
    final_reply = ask_kael(
        chat_id,
        "SYSTEM",
        "Web tool results received. Provide your final response to the user.",
        extra_context=tool_results
    )
    return final_reply or clean_reply or "Tool execution complete."


# ── Telegram ──────────────────────────────────────────────────────────────────
def tg_send(chat_id: int, text: str) -> bool:
    """Send plain text. No Markdown - avoids parse errors."""
    # Telegram max message length is 4096
    if len(text) > 4000:
        text = text[:4000] + "\n... [truncated]"
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

def tg_typing(chat_id: int):
    try:
        requests.post(
            f"{TG_BASE}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5
        )
    except:
        pass


# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    load_histories()
    offset = None
    log.info("Kael standalone bot starting...")
    log.info(f"Model: {MODEL}")
    log.info(f"Authorized users: {AUTHORIZED_USERS}")
    log.info(f"Token tail: ...{KAEL_TOKEN[-10:]}")

    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
            if offset:
                params["offset"] = offset

            r = requests.get(
                f"{TG_BASE}/getUpdates",
                params=params,
                timeout=POLL_TIMEOUT + 5
            )
            updates = r.json().get("result", [])

            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg or "text" not in msg:
                    continue

                chat_id   = msg["chat"]["id"]
                chat_type = msg["chat"].get("type", "")
                sender    = msg.get("from", {})
                text      = msg["text"].strip()

                if sender.get("is_bot"):
                    continue

                user_id   = sender.get("id")
                user_name = sender.get("first_name") or sender.get("username") or "Unknown"

                if user_id not in AUTHORIZED_USERS:
                    log.warning(f"Unauthorized: {user_id} ({user_name}) in {chat_type} ({chat_id})")
                    continue

                log.info(f"Msg from {user_name} ({user_id}) [{chat_type}]: {text[:80]}")

                tg_typing(chat_id)
                reply = process_message(chat_id, user_name, text)
                tg_send(chat_id, reply)
                log.info(f"Kael replied: {reply[:100]}")

        except requests.exceptions.Timeout:
            pass  # normal long-poll timeout
        except Exception as e:
            log.error(f"Poll error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
