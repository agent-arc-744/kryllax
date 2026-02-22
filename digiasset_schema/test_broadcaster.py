#!/usr/bin/env python3
"""
test_broadcaster.py
====================
Unit tests for dgb_broadcaster.py — both legacy and PSBT paths.
Perpetual Giving Engine — Kryllax / Kael — 2026-02-22

Runs with: python -m pytest test_broadcaster.py -v
Or:        python test_broadcaster.py

All tests use mock RPC — no live DGB node required.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

# Resolve broadcaster path
BROADCASTER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'profit-emitter'
)
sys.path.insert(0, os.path.abspath(BROADCASTER_DIR))

import dgb_broadcaster as b


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

GOOD_PAYLOAD   = 'ab' * 80          # 80 bytes, valid hex
FAKE_TXID      = 'f' * 64           # 32-byte fake txid
FAKE_RAW_TX    = 'deadbeef' * 10
FAKE_FUNDED_TX = 'cafebabe' * 10
FAKE_SIGNED_TX = '12345678' * 10
FAKE_PSBT_B64  = 'cHNidP8BAAoAAAAA'  # minimal valid-looking base64

# Version integers
V8_NETINFO  = {'version': 8260200, 'subversion': '/DigiByte:8.26.2/'}
V9_NETINFO  = {'version': 9260000, 'subversion': '/DigiByte:9.26.0/'}
V9RC_NETINFO = {'version': 9260022, 'subversion': '/DigiByte:9.26.0-rc22/'}


# ---------------------------------------------------------------------------
# Helper: reset version cache between tests
# ---------------------------------------------------------------------------

def _reset_cache():
    b._NODE_VERSION_CACHE = None


# ---------------------------------------------------------------------------
# Test 1: Payload validation
# ---------------------------------------------------------------------------

def test_validate_payload_good():
    result = b._validate_payload(GOOD_PAYLOAD)
    assert result == GOOD_PAYLOAD
    print("  PASS: valid 80-byte payload accepted")


def test_validate_payload_short():
    try:
        b._validate_payload('ab' * 79)
        assert False, "Should raise"
    except ValueError as e:
        assert '79' in str(e)
    print("  PASS: 79-byte payload rejected")


def test_validate_payload_long():
    try:
        b._validate_payload('ab' * 81)
        assert False, "Should raise"
    except ValueError as e:
        assert '81' in str(e)
    print("  PASS: 81-byte payload rejected")


def test_validate_payload_bad_hex():
    try:
        b._validate_payload('zz' * 80)
        assert False, "Should raise"
    except ValueError as e:
        assert 'hex' in str(e).lower() or 'Invalid' in str(e)
    print("  PASS: non-hex payload rejected")


def test_validate_payload_strips_whitespace():
    padded = '  ' + GOOD_PAYLOAD + '\n'
    result = b._validate_payload(padded)
    assert result == GOOD_PAYLOAD
    print("  PASS: whitespace stripped from payload")


# ---------------------------------------------------------------------------
# Test 2: Node version detection
# ---------------------------------------------------------------------------

def test_get_node_version_v8():
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V8_NETINFO):
        ver = b.get_node_version(cached=False)
    assert ver == (8, 26, 2), f"Got {ver}"
    print(f"  PASS: v8 version parsed: {ver}")


def test_get_node_version_v9():
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V9_NETINFO):
        ver = b.get_node_version(cached=False)
    assert ver == (9, 26, 0), f"Got {ver}"
    print(f"  PASS: v9 version parsed: {ver}")


def test_get_node_version_cached():
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V9_NETINFO) as mock_rpc:
        b.get_node_version(cached=False)  # populate cache
        b.get_node_version(cached=True)   # should NOT call _rpc again
        b.get_node_version(cached=True)
    # _rpc called exactly once (for getnetworkinfo)
    assert mock_rpc.call_count == 1
    print("  PASS: version result cached after first call")
    _reset_cache()


# ---------------------------------------------------------------------------
# Test 3: Path selection logic
# ---------------------------------------------------------------------------

def test_use_psbt_path_v8():
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V8_NETINFO):
        assert b._use_psbt_path() is False
    print("  PASS: v8.26.2 -> legacy path selected")
    _reset_cache()


def test_use_psbt_path_v9():
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V9_NETINFO):
        assert b._use_psbt_path() is True
    print("  PASS: v9.26.0 -> PSBT path selected")
    _reset_cache()


def test_use_psbt_path_force_legacy(monkeypatch=None):
    _reset_cache()
    orig = b._FORCE_LEGACY
    b._FORCE_LEGACY = True
    try:
        # Even with v9 node, FORCE_LEGACY wins
        with patch.object(b, '_rpc', return_value=V9_NETINFO):
            assert b._use_psbt_path() is False
    finally:
        b._FORCE_LEGACY = orig
    print("  PASS: FORCE_LEGACY overrides v9 node")
    _reset_cache()


def test_use_psbt_path_force_psbt():
    _reset_cache()
    orig_legacy = b._FORCE_LEGACY
    orig_psbt   = b._FORCE_PSBT
    b._FORCE_LEGACY = False
    b._FORCE_PSBT   = True
    try:
        # Even with v8 node, FORCE_PSBT wins
        with patch.object(b, '_rpc', return_value=V8_NETINFO):
            assert b._use_psbt_path() is True
    finally:
        b._FORCE_LEGACY = orig_legacy
        b._FORCE_PSBT   = orig_psbt
    print("  PASS: FORCE_PSBT overrides v8 node")
    _reset_cache()


def test_use_psbt_path_version_error_falls_back():
    """If version detection fails, fall back to legacy (safe)."""
    _reset_cache()
    orig_legacy = b._FORCE_LEGACY
    orig_psbt   = b._FORCE_PSBT
    b._FORCE_LEGACY = False
    b._FORCE_PSBT   = False
    try:
        with patch.object(b, '_rpc', side_effect=ConnectionError("node down")):
            result = b._use_psbt_path()
        assert result is False
    finally:
        b._FORCE_LEGACY = orig_legacy
        b._FORCE_PSBT   = orig_psbt
    print("  PASS: version detection failure -> legacy fallback")
    _reset_cache()


# ---------------------------------------------------------------------------
# Test 4: Legacy broadcast path
# ---------------------------------------------------------------------------

def test_broadcast_legacy_success():
    """Happy path: legacy flow calls correct RPC sequence and returns txid."""
    rpc_responses = {
        'createrawtransaction': FAKE_RAW_TX,
        'fundrawtransaction':   {'hex': FAKE_FUNDED_TX, 'fee': 0.0001},
        'signrawtransactionwithwallet': {'hex': FAKE_SIGNED_TX, 'complete': True},
        'sendrawtransaction':   FAKE_TXID,
    }

    def mock_rpc(method, params=None):
        return rpc_responses[method]

    with patch.object(b, '_rpc', side_effect=mock_rpc) as mock:
        txid = b._broadcast_legacy(GOOD_PAYLOAD)

    assert txid == FAKE_TXID

    # Verify call sequence
    calls = [c[0][0] for c in mock.call_args_list]  # method names
    assert calls == [
        'createrawtransaction',
        'fundrawtransaction',
        'signrawtransactionwithwallet',
        'sendrawtransaction',
    ]
    print(f"  PASS: legacy path RPC sequence correct, txid={txid[:16]}...")


def test_broadcast_legacy_change_type_bech32():
    """fundrawtransaction must include changeType: bech32."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'createrawtransaction':
            return FAKE_RAW_TX
        if method == 'fundrawtransaction':
            captured['fund_opts'] = params[1]
            return {'hex': FAKE_FUNDED_TX, 'fee': 0.0001}
        if method == 'signrawtransactionwithwallet':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_legacy(GOOD_PAYLOAD)

    assert captured['fund_opts']['changeType'] == 'bech32'
    print("  PASS: legacy fundrawtransaction uses changeType=bech32")


