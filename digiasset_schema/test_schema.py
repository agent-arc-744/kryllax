"""
test_schema.py
==============
Comprehensive test suite for DigiAsset 80-byte OP_RETURN metadata schema.
Perpetual Giving Engine — Kryllax / Kael

Runs with: python -m pytest test_schema.py -v
Or:        python test_schema.py
"""

import sys
import os
import hashlib
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import (
    GivingEngineMetadata,
    MAGIC, SCHEMA_VERSION, TOTAL_BYTES, STRUCT_FMT,
    DONATION_TYPE_DIRECT, DONATION_TYPE_CDP, DONATION_TYPE_RECURRING,
    ASSET_CLASS_GIVING, ASSET_CLASS_IDENTITY, ASSET_CLASS_RECEIPT,
    DGB_P2PKH_VERSION, DGB_P2SH_VERSION,
    derive_donor_id, make_sphincs_commitment, make_sphincs_placeholder,
    verify_sphincs_commitment, encode_flags, decode_flags,
    dgb_address_to_hash160, _base58_decode, _base58check_decode,
    BASE58_ALPHABET,
)


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_valid_dgb_address(hash160: bytes = None, version: int = DGB_P2PKH_VERSION) -> str:
    """
    Construct a valid Base58Check DGB address from a hash160.
    Used to generate deterministic test addresses without needing a live wallet.
    """
    if hash160 is None:
        hash160 = bytes(range(20))  # deterministic 20 bytes
    payload = bytes([version]) + hash160
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    raw = payload + checksum
    # Base58 encode
    n = int.from_bytes(raw, 'big')
    result = []
    while n > 0:
        n, rem = divmod(n, 58)
        result.append(BASE58_ALPHABET[rem:rem+1])
    # Leading zero bytes -> leading '1' chars (count LEADING zeros only)
    pad = 0
    for b in raw:
        if b == 0:
            pad += 1
        else:
            break
    result.extend([BASE58_ALPHABET[0:1]] * pad)
    return b''.join(reversed(result)).decode('ascii')


# Shared test fixtures
DONOR_ADDR   = _make_valid_dgb_address(bytes(range(20)), DGB_P2PKH_VERSION)
TARGET_ADDR  = _make_valid_dgb_address(bytes(range(1, 21)), DGB_P2PKH_VERSION)
PROFIT_TXHASH = 'a' * 64   # 32 bytes of 0xAA
AMOUNT_SAT   = 100_000_000  # 1.0 DGB
FAKE_SPHINCS = b'SPHINCS_FULL_SIG_PLACEHOLDER_DATA_8080_BYTES' * 184  # ~8KB


# ---------------------------------------------------------------------------
# Test 1: Constants sanity
# ---------------------------------------------------------------------------

def test_constants():
    """Verify magic bytes, version, struct format, and total byte count."""
    assert MAGIC == bytes([0x4B, 0x41]), f"Magic wrong: {MAGIC.hex()}"
    assert MAGIC == b'KA'
    assert SCHEMA_VERSION == 1
    assert TOTAL_BYTES == 80
    assert struct.calcsize(STRUCT_FMT) == 80, (
        f"Struct size: {struct.calcsize(STRUCT_FMT)}"
    )
    print("  PASS: constants")


# ---------------------------------------------------------------------------
# Test 2: Byte layout verification
# ---------------------------------------------------------------------------

def test_byte_layout():
    """Verify each field occupies the correct byte offsets."""
    # Build a known payload
    magic        = b'KA'
    version      = bytes([0x01])
    flags        = bytes([0x00])
    donor_id     = bytes(range(8))
    profit_src   = bytes(range(16))
    donate_tgt   = bytes(range(20))
    amount       = (999).to_bytes(8, 'little')
    sphincs      = bytes(range(24))

    raw = magic + version + flags + donor_id + profit_src + donate_tgt + amount + sphincs
    assert len(raw) == 80, f"Manual layout: {len(raw)} bytes"

    # Verify offsets
    assert raw[0:2]   == b'KA'
    assert raw[2]     == 0x01
    assert raw[3]     == 0x00
    assert raw[4:12]  == donor_id
    assert raw[12:28] == profit_src
    assert raw[28:48] == donate_tgt
    assert raw[48:56] == amount
    assert raw[56:80] == sphincs
    print("  PASS: byte layout offsets")


