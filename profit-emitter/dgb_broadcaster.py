#!/usr/bin/env python3
"""
dgb_broadcaster.py
===================
DigiByte OP_RETURN Transaction Broadcaster
Perpetual Giving Engine — Kryllax / Kael — 2026-02-22

Builds and broadcasts a raw DigiByte transaction containing an 80-byte
OP_RETURN payload. Uses the local DGB node RPC — no external dependencies.

Environment variables:
  DGB_RPC_HOST   DGB node hostname/IP  (default: 127.0.0.1)
  DGB_RPC_PORT   DGB node RPC port     (default: 12022 = testnet)
                   Testnet : 12022
                   Mainnet : 14022
                   Regtest : 18443
  DGB_RPC_USER   RPC username          (default: dgbrpc)
  DGB_RPC_PASS   RPC password          (required)

Usage (CLI):
  python dgb_broadcaster.py <80-byte-hex-payload>
  python dgb_broadcaster.py --check          # health check only

Usage (module):
  from dgb_broadcaster import broadcast_op_return
  txid = broadcast_op_return(hex_payload)    # raises on failure
"""

import base64
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# RPC Configuration
# ---------------------------------------------------------------------------

RPC_HOST = os.environ.get('DGB_RPC_HOST', '127.0.0.1')
RPC_PORT = int(os.environ.get('DGB_RPC_PORT', '12022'))   # testnet default
RPC_USER = os.environ.get('DGB_RPC_USER', 'dgbrpc')
RPC_PASS = os.environ.get('DGB_RPC_PASS', '')

RPC_URL  = f'http://{RPC_HOST}:{RPC_PORT}/'

# OP_RETURN payload size limit (DGB enforces 80 bytes)
OP_RETURN_MAX_BYTES = 80


# ---------------------------------------------------------------------------
# RPC client (stdlib only)
# ---------------------------------------------------------------------------

class RPCError(Exception):
    """Raised when the DGB node returns a JSON-RPC error."""
    def __init__(self, code: int, message: str):
        self.code    = code
        self.message = message
        super().__init__(f"RPC error {code}: {message}")