def test_broadcast_legacy_signing_incomplete_raises():
    """Incomplete signing must raise RPCError."""
    def mock_rpc(method, params=None):
        if method == 'createrawtransaction':
            return FAKE_RAW_TX
        if method == 'fundrawtransaction':
            return {'hex': FAKE_FUNDED_TX, 'fee': 0.0001}
        if method == 'signrawtransactionwithwallet':
            return {'hex': '', 'complete': False, 'errors': ['missing key']}

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        try:
            b._broadcast_legacy(GOOD_PAYLOAD)
            assert False, "Should raise RPCError"
        except b.RPCError as e:
            assert 'incomplete' in str(e).lower() or 'signing' in str(e).lower()
    print("  PASS: incomplete signing raises RPCError")


def test_broadcast_legacy_maxfeerate_passed():
    """sendrawtransaction must include maxfeerate argument."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'createrawtransaction':
            return FAKE_RAW_TX
        if method == 'fundrawtransaction':
            return {'hex': FAKE_FUNDED_TX, 'fee': 0.0001}
        if method == 'signrawtransactionwithwallet':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            captured['send_params'] = params
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_legacy(GOOD_PAYLOAD)

    assert len(captured['send_params']) == 2
    assert captured['send_params'][1] == b._SEND_MAX_FEERATE
    print(f"  PASS: sendrawtransaction maxfeerate={b._SEND_MAX_FEERATE}")


# ---------------------------------------------------------------------------
# Test 5: PSBT broadcast path
# ---------------------------------------------------------------------------

def test_broadcast_psbt_success():
    """Happy path: PSBT flow calls correct RPC sequence and returns txid."""
    rpc_responses = {
        'walletcreatefundedpsbt': {'psbt': FAKE_PSBT_B64, 'fee': 0.0001},
        'walletprocesspsbt':      {'psbt': FAKE_PSBT_B64 + 'processed', 'complete': True},
        'finalizepsbt':           {'hex': FAKE_SIGNED_TX, 'complete': True},
        'sendrawtransaction':     FAKE_TXID,
    }

    def mock_rpc(method, params=None):
        return rpc_responses[method]

    with patch.object(b, '_rpc', side_effect=mock_rpc) as mock:
        txid = b._broadcast_psbt(GOOD_PAYLOAD)

    assert txid == FAKE_TXID

    calls = [c[0][0] for c in mock.call_args_list]
    assert calls == [
        'walletcreatefundedpsbt',
        'walletprocesspsbt',
        'finalizepsbt',
        'sendrawtransaction',
    ]
    print(f"  PASS: PSBT path RPC sequence correct, txid={txid[:16]}...")


def test_broadcast_psbt_change_type_bech32m():
    """walletcreatefundedpsbt must request bech32m change output."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'walletcreatefundedpsbt':
            captured['psbt_opts'] = params[3]  # options dict is 4th param
            return {'psbt': FAKE_PSBT_B64, 'fee': 0.0001}
        if method == 'walletprocesspsbt':
            return {'psbt': FAKE_PSBT_B64, 'complete': True}
        if method == 'finalizepsbt':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_psbt(GOOD_PAYLOAD)

    assert captured['psbt_opts']['changeType'] == 'bech32m'
    print("  PASS: PSBT walletcreatefundedpsbt uses changeType=bech32m")


