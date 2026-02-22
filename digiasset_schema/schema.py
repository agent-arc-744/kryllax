"""
digiasset_schema.py
====================
DigiAsset 80-byte OP_RETURN Metadata Schema
Perpetual Giving Engine — Kryllax / Kael

Byte Layout (80 bytes total):
  [0:2]   Magic bytes       0x4B41 ('KA') — Kryllax/Kael identifier
  [2]     Schema version    0x01
  [3]     Flags             donation_type[2] | asset_class[2] | reserved[4]
  [4:12]  Donor ID          8 bytes — BLAKE2b-64 of donor DGB address
  [12:28] Profit source     16 bytes — first 16 bytes of loop-bot tx hash
  [28:48] Donation target   20 bytes — P2PKH hash160 of target DGB address
  [48:56] Amount            8 bytes — uint64 little-endian, satoshis
  [56:80] SPHINCS+ commit   24 bytes — SHA256[:24] of off-chain SPHINCS+ sig

Total: 2+1+1+8+16+20+8+24 = 80 bytes

SPHINCS+ Note:
  Full SPHINCS+-SHA256-128s signatures are 8,080 bytes — cannot fit on-chain.
  This field stores a 24-byte SHA256 commitment to the full off-chain signature.
  The full signature must be stored off-chain (IPFS, local DB, or VPS storage).
  Verification: SHA256(full_sig)[:24] == on_chain_commitment

DigiByte Address Note:
  DGB mainnet P2PKH version byte: 0x1E (addresses start with 'D')
  DGB mainnet P2SH version byte:  0x05 (addresses start with 'S')
"""

import hashlib
import struct
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGIC = bytes([0x4B, 0x41])   # 'KA' — Kryllax/Kael
SCHEMA_VERSION = 0x01
TOTAL_BYTES = 80

# Struct format: little-endian, packed
# 2s = 2 bytes magic
# B  = 1 byte version
# B  = 1 byte flags
# 8s = 8 bytes donor_id
# 16s= 16 bytes profit_source
# 20s= 20 bytes donation_target
# Q  = 8 bytes amount (uint64 LE)
# 24s= 24 bytes sphincs_commit
STRUCT_FMT = '<2sBB8s16s20sQ24s'
assert struct.calcsize(STRUCT_FMT) == TOTAL_BYTES, (
    f"Struct size mismatch: {struct.calcsize(STRUCT_FMT)} != {TOTAL_BYTES}"
)

# Donation type flags (bits 7-6 of flags byte)
DONATION_TYPE_DIRECT    = 0b00  # Direct charitable transfer
DONATION_TYPE_CDP       = 0b01  # CDP-minted DigiDollar deployment
DONATION_TYPE_RECURRING = 0b10  # Recurring engine distribution
DONATION_TYPE_RESERVED  = 0b11

# Asset class flags (bits 5-4 of flags byte)
ASSET_CLASS_GIVING      = 0b00  # Perpetual Giving Engine asset
ASSET_CLASS_IDENTITY    = 0b01  # Donor identity token
ASSET_CLASS_RECEIPT     = 0b10  # Donation receipt
ASSET_CLASS_RESERVED    = 0b11

# DigiByte address version bytes
DGB_P2PKH_VERSION = 0x1E  # Mainnet P2PKH ('D' addresses)
DGB_P2SH_VERSION  = 0x05  # Mainnet P2SH  ('S' addresses)


# ---------------------------------------------------------------------------
# Base58 (stdlib only — no external deps)
# ---------------------------------------------------------------------------

BASE58_ALPHABET = b'123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _base58_decode(s: str) -> bytes:
    """Decode a Base58-encoded string to bytes."""
    n = 0
    for char in s:
        n *= 58
        idx = BASE58_ALPHABET.find(char.encode())
        if idx < 0:
            raise ValueError(f"Invalid Base58 character: {char!r}")
        n += idx
    # Count LEADING '1' chars only (each encodes a leading zero byte)
    pad = 0
    for c in s:
        if c == '1':
            pad += 1
        else:
            break
    # Convert integer to bytes
    result = []
    while n > 0:
        n, rem = divmod(n, 256)
        result.append(rem)
    result.extend([0] * pad)
    return bytes(reversed(result))


def _base58check_decode(address: str) -> tuple:
    """
    Decode a Base58Check address.
    Returns (version_byte: int, hash160: bytes).
    Raises ValueError on checksum failure.
    """
    raw = _base58_decode(address)
    if len(raw) < 5:
        raise ValueError(f"Address too short after decode: {len(raw)} bytes")
    payload, checksum = raw[:-4], raw[-4:]
    computed = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if computed != checksum:
        raise ValueError(
            f"Base58Check checksum failed: "
            f"expected {computed.hex()}, got {checksum.hex()}"
        )
    return payload[0], payload[1:]