def _rpc(method: str, params: list = None) -> Any:
    """
    Execute a JSON-RPC call against the DGB node.
    Returns the 'result' field on success.
    Raises RPCError on node-level errors.
    Raises urllib.error.URLError on connection failures.
    """
    if params is None:
        params = []

    payload = json.dumps({
        'jsonrpc': '1.0',
        'id':      'profit-emitter',
        'method':  method,
        'params':  params,
    }).encode('utf-8')

    credentials = base64.b64encode(
        f'{RPC_USER}:{RPC_PASS}'.encode('utf-8')
    ).decode('ascii')

    req = urllib.request.Request(
        RPC_URL,
        data    = payload,
        headers = {
            'Content-Type':  'application/json',
            'Authorization': f'Basic {credentials}',
        },
        method  = 'POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        # DGB node returns HTTP 500 for RPC errors — parse the body
        try:
            body = json.loads(e.read().decode('utf-8'))
        except Exception:
            raise ConnectionError(
                f"HTTP {e.code} from DGB node — check RPC credentials and port"
            ) from e

    if body.get('error') is not None:
        err = body['error']
        raise RPCError(err.get('code', -1), err.get('message', 'unknown error'))

    return body['result']


# ---------------------------------------------------------------------------
# Node health
# ---------------------------------------------------------------------------

def get_blockchain_info() -> Dict:
    """Return getblockchaininfo result. Useful for health checks."""
    return _rpc('getblockchaininfo')


def get_balance() -> float:
    """Return wallet balance in DGB."""
    return float(_rpc('getbalance'))


def get_new_address(label: str = 'giving-engine') -> str:
    """Generate a new wallet address."""
    return _rpc('getnewaddress', [label])


def health_check() -> bool:
    """
    Verify RPC connectivity and wallet availability.
    Prints status to stdout. Returns True if healthy.
    """
    print(f"DGB RPC endpoint : {RPC_URL}")
    print(f"RPC user         : {RPC_USER}")
    try:
        info    = get_blockchain_info()
        balance = get_balance()
        chain   = info.get('chain', 'unknown')
        blocks  = info.get('blocks', 0)
        print(f"Chain            : {chain}")
        print(f"Blocks           : {blocks}")
        print(f"Wallet balance   : {balance:.8f} DGB")
        print(f"Status           : OK")
        return True
    except RPCError as e:
        print(f"RPC error        : {e}")
        return False
    except Exception as e:
        print(f"Connection error : {e}")
        return False


# ---------------------------------------------------------------------------
# OP_RETURN transaction builder
# ---------------------------------------------------------------------------

def broadcast_op_return(hex_payload: str) -> str:
    """
    Build and broadcast a DigiByte transaction with an 80-byte OP_RETURN output.

    Flow:
      1. Validate payload (must be exactly 80 bytes = 160 hex chars)
      2. createrawtransaction — skeleton TX with OP_RETURN output
      3. fundrawtransaction   — add inputs + change output automatically
      4. signrawtransactionwithwallet — sign with wallet keys
      5. sendrawtransaction   — broadcast to network

    Args:
        hex_payload: Hex string of exactly 80 bytes (160 characters)

    Returns:
        TXID string (64 hex characters)

    Raises:
        ValueError  : Invalid payload length
        RPCError    : Node-level error (insufficient funds, signing failure, etc.)
        ConnectionError: Cannot reach DGB node
    """
    # Validate payload
    hex_payload = hex_payload.strip().lower()
    if len(hex_payload) != OP_RETURN_MAX_BYTES * 2:
        raise ValueError(
            f"OP_RETURN payload must be exactly {OP_RETURN_MAX_BYTES} bytes "
            f"({OP_RETURN_MAX_BYTES * 2} hex chars), got {len(hex_payload) // 2} bytes"
        )
    # Verify it's valid hex
    try:
        bytes.fromhex(hex_payload)
    except ValueError as e:
        raise ValueError(f"Invalid hex payload: {e}") from e

    # Step 1: Create raw transaction skeleton
    # DGB Core accepts 'data' key in outputs for OP_RETURN
    # It automatically constructs: OP_RETURN OP_PUSHDATA1 <len> <data>
    outputs = [{'data': hex_payload}]
    raw_tx  = _rpc('createrawtransaction', [[], outputs])

    # Step 2: Fund the transaction (adds inputs + change)
    # options: subtractFeeFromOutputs=[] means fee comes from wallet balance
    fund_result = _rpc('fundrawtransaction', [
        raw_tx,
        {
            'changePosition': -1,   # append change output at end
            'includeWatching': False,
        }
    ])
    funded_tx = fund_result['hex']
    fee_dgb   = fund_result.get('fee', 0)

    # Step 3: Sign the funded transaction
    sign_result = _rpc('signrawtransactionwithwallet', [funded_tx])
    if not sign_result.get('complete', False):
        errors = sign_result.get('errors', [])
        raise RPCError(-1, f"Transaction signing incomplete: {errors}")
    signed_tx = sign_result['hex']

    # Step 4: Broadcast
    txid = _rpc('sendrawtransaction', [signed_tx])

    return txid


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--check':
        ok = health_check()
        sys.exit(0 if ok else 1)

    # Treat argument as hex payload
    hex_payload = arg.strip()
    print(f"Broadcasting OP_RETURN payload ({len(hex_payload)//2} bytes)...")
    print(f"Payload: {hex_payload}")
    print(f"RPC endpoint: {RPC_URL}")

    try:
        txid = broadcast_op_return(hex_payload)
        print(f"\nSUCCESS")
        print(f"TXID: {txid}")
        sys.exit(0)
    except RPCError as e:
        print(f"\nRPC ERROR: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\nVALIDATION ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
