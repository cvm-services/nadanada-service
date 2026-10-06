"""Shared test helpers. Offline only: no browser, no network, no live mint."""
from __future__ import annotations

from coincurve import PrivateKey

#: fixed test keys (never used anywhere real)
SERVER_SK = "22" * 32
OWNER_SK = "11" * 32
STRANGER_SK = "33" * 32


def pub_hex(sk_hex: str) -> str:
    return PrivateKey(bytes.fromhex(sk_hex)).public_key.format(compressed=True)[1:].hex()