def dgb_address_to_hash160(address: str) -> bytes:
    """
    Convert a DigiByte address to its 20-byte hash160.
    Validates checksum and version byte.
    """
    version, hash160 = _base58check_decode(address)
    if version not in (DGB_P2PKH_VERSION, DGB_P2SH_VERSION):
        raise ValueError(
            f"Unknown DGB address version: 0x{version:02X}. "
            f"Expected 0x{DGB_P2PKH_VERSION:02X} (P2PKH) "
            f"or 0x{DGB_P2SH_VERSION:02X} (P2SH)"
        )
    if len(hash160) != 20:
        raise ValueError(f"hash160 must be 20 bytes, got {len(hash160)}")
    return hash160


# ---------------------------------------------------------------------------
# Donor ID derivation
# ---------------------------------------------------------------------------

def derive_donor_id(dgb_address: str) -> bytes:
    """
    Derive an 8-byte donor identifier from a DGB address.
    Uses BLAKE2b with digest_size=8.
    Deterministic and privacy-preserving — full address NOT stored on-chain.
    """
    return hashlib.blake2b(
        dgb_address.encode('utf-8'),
        digest_size=8
    ).digest()


# ---------------------------------------------------------------------------
# SPHINCS+ commitment
# ---------------------------------------------------------------------------

def make_sphincs_commitment(full_signature: bytes) -> bytes:
    """
    Create a 24-byte on-chain commitment to a full SPHINCS+ signature.

    Full SPHINCS+-SHA256-128s signatures are 8,080 bytes — stored off-chain.
    On-chain we store SHA256(full_sig)[:24] as a binding commitment.

    Verification:
        assert hashlib.sha256(stored_full_sig).digest()[:24] == on_chain_commitment
    """
    return hashlib.sha256(full_signature).digest()[:24]


def make_sphincs_placeholder() -> bytes:
    """24-byte zero placeholder — used before signature is generated."""
    return bytes(24)


def verify_sphincs_commitment(full_signature: bytes, commitment: bytes) -> bool:
    """Verify that a full SPHINCS+ signature matches its on-chain commitment."""
    return hashlib.sha256(full_signature).digest()[:24] == commitment


# ---------------------------------------------------------------------------
# Flags byte
# ---------------------------------------------------------------------------

def encode_flags(donation_type: int = DONATION_TYPE_DIRECT,
                 asset_class: int = ASSET_CLASS_GIVING) -> int:
    """
    Encode the flags byte.
    Bits 7-6: donation_type (2 bits)
    Bits 5-4: asset_class   (2 bits)
    Bits 3-0: reserved      (4 bits, zero)
    """
    if donation_type not in (0, 1, 2, 3):
        raise ValueError(f"donation_type must be 0-3, got {donation_type}")
    if asset_class not in (0, 1, 2, 3):
        raise ValueError(f"asset_class must be 0-3, got {asset_class}")
    return ((donation_type & 0x03) << 6) | ((asset_class & 0x03) << 4)


def decode_flags(flags: int) -> dict:
    """Decode the flags byte into component fields."""
    return {
        'donation_type': (flags >> 6) & 0x03,
        'asset_class'  : (flags >> 4) & 0x03,
        'reserved'     : flags & 0x0F,
    }


# ---------------------------------------------------------------------------
# Core dataclass
# ---------------------------------------------------------------------------