# ---------------------------------------------------------------------------
# Test 3: Encode produces exactly 80 bytes
# ---------------------------------------------------------------------------

def test_encode_length():
    """Encoded output must be exactly 80 bytes."""
    meta = GivingEngineMetadata(
        donor_id        = bytes(8),
        profit_source   = bytes(16),
        donation_target = bytes(20),
        amount_satoshis = 0,
    )
    encoded = meta.encode()
    assert len(encoded) == 80, f"Encoded length: {len(encoded)}"
    print(f"  PASS: encode length = {len(encoded)} bytes")


# ---------------------------------------------------------------------------
# Test 4: Encode/decode roundtrip (raw bytes)
# ---------------------------------------------------------------------------

def test_roundtrip_raw():
    """Encode then decode must produce identical field values."""
    donor_id        = hashlib.blake2b(b'test_donor', digest_size=8).digest()
    profit_source   = bytes.fromhex('deadbeef' * 4)
    donation_target = bytes.fromhex('cafebabe' * 5)
    amount_satoshis = 250_000_000  # 2.5 DGB
    sphincs_commit  = hashlib.sha256(b'fake_sig').digest()[:24]

    original = GivingEngineMetadata(
        donor_id        = donor_id,
        profit_source   = profit_source,
        donation_target = donation_target,
        amount_satoshis = amount_satoshis,
        sphincs_commit  = sphincs_commit,
        donation_type   = DONATION_TYPE_CDP,
        asset_class     = ASSET_CLASS_RECEIPT,
    )

    encoded = original.encode()
    decoded = GivingEngineMetadata.decode(encoded)

    assert decoded.donor_id        == donor_id
    assert decoded.profit_source   == profit_source
    assert decoded.donation_target == donation_target
    assert decoded.amount_satoshis == amount_satoshis
    assert decoded.sphincs_commit  == sphincs_commit
    assert decoded.donation_type   == DONATION_TYPE_CDP
    assert decoded.asset_class     == ASSET_CLASS_RECEIPT
    print("  PASS: encode/decode roundtrip (raw)")


# ---------------------------------------------------------------------------
# Test 5: Hex roundtrip
# ---------------------------------------------------------------------------

def test_roundtrip_hex():
    """encode_hex / decode_hex roundtrip."""
    meta = GivingEngineMetadata(
        donor_id        = bytes(range(8)),
        profit_source   = bytes(range(16)),
        donation_target = bytes(range(20)),
        amount_satoshis = 1_000_000,
    )
    hex_str = meta.encode_hex()
    assert len(hex_str) == 160, f"Hex length: {len(hex_str)} (expected 160)"
    decoded = GivingEngineMetadata.decode_hex(hex_str)
    assert decoded.amount_satoshis == 1_000_000
    assert decoded.donor_id == bytes(range(8))
    print(f"  PASS: hex roundtrip, hex={hex_str[:32]}...")


# ---------------------------------------------------------------------------
# Test 6: from_addresses constructor
# ---------------------------------------------------------------------------

def test_from_addresses():
    """from_addresses must correctly derive all fields from human-readable inputs."""
    meta = GivingEngineMetadata.from_addresses(
        donor_address   = DONOR_ADDR,
        profit_tx_hash  = PROFIT_TXHASH,
        target_address  = TARGET_ADDR,
        amount_satoshis = AMOUNT_SAT,
    )
    # Verify donor_id derivation
    expected_donor_id = derive_donor_id(DONOR_ADDR)
    assert meta.donor_id == expected_donor_id, (
        f"donor_id mismatch: {meta.donor_id.hex()} != {expected_donor_id.hex()}"
    )
    # Verify profit_source (first 16 bytes of tx hash)
    expected_profit = bytes.fromhex(PROFIT_TXHASH)[:16]
    assert meta.profit_source == expected_profit
    # Verify donation_target (hash160 of target address)
    expected_target = dgb_address_to_hash160(TARGET_ADDR)
    assert meta.donation_target == expected_target
    # Verify amount
    assert meta.amount_satoshis == AMOUNT_SAT
    # Verify sphincs placeholder (no sig provided)
    assert meta.sphincs_commit == bytes(24)
    # Verify encode still produces 80 bytes
    assert len(meta.encode()) == 80
    print(f"  PASS: from_addresses constructor")
    print(f"         donor_id={meta.donor_id.hex()}")
    print(f"         profit_source={meta.profit_source.hex()}")
    print(f"         donation_target={meta.donation_target.hex()}")


