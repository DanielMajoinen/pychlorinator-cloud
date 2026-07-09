"""Helpers for parsing Halo BLE advertisements."""

from __future__ import annotations


MANUFACTURER_ID = 1095  # AstralPool/Fabtronics
ACCESS_CODE_OFFSET = 10
ACCESS_CODE_LENGTH = 4


def access_code_bytes(manufacturer_data: bytes) -> bytes | None:
    """Return the raw access-code bytes from manufacturer data."""
    end = ACCESS_CODE_OFFSET + ACCESS_CODE_LENGTH
    if len(manufacturer_data) < end:
        return None
    return manufacturer_data[ACCESS_CODE_OFFSET:end]


def is_pairable_access_code(access_bytes: bytes | None) -> bool:
    """Return true when access-code bytes indicate a pairable advertisement."""
    if access_bytes is None or len(access_bytes) != ACCESS_CODE_LENGTH:
        return False
    if access_bytes == b"\x00" * ACCESS_CODE_LENGTH:
        return False
    if access_bytes == b"\xff" * ACCESS_CODE_LENGTH:
        return False
    return True