@dataclass
class GivingEngineMetadata:
    """
    80-byte DigiAsset OP_RETURN metadata for the Perpetual Giving Engine.

    Fields:
        donor_id        : 8-byte BLAKE2b-64 hash of donor DGB address
        profit_source   : 16-byte prefix of loop-bot trade tx hash
        donation_target : 20-byte hash160 of charitable recipient DGB address
        amount_satoshis : uint64 donation amount in DGB satoshis (1 DGB = 1e8 sat)
        sphincs_commit  : 24-byte SHA256 commitment to off-chain SPHINCS+ signature
        donation_type   : 2-bit flag (0=direct, 1=CDP, 2=recurring)
        asset_class     : 2-bit flag (0=giving, 1=identity, 2=receipt)
    """
    donor_id        : bytes
    profit_source   : bytes
    donation_target : bytes
    amount_satoshis : int
    sphincs_commit  : bytes = field(default_factory=make_sphincs_placeholder)
    donation_type   : int   = DONATION_TYPE_DIRECT
    asset_class     : int   = ASSET_CLASS_GIVING

    def __post_init__(self):
        self._validate()

    def _validate(self):
        if len(self.donor_id) != 8:
            raise ValueError(f"donor_id must be 8 bytes, got {len(self.donor_id)}")
        if len(self.profit_source) != 16:
            raise ValueError(f"profit_source must be 16 bytes, got {len(self.profit_source)}")
        if len(self.donation_target) != 20:
            raise ValueError(f"donation_target must be 20 bytes, got {len(self.donation_target)}")
        if not (0 <= self.amount_satoshis <= 0xFFFFFFFFFFFFFFFF):
            raise ValueError(f"amount_satoshis out of uint64 range")
        if len(self.sphincs_commit) != 24:
            raise ValueError(f"sphincs_commit must be 24 bytes, got {len(self.sphincs_commit)}")
        if self.donation_type not in (0, 1, 2, 3):
            raise ValueError(f"donation_type must be 0-3")
        if self.asset_class not in (0, 1, 2, 3):
            raise ValueError(f"asset_class must be 0-3")

    # ------------------------------------------------------------------
    # Encoding
    # ------------------------------------------------------------------

    def encode(self) -> bytes:
        """Serialize to exactly 80 bytes for OP_RETURN embedding."""
        flags = encode_flags(self.donation_type, self.asset_class)
        packed = struct.pack(
            STRUCT_FMT,
            MAGIC,
            SCHEMA_VERSION,
            flags,
            self.donor_id,
            self.profit_source,
            self.donation_target,
            self.amount_satoshis,
            self.sphincs_commit,
        )
        assert len(packed) == TOTAL_BYTES
        return packed

    def encode_hex(self) -> str:
        """Hex string of encoded bytes (for OP_RETURN script construction)."""
        return self.encode().hex()

    # ------------------------------------------------------------------
    # Decoding
    # ------------------------------------------------------------------

    @classmethod
    def decode(cls, data: bytes) -> 'GivingEngineMetadata':
        """
        Deserialize from 80 bytes.
        Raises ValueError on magic/version mismatch or length error.
        """
        if len(data) != TOTAL_BYTES:
            raise ValueError(f"Expected {TOTAL_BYTES} bytes, got {len(data)}")

        (
            magic, version, flags,
            donor_id, profit_source, donation_target,
            amount_satoshis, sphincs_commit
        ) = struct.unpack(STRUCT_FMT, data)

        if magic != MAGIC:
            raise ValueError(
                f"Magic mismatch: expected {MAGIC.hex()}, got {magic.hex()}"
            )
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"Version mismatch: expected {SCHEMA_VERSION}, got {version}"
            )

        flag_fields = decode_flags(flags)
        return cls(
            donor_id        = donor_id,
            profit_source   = profit_source,
            donation_target = donation_target,
            amount_satoshis = amount_satoshis,
            sphincs_commit  = sphincs_commit,
            donation_type   = flag_fields['donation_type'],
            asset_class     = flag_fields['asset_class'],
        )

    @classmethod
    def decode_hex(cls, hex_str: str) -> 'GivingEngineMetadata':
        """Deserialize from hex string."""
        return cls.decode(bytes.fromhex(hex_str))

    # ------------------------------------------------------------------
    # Convenience constructor
    # ------------------------------------------------------------------

    @classmethod
    def from_addresses(
        cls,
        donor_address    : str,
        profit_tx_hash   : str,
        target_address   : str,
        amount_satoshis  : int,
        sphincs_full_sig : Optional[bytes] = None,
        donation_type    : int = DONATION_TYPE_DIRECT,
        asset_class      : int = ASSET_CLASS_GIVING,
    ) -> 'GivingEngineMetadata':
        """
        Construct from human-readable inputs.

        Args:
            donor_address   : DGB address of the donor
            profit_tx_hash  : Hex string of loop-bot trade tx hash (>= 32 bytes)
            target_address  : DGB address of charitable recipient
            amount_satoshis : Donation amount in satoshis
            sphincs_full_sig: Full SPHINCS+ signature bytes (stored off-chain).
                              If None, placeholder zeros are used.
            donation_type   : Donation type flag
            asset_class     : Asset class flag
        """
        donor_id = derive_donor_id(donor_address)

        tx_bytes = bytes.fromhex(profit_tx_hash)
        if len(tx_bytes) < 16:
            raise ValueError(
                f"profit_tx_hash must decode to >= 16 bytes, got {len(tx_bytes)}"
            )
        profit_source = tx_bytes[:16]

        donation_target = dgb_address_to_hash160(target_address)

        sphincs_commit = (
            make_sphincs_commitment(sphincs_full_sig)
            if sphincs_full_sig is not None
            else make_sphincs_placeholder()
        )

        return cls(
            donor_id        = donor_id,
            profit_source   = profit_source,
            donation_target = donation_target,
            amount_satoshis = amount_satoshis,
            sphincs_commit  = sphincs_commit,
            donation_type   = donation_type,
            asset_class     = asset_class,
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def summary(self) -> str:
        """Human-readable summary of all metadata fields."""
        dtype_names  = ['DIRECT', 'CDP', 'RECURRING', 'RESERVED']
        aclass_names = ['GIVING', 'IDENTITY', 'RECEIPT', 'RESERVED']
        return (
            f"GivingEngineMetadata (80 bytes)\n"
            f"  magic          : {MAGIC.hex().upper()}  ('KA')\n"
            f"  version        : {SCHEMA_VERSION}\n"
            f"  donation_type  : {dtype_names[self.donation_type]}\n"
            f"  asset_class    : {aclass_names[self.asset_class]}\n"
            f"  donor_id       : {self.donor_id.hex()}  (8 bytes)\n"
            f"  profit_source  : {self.profit_source.hex()}  (16 bytes)\n"
            f"  donation_target: {self.donation_target.hex()}  (20 bytes)\n"
            f"  amount         : {self.amount_satoshis} sat "
            f"({self.amount_satoshis / 1e8:.8f} DGB)\n"
            f"  sphincs_commit : {self.sphincs_commit.hex()}  (24 bytes)\n"
            f"  encoded_hex    : {self.encode_hex()}"
        )
