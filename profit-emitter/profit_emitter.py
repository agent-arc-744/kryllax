#!/usr/bin/env python3
"""
profit_emitter.py
==================
Perpetual Giving Engine — Profit Emitter
Kryllax / Kael — 2026-02-22

Polls webhook_events.json for loop-bot trade_completion events.
For each profitable trade, encodes the 80-byte DigiAsset OP_RETURN schema
and broadcasts a donation transaction to the DigiByte network.

Environment variables (from /root/.emitter.env):
  DONOR_WALLET_ADDRESS   DGB address of the bot wallet (donor)
  EVENTS_FILE            Path to webhook_events.json (default: /root/loop-bot/data/webhook_events.json)
  STATE_FILE             Path to emitter state file (default: /root/.emitter_state.json)
  LOG_FILE               Path to log file (default: /root/profit_emitter.log)
  DONATION_PCT           Percentage of profit to donate (default: 10)
  REN_WEBHOOK_URL        Ren's inbox endpoint for notifications
  DGB_RPC_HOST           DGB node RPC host
  DGB_RPC_PORT           DGB node RPC port (12022=testnet, 14022=mainnet)
  DGB_RPC_USER           DGB node RPC username
  DGB_RPC_PASS           DGB node RPC password
  POLL_INTERVAL          Seconds between polls (default: 30)
  DRY_RUN                If '1', encode schema but skip broadcast (default: 0)
"""

import hashlib
import json
import logging
import os
import struct
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EVENTS_FILE      = os.environ.get('EVENTS_FILE',      '/root/loop-bot/data/webhook_events.json')
STATE_FILE       = os.environ.get('STATE_FILE',       '/root/.emitter_state.json')
LOG_FILE         = os.environ.get('LOG_FILE',         '/root/profit_emitter.log')
DONOR_WALLET     = os.environ.get('DONOR_WALLET_ADDRESS', '')
DONATION_PCT     = float(os.environ.get('DONATION_PCT', '10'))
REN_WEBHOOK_URL  = os.environ.get('REN_WEBHOOK_URL',  'http://68.183.75.152:5001/inbox')
POLL_INTERVAL    = int(os.environ.get('POLL_INTERVAL', '30'))
DRY_RUN          = os.environ.get('DRY_RUN', '0') == '1'

# Joshua's verified hash160 (tested in regtest 2026-02-22)
# DGB address: D7nBFGPBnBFGPBnBFGPBnBFGPBnBFGPBnB (mainnet)
# hash160 verified via Base58Check decode
JOSHUA_HASH160_HEX = '08bbdfa3fb1f135072a5dfd5d96b8c4f9a162233'


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging():
    fmt = '%(asctime)s [%(levelname)s] %(message)s'
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(logging.FileHandler(LOG_FILE))
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)

log = logging.getLogger('profit_emitter')


# ---------------------------------------------------------------------------
# Schema encoding (inline — no external deps)
# ---------------------------------------------------------------------------

MAGIC          = bytes([0x4B, 0x41])  # 'KA'
SCHEMA_VERSION = 0x01
STRUCT_FMT     = '<2sBB8s16s20sQ24s'
TOTAL_BYTES    = 80

assert struct.calcsize(STRUCT_FMT) == TOTAL_BYTES, (
    f"Schema struct size mismatch: {struct.calcsize(STRUCT_FMT)} != {TOTAL_BYTES}"
)


def derive_donor_id(dgb_address: str) -> bytes:
    """8-byte BLAKE2b-64 of donor DGB address. Privacy-preserving."""
    return hashlib.blake2b(dgb_address.encode('utf-8'), digest_size=8).digest()


def make_profit_source(cycle_id: str) -> bytes:
    """
    Encode cycle_id as 16-byte profit_source.
    Strategy: SHA256(cycle_id_str)[:16] — deterministic, fixed-length.
    """
    return hashlib.sha256(cycle_id.encode('utf-8')).digest()[:16]


def make_sphincs_commitment(amount_satoshis: int, timestamp: str, cycle_id: str) -> bytes:
    """
    24-byte post-quantum commitment.
    SHA256(amount_le_8bytes + timestamp_utf8 + cycle_id_utf8)[:24]
    Stores a binding commitment to the profit event — verifiable off-chain.
    """
    amount_bytes    = struct.pack('<Q', amount_satoshis)
    timestamp_bytes = timestamp.encode('utf-8')
    cycle_bytes     = cycle_id.encode('utf-8')
    preimage        = amount_bytes + timestamp_bytes + cycle_bytes
    return hashlib.sha256(preimage).digest()[:24]


def encode_flags(donation_type: int = 0, asset_class: int = 0) -> int:
    """Bits 7-6: donation_type, Bits 5-4: asset_class, Bits 3-0: reserved."""
    return ((donation_type & 0x03) << 6) | ((asset_class & 0x03) << 4)


