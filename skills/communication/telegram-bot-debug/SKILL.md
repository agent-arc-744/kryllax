# Telegram Bot Debug

A systematic checklist for diagnosing silent or misbehaving Telegram bots. Based on every failure mode we actually hit.

## Why This Exists

We spent hours debugging silent bots that turned out to have simple, fixable causes. This checklist would have saved all of that time.

## The Silent Bot Checklist

Work through these in order. Each one takes 30 seconds.

### Check 1: Is the bot token valid?

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getMe" | python3 -m json.tool
```

Expected: `"ok": true` with bot details.
Fail: `"ok": false` → Token is invalid or revoked. Get a new one from @BotFather.

### Check 2: Is the service running?

```bash
ssh root@68.183.75.152 "systemctl status <service>.service"
# OR for Docker:
ssh root@68.183.75.152 "docker ps | grep myloopbot"
```

Fail: Service is inactive → `systemctl start <service>`

### Check 3: Are there errors in the logs?

```bash
ssh root@68.183.75.152 "journalctl -u <service> -n 50 --no-pager"
# OR:
ssh root@68.183.75.152 "docker logs myloopbot --tail 50"
```

Look for: `ImportError`, `SyntaxError`, `KeyError`, `AttributeError`

### Check 4: Group Privacy Mode

For bots in GROUP chats that aren't responding to regular messages:

1. Open Telegram → @BotFather
2. `/mybots` → Select bot → `Bot Settings` → `Group Privacy`
3. If `Enabled` → Turn OFF
4. Restart the bot service

Note: Privacy ON = bot only sees `/commands`. Privacy OFF = bot sees all messages.

| Bot | Privacy Setting | Reason |
|-----|----------------|--------|
| Ren (@ren_2213bot) | OFF | Needs full context |
| Loop-bot (@my_loop_dgb_bot) | ON | Only needs commands |
| Kael (@AgentARC_bot) | OFF | Needs full context |

### Check 5: Authorization Whitelist

Bot receives messages but silently drops them:

```bash
# Add debug logging temporarily
ssh root@68.183.75.152 "grep -n 'authorized\|chat_id\|AUTHORIZED' /root/<script>.py"
```

Common issue: `chat_id` whitelist contains old/wrong IDs.

Fix: Add a debug log before the auth check:
```python
print(f"DEBUG: message from chat_id={update.effective_chat.id}, user_id={update.effective_user.id}")
```

Then check logs to see the actual IDs being received.

### Check 6: Markdown Parse Errors

Bot sends some messages but not others:

```bash
grep -n "parse_mode" /root/<script>.py
```

If `parse_mode='Markdown'` is set → Remove it. AI-generated text frequently contains unescaped `_`, `*`, `[` characters that cause Telegram to reject the message silently.

Fix:
```python
# Remove parse_mode entirely
await bot.send_message(chat_id=chat_id, text=response)
# NOT: await bot.send_message(chat_id=chat_id, text=response, parse_mode='Markdown')
```

### Check 7: Duplicate Processes

Bot responds multiple times to one message:

```bash
ssh root@68.183.75.152 "ps aux | grep <script_name> | grep -v grep"
```

If multiple PIDs → Kill the rogue ones:
```bash
ssh root@68.183.75.152 "kill -9 <ROGUE_PID>"
```

Only the systemd-managed process should remain.

### Check 8: Shared Token Conflict (ECHO)

Messages appearing in wrong chats:

- Two bots sharing the same Telegram token will both receive ALL updates
- Fix: Each bot needs its own unique token from @BotFather
- Check: `grep -r "TELEGRAM_TOKEN\|BOT_TOKEN" /root/*.env /root/*.py`

## Quick Diagnostic Script

```bash
#!/bin/bash
# Run on VPS to get full bot status
TOKEN="your_token_here"
echo "=== Bot Identity ==="
curl -s "https://api.telegram.org/bot$TOKEN/getMe"
echo ""
echo "=== Recent Updates ==="
curl -s "https://api.telegram.org/bot$TOKEN/getUpdates?limit=5"
echo ""
echo "=== Running Processes ==="
ps aux | grep python | grep -v grep
```

## Project Bot Registry

| Bot | Token Env Var | Service | Chat IDs |
|-----|--------------|---------|----------|
| Ren | `REN_TOKEN` in `/root/.ren.env` | `ren.service` | Joshua only (7218892057) |
| Loop-bot | `TELEGRAM_TOKEN` in `/root/loop-bot/.env` | `myloopbot` Docker | Trade channel (-5110248359) |
| Kael | Hardcoded in `kael_listener.py` | `kael.service` (HIBERNATING) | Agent group (deleted) |