# ---------------------------------------------------------------------------
# Test 7: from_addresses with SPHINCS+ commitment
# ---------------------------------------------------------------------------

def test_from_addresses_with_sphincs():
    """SPHINCS+ commitment must be SHA256(full_sig)[:24]."""
    meta = GivingEngineMetadata.from_addresses(
        donor_address   = DONOR_ADDR,
        profit_tx_hash  = PROFIT_TXHASH,
        target_address  = TARGET_ADDR,
        amount_satoshis = AMOUNT_SAT,
        sphincs_full_sig = FAKE_SPHINCS,
    )
    expected_commit = hashlib.sha256(FAKE_SPHINCS).digest()[:24]
    assert meta.sphincs_commit == expected_commit
    assert len(meta.sphincs_commit) == 24
    # Verify commitment verification function
    assert verify_sphincs_commitment(FAKE_SPHINCS, meta.sphincs_commit)
    assert not verify_sphincs_commitment(b'wrong_sig', meta.sphincs_commit)
    print(f"  PASS: SPHINCS+ commitment = {meta.sphincs_commit.hex()}")


# ---------------------------------------------------------------------------
# Test 8: Flags encoding/decoding — all combinations
# ---------------------------------------------------------------------------

def test_flags_all_combinations():
    """All donation_type x asset_class combinations must roundtrip through flags byte."""
    for dtype in (0, 1, 2, 3):
        for aclass in (0, 1, 2, 3):
            flags = encode_flags(dtype, aclass)
            decoded = decode_flags(flags)
            assert decoded['donation_type'] == dtype, (
                f"dtype={dtype} aclass={aclass}: got {decoded['donation_type']}"
            )
            assert decoded['asset_class'] == aclass, (
                f"dtype={dtype} aclass={aclass}: got {decoded['asset_class']}"
            )
            assert decoded['reserved'] == 0
    print("  PASS: flags all 16 combinations")


# ---------------------------------------------------------------------------
# Test 9: Flags survive encode/decode roundtrip
# ---------------------------------------------------------------------------

def test_flags_roundtrip():
    """donation_type and asset_class must survive full encode/decode cycle."""
    for dtype in (DONATION_TYPE_DIRECT, DONATION_TYPE_CDP, DONATION_TYPE_RECURRING):
        for aclass in (ASSET_CLASS_GIVING, ASSET_CLASS_IDENTITY, ASSET_CLASS_RECEIPT):
            meta = GivingEngineMetadata(
                donor_id        = bytes(8),
                profit_source   = bytes(16),
                donation_target = bytes(20),
                amount_satoshis = 1,
                donation_type   = dtype,
                asset_class     = aclass,
            )
            decoded = GivingEngineMetadata.decode(meta.encode())
            assert decoded.donation_type == dtype
            assert decoded.asset_class   == aclass
    print("  PASS: flags roundtrip through encode/decode")


# ---------------------------------------------------------------------------
# Test 10: Amount boundary values
# ---------------------------------------------------------------------------

def test_amount_boundaries():
    """Amount field must handle 0, 1, max uint64."""
    for amount in (0, 1, 100_000_000, 21_000_000 * 100_000_000, 0xFFFFFFFFFFFFFFFF):
        meta = GivingEngineMetadata(
            donor_id        = bytes(8),
            profit_source   = bytes(16),
            donation_target = bytes(20),
            amount_satoshis = amount,
        )
        decoded = GivingEngineMetadata.decode(meta.encode())
        assert decoded.amount_satoshis == amount, (
            f"Amount {amount} failed roundtrip: got {decoded.amount_satoshis}"
        )
    print("  PASS: amount boundary values (0, 1, 1 DGB, 21M DGB, max uint64)")