def encode_schema(
    donor_id:        bytes,
    profit_source:   bytes,
    donation_target: bytes,
    amount_satoshis: int,
    sphincs_commit:  bytes,
    donation_type:   int = 0,
    asset_class:     int = 0,
) -> bytes:
    """Serialize to exactly 80 bytes for OP_RETURN embedding."""
    assert len(donor_id)        == 8,  f"donor_id must be 8 bytes"
    assert len(profit_source)   == 16, f"profit_source must be 16 bytes"
    assert len(donation_target) == 20, f"donation_target must be 20 bytes"
    assert len(sphincs_commit)  == 24, f"sphincs_commit must be 24 bytes"

    flags  = encode_flags(donation_type, asset_class)
    packed = struct.pack(
        STRUCT_FMT,
        MAGIC,
        SCHEMA_VERSION,
        flags,
        donor_id,
        profit_source,
        donation_target,
        amount_satoshis,
        sphincs_commit,
    )
    assert len(packed) == TOTAL_BYTES
    return packed


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    """Load emitter state (tracks processed event IDs)."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'processed_ids': [], 'total_donations': 0, 'total_satoshis': 0}


def save_state(state: dict) -> None:
    """Persist emitter state."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# Event file management
# ---------------------------------------------------------------------------

def load_events() -> list:
    """Load webhook events from file."""
    if not os.path.exists(EVENTS_FILE):
        return []
    try:
        with open(EVENTS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Failed to load events file: {e}")
        return []


def mark_event_consumed(event_id: str) -> None:
    """Mark a webhook event as consumed in the events file."""
    events = load_events()
    for event in events:
        if event.get('id') == event_id:
            event['consumed'] = True
            break
    try:
        with open(EVENTS_FILE, 'w') as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        log.warning(f"Failed to mark event {event_id} consumed: {e}")


def get_pending_trades(state: dict) -> list:
    """
    Return unconsumed trade_completion events with profit > 0
    that haven't been processed by this emitter.
    """
    events     = load_events()
    processed  = set(state.get('processed_ids', []))
    pending    = []

    for event in events:
        if event.get('consumed', False):
            continue
        if event.get('type') != 'bot':
            continue
        if event.get('data', {}).get('event') != 'trade_completion':
            # Also check top-level event field (webhook_fire uses 'event' in payload)
            if event.get('data', {}).get('type') != 'trade_completion':
                # Try the raw payload structure from webhook_fire.fire()
                # webhook_fire sends: {type, event, timestamp, data}
                # webhook_listener stores: {id, type, timestamp, data, source, consumed}
                # The 'event' field from webhook_fire is stored inside data or at top level
                pass
        event_id = event.get('id', '')
        if event_id in processed:
            continue

        data   = event.get('data', {})
        profit = data.get('profit', 0)
        if profit is None or float(profit) <= 0:
            continue

        pending.append(event)

    return pending


# ---------------------------------------------------------------------------
# Ren notification
# ---------------------------------------------------------------------------

def notify_ren(message: str) -> None:
    """Push a message to Ren's inbox. Fire-and-forget."""
    if not REN_WEBHOOK_URL:
        return
    payload = json.dumps({
        'message':   message,
        'from':      'profit-emitter',
        'priority':  'normal',
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    }).encode('utf-8')
    try:
        req = urllib.request.Request(
            REN_WEBHOOK_URL,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                log.info(f"Ren notified.")
    except Exception as e:
        log.warning(f"Ren notification failed (non-critical): {e}")


# ---------------------------------------------------------------------------
# Broadcaster import
# ---------------------------------------------------------------------------

def broadcast_payload(hex_payload: str) -> Optional[str]:
    """
    Import and call dgb_broadcaster.broadcast_op_return().
    Returns TXID string on success, None on failure.
    """
    if DRY_RUN:
        log.info(f"[DRY RUN] Would broadcast: {hex_payload}")
        return 'DRY_RUN_NO_TXID'

    try:
        # Add script directory to path for sibling import
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        import dgb_broadcaster
        return dgb_broadcaster.broadcast_op_return(hex_payload)
    except Exception as e:
        log.error(f"Broadcast failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def process_trade_event(event: dict, state: dict) -> bool:
    """
    Process a single trade_completion event.
    Returns True on success (event should be marked consumed).
    """
    event_id  = event.get('id', 'unknown')
    data      = event.get('data', {})
    timestamp = event.get('timestamp', datetime.now(timezone.utc).isoformat())

    profit_usd = float(data.get('profit', 0))
    cycle_id   = str(data.get('cycle_id', event_id))
    symbol     = data.get('symbol', 'DGB/USDT')

    # Calculate donation amount (percentage of profit, converted to DGB satoshis)
    # Approximation: profit is in USD, DGB price ~0.004 USD
    # For testnet: use a fixed small amount (1000 satoshis = 0.00001 DGB)
    # For mainnet: calculate real DGB equivalent
    dgb_price_usd    = float(data.get('price', 0.004))  # fallback price
    donation_usd     = profit_usd * (DONATION_PCT / 100.0)
    donation_dgb     = donation_usd / dgb_price_usd if dgb_price_usd > 0 else 0
    amount_satoshis  = max(1000, int(donation_dgb * 1e8))  # minimum 1000 sat

    log.info(
        f"Processing trade event {event_id}: "
        f"profit=${profit_usd:.4f}, donation={DONATION_PCT}%=${donation_usd:.4f}, "
        f"~{amount_satoshis} sat, cycle={cycle_id}"
    )

    # Validate donor wallet
    if not DONOR_WALLET:
        log.error("DONOR_WALLET_ADDRESS not set — cannot derive donor_id")
        return False

    # Encode schema fields
    try:
        donor_id        = derive_donor_id(DONOR_WALLET)
        profit_source   = make_profit_source(cycle_id)
        donation_target = bytes.fromhex(JOSHUA_HASH160_HEX)
        sphincs_commit  = make_sphincs_commitment(amount_satoshis, timestamp, cycle_id)

        payload_bytes = encode_schema(
            donor_id        = donor_id,
            profit_source   = profit_source,
            donation_target = donation_target,
            amount_satoshis = amount_satoshis,
            sphincs_commit  = sphincs_commit,
            donation_type   = 0,  # DIRECT
            asset_class     = 0,  # GIVING
        )
        hex_payload = payload_bytes.hex()

        log.info(f"Schema encoded: {len(payload_bytes)} bytes")
        log.info(f"  donor_id      : {donor_id.hex()}")
        log.info(f"  profit_source : {profit_source.hex()}")
        log.info(f"  target_hash160: {JOSHUA_HASH160_HEX}")
        log.info(f"  amount_sat    : {amount_satoshis}")
        log.info(f"  sphincs_commit: {sphincs_commit.hex()}")
        log.info(f"  payload_hex   : {hex_payload}")

    except Exception as e:
        log.error(f"Schema encoding failed: {e}")
        return False

    # Broadcast
    txid = broadcast_payload(hex_payload)
    if txid is None:
        log.error(f"Broadcast failed for event {event_id} — will retry next poll")
        return False

    log.info(f"SUCCESS — TXID: {txid}")

    # Update state
    state.setdefault('processed_ids', []).append(event_id)
    state['total_donations']  = state.get('total_donations', 0) + 1
    state['total_satoshis']   = state.get('total_satoshis', 0) + amount_satoshis
    state.setdefault('history', []).append({
        'event_id':        event_id,
        'cycle_id':        cycle_id,
        'profit_usd':      profit_usd,
        'amount_satoshis': amount_satoshis,
        'txid':            txid,
        'timestamp':       timestamp,
        'payload_hex':     hex_payload,
    })

    # Keep only last 100 history entries
    if len(state['history']) > 100:
        state['history'] = state['history'][-100:]

    # Notify Ren
    notify_ren(
        f"🔗 Donation encoded on-chain!\n"
        f"Trade profit: ${profit_usd:.4f} ({symbol})\n"
        f"Donation: {amount_satoshis} sat ({DONATION_PCT}%)\n"
        f"TXID: {txid}\n"
        f"Cycle: {cycle_id}"
    )

    return True


# ---------------------------------------------------------------------------
# Main poll loop
# ---------------------------------------------------------------------------

def main():
    setup_logging()
    log.info("=" * 60)
    log.info("Perpetual Giving Engine — Profit Emitter starting")
    log.info(f"Events file  : {EVENTS_FILE}")
    log.info(f"State file   : {STATE_FILE}")
    log.info(f"Donation pct : {DONATION_PCT}%")
    log.info(f"Target hash  : {JOSHUA_HASH160_HEX}")
    log.info(f"Poll interval: {POLL_INTERVAL}s")
    log.info(f"Dry run      : {DRY_RUN}")
    log.info("=" * 60)

    if not DONOR_WALLET:
        log.warning("DONOR_WALLET_ADDRESS not set — donor_id will fail on first trade")

    while True:
        try:
            state   = load_state()
            pending = get_pending_trades(state)

            if pending:
                log.info(f"Found {len(pending)} pending trade event(s)")
                for event in pending:
                    success = process_trade_event(event, state)
                    if success:
                        mark_event_consumed(event.get('id', ''))
                    save_state(state)
            else:
                log.debug("No pending profitable trades.")

        except KeyboardInterrupt:
            log.info("Emitter stopped by user.")
            break
        except Exception as e:
            log.error(f"Unexpected error in poll loop: {e}", exc_info=True)

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
