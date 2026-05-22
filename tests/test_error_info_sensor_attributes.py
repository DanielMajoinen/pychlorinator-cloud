"""Tests for controller error-info parsing and attributes."""

from __future__ import annotations

import struct

from pychlorinator_cloud.error_codes import error_info_attributes
from pychlorinator_cloud.payload_parsers import parse_data_payload
from pychlorinator_cloud.websocket_client import HaloWebSocketClient


def _state_raw(error_info: int) -> bytes:
    payload = bytearray(15)
    payload[4] = 5  # Standby
    struct.pack_into("<H", payload, 13, error_info)
    return bytes([0x03]) + struct.pack("<H", 0x0068) + bytes(payload)


def _parse_error_info(error_info: int):
    client = HaloWebSocketClient("serial", "user", "pass")
    raw = _state_raw(error_info)
    client._update_data(parse_data_payload(raw), raw)
    return client.data


def test_state_parser_populates_707_error_info_details() -> None:
    data = _parse_error_info(707)

    assert data.error_message == "Dosing Disabled"
    assert data.error_severity == "Information"
    assert data.error_category == "Acid"
    assert (
        data.error_reason == "Disabled by the user, or disabled by the user for time."
    )
    assert data.error_action == "Please enable acid dosing"
    assert error_info_attributes(data) == {
        "severity": "Information",
        "category": "Acid",
        "reason": "Disabled by the user, or disabled by the user for time.",
        "recommended_action": "Please enable acid dosing",
        "raw_code": 707,
    }


def test_state_parser_error_info_zero_clears_secondary_fields() -> None:
    data = _parse_error_info(0)

    assert data.error_message == "NoError"
    assert error_info_attributes(data) == {
        "severity": None,
        "category": None,
        "reason": None,
        "recommended_action": None,
        "raw_code": 0,
    }


def test_state_parser_populates_hardware_fault_details() -> None:
    data = _parse_error_info(1)

    assert data.error_message == "Hardware Fault (IO expander)"
    assert data.error_severity == "Fault"
    assert data.error_category == "Hardware"
    assert data.error_reason == "Hardware Fault (IO expander)"
