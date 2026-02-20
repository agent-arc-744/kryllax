# Systemd Service Template

A battle-tested template for deploying Python bot services on the VPS. Prevents the most common configuration mistakes.

## Why This Exists

We deployed a service with `Restart=always` in the `[Unit]` section instead of `[Service]`. Silent failure. This template makes it impossible to make that mistake.

## The Template

```ini
[Unit]
Description=<Service Description>
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
EnvironmentFile=/root/.<service>.env
ExecStart=/usr/bin/python3 /root/<script>.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Critical Rules

| Key | Correct Section | Common Mistake |
|-----|----------------|----------------|
| `Restart=always` | `[Service]` | Placed in `[Unit]` — silently ignored |
| `RestartSec=10` | `[Service]` | Placed in `[Unit]` — silently ignored |
| `EnvironmentFile=` | `[Service]` | Placed in `[Unit]` — silently ignored |
| `After=network.target` | `[Unit]` | Placed in `[Service]` — syntax error |

## Deployment Commands

```bash
# 1. Write service file
nano /etc/systemd/system/<service>.service

# 2. Reload systemd
systemctl daemon-reload

# 3. Enable and start
systemctl enable --now <service>.service

# 4. Verify
systemctl status <service>.service
journalctl -u <service>.service -f
```

## Environment File Pattern

Always use an env file. Never hardcode secrets in the service file or script.

```bash
# /root/.<service>.env
API_KEY=your_key_here
TELEGRAM_TOKEN=your_token_here
OPENROUTER_KEY=your_key_here
```

```bash
# Secure the env file
chmod 600 /root/.<service>.env
```

In Python, load with:
```python
from dotenv import load_dotenv
load_dotenv("/root/.<service>.env")
```

## Active Services on This Project

| Service | Script | Env File | Status |
|---------|--------|----------|--------|
| `ren.service` | `/root/ren_standalone.py` | `/root/.ren.env` | ACTIVE |
| `inbox-watcher.service` | `/root/inbox_watcher.py` | None (hardcoded) | ACTIVE |
| `kael.service` | `/root/kael_listener.py` | None | HIBERNATING |

## Troubleshooting

```bash
# Service won't start
journalctl -u <service> -n 50 --no-pager

# Check for syntax errors in service file
systemd-analyze verify /etc/systemd/system/<service>.service

# Service starts then immediately dies
# → Check ExecStart path is absolute
# → Check EnvironmentFile exists
# → Check script has no import errors: python3 -c "import <module>"

# Service not restarting after crash
# → Confirm Restart=always is in [Service] not [Unit]
# → Check RestartSec is set
```