"""Regression tests for the 0x012D light capabilities parser."""

from __future__ import annotations

import struct

from pychlorinator_cloud.payload_parsers import _parse_light_capabilities, parse_data_payload
from pychlorinator_cloud.websocket_client import HaloWebSocketClient, LIGHT_CAPABILITIES_CMD_ID


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


def test_parse_light_capabilities_single_zone() -> None:
    result = _parse_light_capabilities(bytes([1, 1, 4, 1, 0b0001]))

    assert result == {
        "type": "light_capabilities",
        "lighting_enabled": True,
        "onboard_light_enabled": True,
        "lighting_model": 4,
        "lighting_num_zones_in_use": 1,
        "zone1_is_multicolour": True,
        "zone2_is_multicolour": False,
        "zone3_is_multicolour": False,
        "zone4_is_multicolour": False,
    }


def test_parse_light_capabilities_two_zones_all_multicolour_flags() -> None:
    result = _parse_light_capabilities(bytes([1, 0, 7, 2, 0b1111]))

    assert result["lighting_enabled"] is True
    assert result["onboard_light_enabled"] is False
    assert result["lighting_model"] == 7
    assert result["lighting_num_zones_in_use"] == 2
    assert result["zone1_is_multicolour"] is True
    assert result["zone2_is_multicolour"] is True
    assert result["zone3_is_multicolour"] is True
    assert result["zone4_is_multicolour"] is True


def test_parse_light_capabilities_too_short() -> None:
    result = _parse_light_capabilities(b"\x01\x00")

    assert result["type"] == "light_capabilities"
    assert result["raw"] == "0100"
    assert result["error"] == "too short"


def test_parse_data_payload_dispatches_0x012d_and_updates_live_data() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    raw = _make_raw(LIGHT_CAPABILITIES_CMD_ID, bytes([1, 0, 3, 1, 0b0001]))
    parsed = parse_data_payload(raw)

    client._update_data(parsed, raw)

    assert parsed["type"] == "light_capabilities"
    assert client.data.lighting_enabled is True
    assert client.data.onboard_light_enabled is False
    assert client.data.lighting_model == 3
    assert client.data.lighting_num_zones_in_use == 1
    assert client.data.zone1_is_multicolour is True
    assert client.data.zone2_is_multicolour is False