def test_broadcast_psbt_fee_rate_param():
    """walletcreatefundedpsbt must use fee_rate (v9.26 param name), not feeRate."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'walletcreatefundedpsbt':
            captured['psbt_opts'] = params[3]
            return {'psbt': FAKE_PSBT_B64, 'fee': 0.0001}
        if method == 'walletprocesspsbt':
            return {'psbt': FAKE_PSBT_B64, 'complete': True}
        if method == 'finalizepsbt':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_psbt(GOOD_PAYLOAD)

    opts = captured['psbt_opts']
    assert 'fee_rate' in opts,   "fee_rate missing (v9.26 param name required)"
    assert 'feeRate' not in opts, "feeRate present (legacy param — breaks v9.26)"
    print(f"  PASS: PSBT uses fee_rate={opts['fee_rate']} sats/vB (v9.26 param)")


def test_broadcast_psbt_finalize_incomplete_raises():
    """finalizepsbt returning complete=False must raise RPCError."""
    def mock_rpc(method, params=None):
        if method == 'walletcreatefundedpsbt':
            return {'psbt': FAKE_PSBT_B64, 'fee': 0.0001}
        if method == 'walletprocesspsbt':
            return {'psbt': FAKE_PSBT_B64, 'complete': False}
        if method == 'finalizepsbt':
            return {'psbt': FAKE_PSBT_B64, 'complete': False}  # not finalized

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        try:
            b._broadcast_psbt(GOOD_PAYLOAD)
            assert False, "Should raise RPCError"
        except b.RPCError as e:
            assert 'incomplete' in str(e).lower() or 'finali' in str(e).lower()
    print("  PASS: PSBT finalization failure raises RPCError")


def test_broadcast_psbt_maxfeerate_passed():
    """sendrawtransaction in PSBT path must include maxfeerate."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'walletcreatefundedpsbt':
            return {'psbt': FAKE_PSBT_B64, 'fee': 0.0001}
        if method == 'walletprocesspsbt':
            return {'psbt': FAKE_PSBT_B64, 'complete': True}
        if method == 'finalizepsbt':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            captured['send_params'] = params
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_psbt(GOOD_PAYLOAD)

    assert len(captured['send_params']) == 2
    assert captured['send_params'][1] == b._SEND_MAX_FEERATE
    print(f"  PASS: PSBT sendrawtransaction maxfeerate={b._SEND_MAX_FEERATE}")