# ---------------------------------------------------------------------------
# Test 11: Donor ID determinism
# ---------------------------------------------------------------------------

def test_donor_id_determinism():
    """Same address must always produce same donor_id."""
    id1 = derive_donor_id(DONOR_ADDR)
    id2 = derive_donor_id(DONOR_ADDR)
    assert id1 == id2
    assert len(id1) == 8
    # Different addresses must produce different IDs
    id3 = derive_donor_id(TARGET_ADDR)
    assert id1 != id3
    print(f"  PASS: donor_id determinism, id={id1.hex()}")


# ---------------------------------------------------------------------------
# Test 12: Magic byte validation on decode
# ---------------------------------------------------------------------------

def test_bad_magic_rejected():
    """Decode must reject payloads with wrong magic bytes."""
    meta = GivingEngineMetadata(
        donor_id        = bytes(8),
        profit_source   = bytes(16),
        donation_target = bytes(20),
        amount_satoshis = 0,
    )
    encoded = bytearray(meta.encode())
    encoded[0] = 0xFF  # corrupt magic
    encoded[1] = 0xFF
    try:
        GivingEngineMetadata.decode(bytes(encoded))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'Magic' in str(e) or 'magic' in str(e)
    print("  PASS: bad magic rejected")


# ---------------------------------------------------------------------------
# Test 13: Wrong length rejected
# ---------------------------------------------------------------------------

def test_wrong_length_rejected():
    """Decode must reject payloads that are not exactly 80 bytes."""
    for bad_len in (0, 1, 79, 81, 100, 160):
        try:
            GivingEngineMetadata.decode(bytes(bad_len))
            assert False, f"Should have raised ValueError for length {bad_len}"
        except ValueError as e:
            assert str(bad_len) in str(e) or 'bytes' in str(e).lower()
    print("  PASS: wrong lengths rejected (0, 1, 79, 81, 100, 160)")


# ---------------------------------------------------------------------------
# Test 14: Validation errors on construction
# ---------------------------------------------------------------------------

def test_construction_validation():
    """GivingEngineMetadata must reject invalid field lengths."""
    base = dict(
        donor_id        = bytes(8),
        profit_source   = bytes(16),
        donation_target = bytes(20),
        amount_satoshis = 0,
    )
    # Bad donor_id length
    try:
        GivingEngineMetadata(**{**base, 'donor_id': bytes(7)})
        assert False
    except ValueError:
        pass
    # Bad profit_source length
    try:
        GivingEngineMetadata(**{**base, 'profit_source': bytes(15)})
        assert False
    except ValueError:
        pass
    # Bad donation_target length
    try:
        GivingEngineMetadata(**{**base, 'donation_target': bytes(19)})
        assert False
    except ValueError:
        pass
    # Bad sphincs_commit length
    try:
        GivingEngineMetadata(**{**base, 'sphincs_commit': bytes(23)})
        assert False
    except ValueError:
        pass
    print("  PASS: construction validation errors")


# ---------------------------------------------------------------------------
# Test 15: Base58Check address validation
# ---------------------------------------------------------------------------

def test_base58check_valid_address():
    """Valid DGB addresses must decode to 20-byte hash160."""
    h160 = dgb_address_to_hash160(DONOR_ADDR)
    assert len(h160) == 20
    # Verify it matches what we put in
    expected = bytes(range(20))
    assert h160 == expected, f"hash160 mismatch: {h160.hex()} != {expected.hex()}"
    print(f"  PASS: base58check decode, hash160={h160.hex()}")


def test_base58check_bad_checksum():
    """Corrupted address checksum must be rejected."""
    # Flip last char of address
    bad_addr = DONOR_ADDR[:-1] + ('2' if DONOR_ADDR[-1] != '2' else '3')
    try:
        dgb_address_to_hash160(bad_addr)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  PASS: bad checksum rejected")


# ---------------------------------------------------------------------------
# Test 16: SPHINCS+ placeholder
# ---------------------------------------------------------------------------

