# Profit Emitter
**Perpetual Giving Engine — Kael — 2026-02-22**

Bridges loop-bot trade completions to automated on-chain DigiAsset donations.
Every profitable trade encodes an 80-byte OP_RETURN record on the DigiByte blockchain.

---

## How It Works

```
loop-bot closes a profitable trade
    → engine.py fires webhook_fire('bot', 'trade_completion', {profit, cycle_id})
    → webhook_events.json updated on VPS host volume
    → profit_emitter.py polls file every 30s
    → detects profit > 0, unconsumed event
    → encodes 80-byte DigiAsset schema:
        [0:2]   Magic 'KA'           (0x4B41)
        [2]     Version              (0x01)
        [3]     Flags                (DIRECT/GIVING)
        [4:12]  Donor ID             BLAKE2b-8(bot_wallet_address)
        [12:28] Profit Source        SHA256(cycle_id)[:16]
        [28:48] Donation Target      Joshua's hash160
        [48:56] Amount               satoshis (10% of profit)
        [56:80] SPHINCS+ Commitment  SHA256(amount+timestamp+cycle_id)[:24]
    → dgb_broadcaster.py builds raw TX + broadcasts via RPC
    → event marked consumed
    → Ren notified with TXID
```

---

## Files

| File | Description |
|------|-------------|
| `profit_emitter.py` | Main service — polls events, encodes schema, calls broadcaster |
| `dgb_broadcaster.py` | Raw TX builder + DGB node RPC client |
| `emitter.service` | systemd unit for VPS deployment |
| `.emitter.env.example` | Environment variable template |

---

## Prerequisites

1. **DGB testnet node** running on VPS with RPC enabled
   - `digibyte.conf` must include:
     ```
     testnet=1
     server=1
     rpcuser=dgbrpc
     rpcpassword=<your_password>
     rpcallowip=127.0.0.1
     ```
   - Default testnet RPC port: `12022`

2. **Wallet funded** with testnet DGB (for TX fees)
   - Get testnet DGB from: https://testnet-faucet.digibyteservers.io/

3. **loop-bot running** with volume mount at `/root/loop-bot/data/`

---

## Deployment

```bash
# 1. Copy files to VPS
scp profit_emitter.py dgb_broadcaster.py root@VPS_IP:/root/

# 2. Create environment file
cp .emitter.env.example /root/.emitter.env
nano /root/.emitter.env          # fill in real values
chmod 600 /root/.emitter.env

# 3. Test with dry run first
DRY_RUN=1 python3 /root/profit_emitter.py

# 4. Verify broadcaster can reach DGB node
python3 /root/dgb_broadcaster.py --check

# 5. Deploy systemd service
cp emitter.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable emitter
systemctl start emitter

# 6. Monitor
journalctl -u emitter -f
```

---

## Testing

### Dry run (no broadcast)
```bash
DRY_RUN=1 DONOR_WALLET_ADDRESS=DYourAddress python3 profit_emitter.py
```

### Manual broadcast test
```bash
# Health check
python3 dgb_broadcaster.py --check

# Broadcast a test payload (80 bytes = 160 hex chars)
python3 dgb_broadcaster.py 4b410100<...160_hex_chars...>
```

### Inject a test trade event
```bash
python3 - << 'TESTEOF'
import json, time
events_file = '/root/loop-bot/data/webhook_events.json'
try:
    with open(events_file) as f: events = json.load(f)
except: events = []
events.append({
    'id': str(int(time.time() * 1000)),
    'type': 'bot',
    'timestamp': '2026-02-22T03:00:00Z',
    'data': {'event': 'trade_completion', 'profit': 3.75, 'cycle_id': 'test_cycle_1', 'symbol': 'DGB/USDT', 'price': 0.004},
    'source': 'test',
    'consumed': False
})
with open(events_file, 'w') as f: json.dump(events, f, indent=2)
print('Test event injected.')
TESTEOF
```

---

## Switching to Mainnet

In `/root/.emitter.env`:
```bash
DGB_RPC_PORT=14022    # mainnet port
```

Ensure DGB node is running in mainnet mode (remove `testnet=1` from `digibyte.conf`).

---

## Donation Target

Hardcoded in `profit_emitter.py`:
```python
JOSHUA_HASH160_HEX = '08bbdfa3fb1f135072a5dfd5d96b8c4f9a162233'
```
Verified via Base58Check decode and confirmed in regtest TX on 2026-02-22.
To change recipient: update this constant and redeploy.

---

## Schema Reference

See `/kryllax/digiasset_schema/schema.py` for the canonical implementation.
The encoding logic in `profit_emitter.py` is inlined for standalone deployment.

---

*Built by Kael. Arc's blueprint. Joshua's vision.*