# ---------------------------------------------------------------------------
# Test 6: broadcast_op_return routes correctly
# ---------------------------------------------------------------------------

def test_broadcast_op_return_routes_legacy_on_v8():
    """broadcast_op_return must call _broadcast_legacy on v8 node."""
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V8_NETINFO):
        with patch.object(b, '_broadcast_legacy', return_value=FAKE_TXID) as leg:
            with patch.object(b, '_broadcast_psbt', return_value=FAKE_TXID) as psbt:
                txid = b.broadcast_op_return(GOOD_PAYLOAD)

    assert txid == FAKE_TXID
    leg.assert_called_once()
    psbt.assert_not_called()
    print("  PASS: v8 node -> _broadcast_legacy called")
    _reset_cache()


def test_broadcast_op_return_routes_psbt_on_v9():
    """broadcast_op_return must call _broadcast_psbt on v9 node."""
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V9_NETINFO):
        with patch.object(b, '_broadcast_legacy', return_value=FAKE_TXID) as leg:
            with patch.object(b, '_broadcast_psbt', return_value=FAKE_TXID) as psbt:
                txid = b.broadcast_op_return(GOOD_PAYLOAD)

    assert txid == FAKE_TXID
    psbt.assert_called_once()
    leg.assert_not_called()
    print("  PASS: v9 node -> _broadcast_psbt called")
    _reset_cache()


def test_broadcast_op_return_validates_before_routing():
    """Payload validation must happen before any RPC call."""
    _reset_cache()
    with patch.object(b, '_rpc', return_value=V8_NETINFO):
        with patch.object(b, '_broadcast_legacy') as leg:
            try:
                b.broadcast_op_return('tooshort')
                assert False
            except ValueError:
                pass
            leg.assert_not_called()
    print("  PASS: validation fires before routing")
    _reset_cache()


# ---------------------------------------------------------------------------
# Test 7: get_new_address
# ---------------------------------------------------------------------------

def test_get_new_address_default_bech32m():
    """Default address type must be bech32m."""
    with patch.object(b, '_rpc', return_value='dgb1ptest') as mock:
        addr = b.get_new_address()
    mock.assert_called_once_with('getnewaddress', ['giving-engine', 'bech32m'])
    assert addr == 'dgb1ptest'
    print("  PASS: get_new_address defaults to bech32m")


def test_get_new_address_bech32m_fallback_on_v8():
    """bech32m failure on v8 must fall back to bech32 gracefully."""
    call_count = [0]

    def mock_rpc(method, params=None):
        call_count[0] += 1
        if params and params[1] == 'bech32m':
            raise b.RPCError(-8, 'Unknown address type')
        return 'dgb1qfallback'

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        addr = b.get_new_address()

    assert addr == 'dgb1qfallback'
    assert call_count[0] == 2  # first bech32m attempt, then bech32 fallback
    print("  PASS: bech32m -> bech32 fallback on v8 RPCError -8")


def test_get_new_address_non_type_error_propagates():
    """Non-address-type RPC errors must propagate, not be swallowed."""
    with patch.object(b, '_rpc', side_effect=b.RPCError(-4, 'Wallet locked')):
        try:
            b.get_new_address()
            assert False
        except b.RPCError as e:
            assert e.code == -4
    print("  PASS: non-type RPCError propagates from get_new_address")


# ---------------------------------------------------------------------------
# Test 8: health_check wallet validation
# ---------------------------------------------------------------------------