def test_sphincs_placeholder():
    """Default sphincs_commit must be 24 zero bytes."""
    placeholder = make_sphincs_placeholder()
    assert placeholder == bytes(24)
    assert len(placeholder) == 24
    # Placeholder must NOT verify against any real signature
    assert not verify_sphincs_commitment(b'any_sig', placeholder)
    print("  PASS: SPHINCS+ placeholder = 24 zero bytes")


# ---------------------------------------------------------------------------
# Test 17: Summary output
# ---------------------------------------------------------------------------

def test_summary_output():
    """summary() must return a non-empty string containing key field names."""
    meta = GivingEngineMetadata.from_addresses(
        donor_address   = DONOR_ADDR,
        profit_tx_hash  = PROFIT_TXHASH,
        target_address  = TARGET_ADDR,
        amount_satoshis = AMOUNT_SAT,
    )
    s = meta.summary()
    assert 'KA' in s
    assert 'donor_id' in s
    assert 'profit_source' in s
    assert 'donation_target' in s
    assert 'amount' in s
    assert 'sphincs_commit' in s
    assert '80 bytes' in s
    print("  PASS: summary output contains all field names")
    print()
    print(s)


# ---------------------------------------------------------------------------
# Test 18: Full pipeline simulation
# ---------------------------------------------------------------------------

def test_full_pipeline():
    """
    Simulate the full Perpetual Giving Engine pipeline:
    1. Loop-bot generates a trade tx hash
    2. Donor address identified
    3. Target charitable address set
    4. SPHINCS+ signature generated (simulated)
    5. Metadata encoded to 80 bytes
    6. Decoded and verified at the other end
    """
    # Step 1: Loop-bot trade tx hash (simulated KuCoin trade)
    loop_bot_tx = hashlib.sha256(b'KUCOIN:DGB/USDT:BUY:2026-02-22T01:59:22').hexdigest()

    # Step 2: Donor
    donor_dgb_addr = DONOR_ADDR

    # Step 3: Charitable target
    target_dgb_addr = TARGET_ADDR

    # Step 4: SPHINCS+ sig (simulated — real sig would be 8,080 bytes)
    simulated_sphincs_sig = hashlib.sha256(b'SPHINCS_PRIVATE_KEY_SIGN:' + loop_bot_tx.encode()).digest() * 253  # ~8KB

    # Step 5: Encode
    meta = GivingEngineMetadata.from_addresses(
        donor_address    = donor_dgb_addr,
        profit_tx_hash   = loop_bot_tx,
        target_address   = target_dgb_addr,
        amount_satoshis  = 50_000_000,  # 0.5 DGB
        sphincs_full_sig = simulated_sphincs_sig,
        donation_type    = DONATION_TYPE_CDP,
        asset_class      = ASSET_CLASS_GIVING,
    )
    encoded = meta.encode()
    assert len(encoded) == 80

    # Step 6: Decode and verify
    decoded = GivingEngineMetadata.decode(encoded)
    assert decoded.amount_satoshis == 50_000_000
    assert decoded.donation_type   == DONATION_TYPE_CDP
    assert decoded.asset_class     == ASSET_CLASS_GIVING
    assert verify_sphincs_commitment(simulated_sphincs_sig, decoded.sphincs_commit)

    print("  PASS: full pipeline simulation")
    print(f"         loop_bot_tx={loop_bot_tx[:32]}...")
    print(f"         encoded={encoded.hex()[:40]}...")
    print(f"         amount=0.5 DGB, type=CDP, class=GIVING")
    print(f"         SPHINCS+ commitment verified: OK")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

TESTS = [
    test_constants,
    test_byte_layout,
    test_encode_length,
    test_roundtrip_raw,
    test_roundtrip_hex,
    test_from_addresses,
    test_from_addresses_with_sphincs,
    test_flags_all_combinations,
    test_flags_roundtrip,
    test_amount_boundaries,
    test_donor_id_determinism,
    test_bad_magic_rejected,
    test_wrong_length_rejected,
    test_construction_validation,
    test_base58check_valid_address,
    test_base58check_bad_checksum,
    test_sphincs_placeholder,
    test_summary_output,
    test_full_pipeline,
]


if __name__ == '__main__':
    print("=" * 60)
    print("DigiAsset 80-byte Schema — Test Suite")
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
