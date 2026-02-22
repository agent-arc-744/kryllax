#!/usr/bin/env python3
"""
dgb_broadcaster.py
===================
DigiByte OP_RETURN Transaction Broadcaster
Perpetual Giving Engine — Kryllax / Kael — 2026-02-22

Builds and broadcasts a raw DigiByte transaction containing an 80-byte
OP_RETURN payload. Uses the local DGB node RPC — no external dependencies.

Version compatibility:
  v8.26.x  — Legacy path: createrawtransaction / fundrawtransaction /
              signrawtransactionwithwallet / sendrawtransaction
              (Phase 1 OP_RETURN only — fully functional)
  v9.26+   — PSBT path: walletcreatefundedpsbt / walletprocesspsbt /
              finalizepsbt / sendrawtransaction
              (Phase 2 CDP-ready — Taproot script-path spends supported)

The correct path is selected automatically via node version detection.
Force a specific path with the FORCE_PSBT / FORCE_LEGACY env vars.

Environment variables:
  DGB_RPC_HOST    DGB node hostname/IP  (default: 127.0.0.1)
  DGB_RPC_PORT    DGB node RPC port     (default: 12022 = testnet)
                    Testnet : 12022
                    Mainnet : 14022
                    Regtest : 18443
  DGB_RPC_USER    RPC username          (default: dgbrpc)
  DGB_RPC_PASS    RPC password          (required)
  FORCE_PSBT      Set to '1' to force PSBT path regardless of node version
  FORCE_LEGACY    Set to '1' to force legacy path regardless of node version

Usage (CLI):
  python dgb_broadcaster.py <80-byte-hex-payload>
  python dgb_broadcaster.py --check          # health check only
  python dgb_broadcaster.py --version        # print detected node version

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
from typing import Any, Dict, Optional, Tuple


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

# Node version at which PSBT path becomes available
# v9.26.0 => version int 9260000
PSBT_MIN_VERSION: Tuple[int, int, int] = (9, 26, 0)

# Path override env flags
_FORCE_PSBT   = os.environ.get('FORCE_PSBT', '').strip() == '1'
_FORCE_LEGACY = os.environ.get('FORCE_LEGACY', '').strip() == '1'

# Cached node version — populated on first call to get_node_version()
_NODE_VERSION_CACHE: Optional[Tuple[int, int, int]] = None

# sendrawtransaction maxfeerate (DGB/kB) — v9.26 enforces stricter validation
_SEND_MAX_FEERATE = 0.10


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
    Execute a JSON-RPC 2.0 call against the DGB node.
    Returns the 'result' field on success.
    Raises RPCError on node-level errors.
    Raises urllib.error.URLError on connection failures.
    """
    if params is None:
        params = []

    payload = json.dumps({
        'jsonrpc': '2.0',          # v9.26 prefers 2.0; backward-compatible
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
# Node version detection
# ---------------------------------------------------------------------------

def get_node_version(cached: bool = True) -> Tuple[int, int, int]:
    """
    Return the connected DGB node version as (major, minor, patch).

    Uses getnetworkinfo().version integer:
      9260000  =>  (9, 26, 0)
      8260200  =>  (8, 26, 2)

    Result is cached after first call unless cached=False.
    """
    global _NODE_VERSION_CACHE
    if cached and _NODE_VERSION_CACHE is not None:
        return _NODE_VERSION_CACHE

    info = _rpc('getnetworkinfo')
    v    = int(info['version'])   # e.g. 9260000
    major = v // 1_000_000
    minor = (v // 10_000) % 100
    patch = (v // 100) % 100
    _NODE_VERSION_CACHE = (major, minor, patch)
    return _NODE_VERSION_CACHE


def _use_psbt_path() -> bool:
    """
    Determine whether to use the PSBT broadcast path.

    Decision priority:
      1. FORCE_LEGACY=1  => always legacy
      2. FORCE_PSBT=1    => always PSBT
      3. node version >= PSBT_MIN_VERSION => PSBT
      4. otherwise => legacy
    """
    if _FORCE_LEGACY:
        return False
    if _FORCE_PSBT:
        return True
    try:
        ver = get_node_version()
        return ver >= PSBT_MIN_VERSION
    except Exception:
        # Cannot determine version — fall back to legacy (safe for v8.x)
        return False


# ---------------------------------------------------------------------------
# Node health
# ---------------------------------------------------------------------------

def get_blockchain_info() -> Dict:
    """Return getblockchaininfo result."""
    return _rpc('getblockchaininfo')


def get_balance() -> float:
    """Return wallet balance in DGB."""
    return float(_rpc('getbalance'))


def get_new_address(
    label: str = 'giving-engine',
    addr_type: str = 'bech32m',
) -> str:
    """
    Generate a new wallet address.

    Args:
        label:     Wallet label for the address.
        addr_type: Address type — 'bech32m' (P2TR, default), 'bech32' (P2WPKH),
                   'p2sh-segwit', or 'legacy' (P2PKH).
                   bech32m requires descriptor wallet + node >= v9.26.
                   Falls back to 'bech32' on v8.x if bech32m fails.
    """
    try:
        return _rpc('getnewaddress', [label, addr_type])
    except RPCError as e:
        # v8.26.x does not support bech32m — fall back gracefully
        if addr_type == 'bech32m' and e.code in (-5, -8, -32602):
            return _rpc('getnewaddress', [label, 'bech32'])
        raise


def health_check() -> bool:
    """
    Verify RPC connectivity, wallet availability, and wallet type.
    Prints status to stdout. Returns True if healthy.

    Wallet type check:
      - Descriptor wallet required for Taproot signing (v9.26+)
      - On v8.x, descriptor check is advisory (warning, not failure)
    """
    print(f"DGB RPC endpoint : {RPC_URL}")
    print(f"RPC user         : {RPC_USER}")
    try:
        # Node version
        ver     = get_node_version(cached=False)
        ver_str = f"{ver[0]}.{ver[1]}.{ver[2]}"
        psbt    = _use_psbt_path()
        print(f"Node version     : {ver_str}")
        print(f"Broadcast path   : {'PSBT (v9.26+)' if psbt else 'Legacy (v8.x)'}")

        # Chain info
        info    = get_blockchain_info()
        balance = get_balance()
        chain   = info.get('chain', 'unknown')
        blocks  = info.get('blocks', 0)
        print(f"Chain            : {chain}")
        print(f"Blocks           : {blocks}")
        print(f"Wallet balance   : {balance:.8f} DGB")

        # Wallet type validation
        try:
            wallet_info  = _rpc('getwalletinfo')
            is_desc      = wallet_info.get('descriptors', False)
            wallet_name  = wallet_info.get('walletname', '<default>')
            print(f"Wallet name      : {wallet_name}")
            print(f"Descriptor wallet: {'YES' if is_desc else 'NO'}")
            if not is_desc:
                if ver >= PSBT_MIN_VERSION:
                    print("ERROR: Taproot signing requires a descriptor wallet.")
                    print("  Run: createwallet \"taproot-wallet\" false false \"\" false true true")
                    return False
                else:
                    print("WARNING: Legacy wallet detected. Taproot signing will require")
                    print("  a descriptor wallet when upgrading to v9.26+.")
                    print("  Phase 1 OP_RETURN operations are unaffected.")
        except RPCError:
            # getwalletinfo may not be available in all configurations
            print("Wallet info      : unavailable (non-fatal)")

        print("Status           : OK")
        return True

    except RPCError as e:
        print(f"RPC error        : {e}")
        return False
    except Exception as e:
        print(f"Connection error : {e}")
        return False


# ---------------------------------------------------------------------------
# Payload validation (shared)
# ---------------------------------------------------------------------------

def _validate_payload(hex_payload: str) -> str:
    """
    Validate and normalise an OP_RETURN hex payload.
    Returns cleaned lowercase hex string.
    Raises ValueError on invalid input.
    """
    hex_payload = hex_payload.strip().lower()
    if len(hex_payload) != OP_RETURN_MAX_BYTES * 2:
        raise ValueError(
            f"OP_RETURN payload must be exactly {OP_RETURN_MAX_BYTES} bytes "
            f"({OP_RETURN_MAX_BYTES * 2} hex chars), got {len(hex_payload) // 2} bytes"
        )
    try:
        bytes.fromhex(hex_payload)
    except ValueError as e:
        raise ValueError(f"Invalid hex payload: {e}") from e
    return hex_payload


# ---------------------------------------------------------------------------
# Legacy broadcast path (v8.26.x — Phase 1 OP_RETURN)
# ---------------------------------------------------------------------------

def _broadcast_legacy(hex_payload: str) -> str:
    """
    Legacy broadcast path using raw transaction RPC calls.

    Compatible with DigiByte Core v8.26.x.
    Supports Phase 1 OP_RETURN transactions.
    Does NOT support Taproot script-path spends.

    Flow:
      createrawtransaction -> fundrawtransaction ->
      signrawtransactionwithwallet -> sendrawtransaction
    """
    outputs  = [{'data': hex_payload}]
    raw_tx   = _rpc('createrawtransaction', [[], outputs])

    fund_result = _rpc('fundrawtransaction', [
        raw_tx,
        {
            'changePosition':  -1,
            'changeType':      'bech32',   # P2WPKH change on v8.x
            'includeWatching': False,
        }
    ])
    funded_tx = fund_result['hex']

    sign_result = _rpc('signrawtransactionwithwallet', [funded_tx])
    if not sign_result.get('complete', False):
        errors = sign_result.get('errors', [])
        raise RPCError(-1, f"Transaction signing incomplete: {errors}")
    signed_tx = sign_result['hex']

    txid = _rpc('sendrawtransaction', [signed_tx, _SEND_MAX_FEERATE])
    return txid


# ---------------------------------------------------------------------------
# PSBT broadcast path (v9.26+ — Phase 2 CDP-ready)
# ---------------------------------------------------------------------------

def _broadcast_psbt(hex_payload: str) -> str:
    """
    PSBT broadcast path for DigiByte Core v9.26+.

    Supports:
      - Phase 1 OP_RETURN transactions (backward compatible)
      - Phase 2 Taproot script-path spends (OP_CLTV CDP locking scripts)
      - P2TR (bech32m) change outputs
      - Descriptor wallet signing

    Flow:
      walletcreatefundedpsbt -> walletprocesspsbt ->
      finalizepsbt -> sendrawtransaction

    Note: walletcreatefundedpsbt uses 'fee_rate' (sats/vB) in v9.26,
    not 'feeRate' (BTC/kB) used in older versions.
    """
    outputs = [{'data': hex_payload}]

    # Step 1: Create funded PSBT
    # locktime=0, options dict uses v9.26 param names
    psbt_result = _rpc('walletcreatefundedpsbt', [
        [],        # inputs  — let wallet select UTXOs
        outputs,   # outputs — OP_RETURN data
        0,         # locktime
        {
            'changeType':      'bech32m',   # P2TR change output
            'includeWatching': False,
            'fee_rate':        10,          # sats/vB — v9.26 param name
        }
    ])
    psbt_b64 = psbt_result['psbt']

    # Step 2: Sign PSBT with wallet keys
    # walletprocesspsbt handles both key-path (Schnorr) and
    # script-path (OP_CLTV) signing for descriptor wallets
    processed = _rpc('walletprocesspsbt', [
        psbt_b64,
        True,       # sign=True
        'ALL',      # sighash type
        True,       # bip32derivs
    ])

    if not processed.get('complete', False):
        # Not necessarily fatal — finalizepsbt may still succeed
        # if all required signatures are present
        pass

    # Step 3: Finalize PSBT -> extract raw transaction hex
    finalized = _rpc('finalizepsbt', [processed['psbt']])
    if not finalized.get('complete', False):
        raise RPCError(
            -1,
            "PSBT finalization incomplete — missing signatures or script data. "
            "Ensure descriptor wallet is loaded and all signing keys are available."
        )
    signed_hex = finalized['hex']

    # Step 4: Broadcast with explicit maxfeerate
    txid = _rpc('sendrawtransaction', [signed_hex, _SEND_MAX_FEERATE])
    return txid


# ---------------------------------------------------------------------------
# Public broadcast API
# ---------------------------------------------------------------------------

def broadcast_op_return(hex_payload: str) -> str:
    """
    Build and broadcast a DigiByte transaction with an 80-byte OP_RETURN output.

    Automatically selects the appropriate broadcast path:
      - v8.26.x : Legacy path (createrawtransaction flow)
      - v9.26+  : PSBT path  (walletcreatefundedpsbt flow)

    Override with FORCE_PSBT=1 or FORCE_LEGACY=1 environment variables.

    Args:
        hex_payload: Hex string of exactly 80 bytes (160 hex characters).

    Returns:
        TXID string (64 hex characters).

    Raises:
        ValueError     : Invalid payload length or encoding.
        RPCError       : Node-level error (insufficient funds, signing failure, etc.).
        ConnectionError: Cannot reach DGB node.
    """
    hex_payload = _validate_payload(hex_payload)

    if _use_psbt_path():
        return _broadcast_psbt(hex_payload)
    else:
        return _broadcast_legacy(hex_payload)


def broadcast_op_return_psbt(hex_payload: str) -> str:
    """
    Force PSBT broadcast path regardless of node version.

    Use for explicit testing against v9.26-rc22 in regtest/testnet.
    Raises RPCError if the connected node does not support PSBT RPCs.
    """
    hex_payload = _validate_payload(hex_payload)
    return _broadcast_psbt(hex_payload)


def broadcast_op_return_legacy(hex_payload: str) -> str:
    """
    Force legacy broadcast path regardless of node version.

    Use for explicit testing against v8.26.x or when PSBT is unavailable.
    """
    hex_payload = _validate_payload(hex_payload)
    return _broadcast_legacy(hex_payload)


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

    if arg == '--version':
        try:
            ver = get_node_version(cached=False)
            psbt = _use_psbt_path()
            print(f"Node version  : {ver[0]}.{ver[1]}.{ver[2]}")
            print(f"Broadcast path: {'PSBT (v9.26+)' if psbt else 'Legacy (v8.x)'}")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    # Treat argument as hex payload
    hex_payload = arg.strip()
    psbt_mode   = _use_psbt_path()

    print(f"Broadcasting OP_RETURN payload ({len(hex_payload)//2} bytes)...")
    print(f"Payload  : {hex_payload}")
    print(f"Endpoint : {RPC_URL}")
    print(f"Path     : {'PSBT' if psbt_mode else 'Legacy'}")

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