def test_health_check_descriptor_wallet_v9_ok():
    """Descriptor wallet on v9 -> health_check returns True."""
    _reset_cache()

    def mock_rpc(method, params=None):
        if method == 'getnetworkinfo':
            return V9_NETINFO
        if method == 'getblockchaininfo':
            return {'chain': 'main', 'blocks': 100000}
        if method == 'getbalance':
            return 42.0
        if method == 'getwalletinfo':
            return {'walletname': 'taproot-wallet', 'descriptors': True}

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        result = b.health_check()

    assert result is True
    print("  PASS: descriptor wallet + v9 -> health_check OK")
    _reset_cache()


def test_health_check_legacy_wallet_v9_fails():
    """Legacy wallet on v9 -> health_check returns False (Taproot requires descriptor)."""
    _reset_cache()

    def mock_rpc(method, params=None):
        if method == 'getnetworkinfo':
            return V9_NETINFO
        if method == 'getblockchaininfo':
            return {'chain': 'main', 'blocks': 100000}
        if method == 'getbalance':
            return 42.0
        if method == 'getwalletinfo':
            return {'walletname': 'legacy-wallet', 'descriptors': False}

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        result = b.health_check()

    assert result is False
    print("  PASS: legacy wallet + v9 -> health_check FAIL (correct)")
    _reset_cache()


def test_health_check_legacy_wallet_v8_warns_not_fails():
    """Legacy wallet on v8 -> health_check returns True (advisory warning only)."""
    _reset_cache()

    def mock_rpc(method, params=None):
        if method == 'getnetworkinfo':
            return V8_NETINFO
        if method == 'getblockchaininfo':
            return {'chain': 'main', 'blocks': 99000}
        if method == 'getbalance':
            return 10.0
        if method == 'getwalletinfo':
            return {'walletname': 'old-wallet', 'descriptors': False}

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        result = b.health_check()

    assert result is True
    print("  PASS: legacy wallet + v8 -> health_check OK (warning only)")
    _reset_cache()


# ---------------------------------------------------------------------------
# Test 9: JSON-RPC version is 2.0
# ---------------------------------------------------------------------------

def test_rpc_uses_jsonrpc_2_0():
    """All RPC calls must use jsonrpc: 2.0."""
    import json
    import urllib.request

    captured_payload = {}

    class FakeResponse:
        def read(self):
            return json.dumps({'result': 'ok', 'error': None, 'id': 'profit-emitter'}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, timeout=None):
        captured_payload['body'] = json.loads(req.data.decode())
        return FakeResponse()

    with patch('urllib.request.urlopen', side_effect=fake_urlopen):
        b._rpc('getblockchaininfo')

    assert captured_payload['body']['jsonrpc'] == '2.0'
    print("  PASS: JSON-RPC version is 2.0")


# ---------------------------------------------------------------------------
# Test 10: OP_RETURN data key in createrawtransaction
# ---------------------------------------------------------------------------

def test_legacy_op_return_data_key():
    """createrawtransaction must use 'data' key for OP_RETURN output."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'createrawtransaction':
            captured['outputs'] = params[1]
            return FAKE_RAW_TX
        if method == 'fundrawtransaction':
            return {'hex': FAKE_FUNDED_TX, 'fee': 0.0001}
        if method == 'signrawtransactionwithwallet':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_legacy(GOOD_PAYLOAD)

    assert len(captured['outputs']) == 1
    assert 'data' in captured['outputs'][0]
    assert captured['outputs'][0]['data'] == GOOD_PAYLOAD
    print("  PASS: createrawtransaction uses 'data' key for OP_RETURN")


def test_psbt_op_return_data_key():
    """walletcreatefundedpsbt must use 'data' key for OP_RETURN output."""
    captured = {}

    def mock_rpc(method, params=None):
        if method == 'walletcreatefundedpsbt':
            captured['outputs'] = params[1]
            return {'psbt': FAKE_PSBT_B64, 'fee': 0.0001}
        if method == 'walletprocesspsbt':
            return {'psbt': FAKE_PSBT_B64, 'complete': True}
        if method == 'finalizepsbt':
            return {'hex': FAKE_SIGNED_TX, 'complete': True}
        if method == 'sendrawtransaction':
            return FAKE_TXID

    with patch.object(b, '_rpc', side_effect=mock_rpc):
        b._broadcast_psbt(GOOD_PAYLOAD)

    assert len(captured['outputs']) == 1
    assert 'data' in captured['outputs'][0]
    assert captured['outputs'][0]['data'] == GOOD_PAYLOAD
    print("  PASS: walletcreatefundedpsbt uses 'data' key for OP_RETURN")


# ---------------------------------------------------------------------------
# Test 11: Explicit path overrides
# ---------------------------------------------------------------------------

def test_broadcast_op_return_psbt_explicit():
    """broadcast_op_return_psbt always calls _broadcast_psbt."""
    with patch.object(b, '_broadcast_psbt', return_value=FAKE_TXID) as psbt:
        with patch.object(b, '_broadcast_legacy', return_value=FAKE_TXID) as leg:
            txid = b.broadcast_op_return_psbt(GOOD_PAYLOAD)
    psbt.assert_called_once()
    leg.assert_not_called()
    assert txid == FAKE_TXID
    print("  PASS: broadcast_op_return_psbt always uses PSBT path")


def test_broadcast_op_return_legacy_explicit():
    """broadcast_op_return_legacy always calls _broadcast_legacy."""
    with patch.object(b, '_broadcast_legacy', return_value=FAKE_TXID) as leg:
        with patch.object(b, '_broadcast_psbt', return_value=FAKE_TXID) as psbt:
            txid = b.broadcast_op_return_legacy(GOOD_PAYLOAD)
    leg.assert_called_once()
    psbt.assert_not_called()
    assert txid == FAKE_TXID
    print("  PASS: broadcast_op_return_legacy always uses legacy path")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    # Payload validation
    test_validate_payload_good,
    test_validate_payload_short,
    test_validate_payload_long,
    test_validate_payload_bad_hex,
    test_validate_payload_strips_whitespace,
    # Version detection
    test_get_node_version_v8,
    test_get_node_version_v9,
    test_get_node_version_cached,
    # Path selection
    test_use_psbt_path_v8,
    test_use_psbt_path_v9,
    test_use_psbt_path_force_legacy,
    test_use_psbt_path_force_psbt,
    test_use_psbt_path_version_error_falls_back,
    # Legacy path
    test_broadcast_legacy_success,
    test_broadcast_legacy_change_type_bech32,
    test_broadcast_legacy_signing_incomplete_raises,
    test_broadcast_legacy_maxfeerate_passed,
    # PSBT path
    test_broadcast_psbt_success,
    test_broadcast_psbt_change_type_bech32m,
    test_broadcast_psbt_fee_rate_param,
    test_broadcast_psbt_finalize_incomplete_raises,
    test_broadcast_psbt_maxfeerate_passed,
    # Routing
    test_broadcast_op_return_routes_legacy_on_v8,
    test_broadcast_op_return_routes_psbt_on_v9,
    test_broadcast_op_return_validates_before_routing,
    # Address generation
    test_get_new_address_default_bech32m,
    test_get_new_address_bech32m_fallback_on_v8,
    test_get_new_address_non_type_error_propagates,
    # Health check
    test_health_check_descriptor_wallet_v9_ok,
    test_health_check_legacy_wallet_v9_fails,
    test_health_check_legacy_wallet_v8_warns_not_fails,
    # Protocol
    test_rpc_uses_jsonrpc_2_0,
    # OP_RETURN data key
    test_legacy_op_return_data_key,
    test_psbt_op_return_data_key,
    # Explicit overrides
    test_broadcast_op_return_psbt_explicit,
    test_broadcast_op_return_legacy_explicit,
]


if __name__ == '__main__':
    print("=" * 60)
    print("dgb_broadcaster.py — Unit Test Suite")
    print("Perpetual Giving Engine / Kryllax / Kael")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    errors = []

    for test_fn in TESTS:
        name = test_fn.__name__
        print(f"[{passed + failed + 1:02d}] {name}")
        try:
            test_fn()
            passed += 1
        except Exception as e:
            import traceback
            failed += 1
            errors.append((name, str(e), traceback.format_exc()))
            print(f"  FAIL: {e}")
        print()

    print("=" * 60)
    print(f"Results: {passed}/{len(TESTS)} passed, {failed} failed")
    if errors:
        print()
        print("FAILURES:")
        for name, msg, tb in errors:
            print(f"  {name}: {msg}")
            print(tb)
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
