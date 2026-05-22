"""Regression tests for the 0x012C light state parser."""

from __future__ import annotations

import struct

import pytest

from pychlorinator_cloud.payload_parsers import (
    _derive_active_source,
    _parse_light_state,
    parse_data_payload,
)
from pychlorinator_cloud.websocket_client import HaloWebSocketClient


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


def test_parse_light_state_new_layout_zone1_on_only() -> None:
    data = bytes([1, 0, 0, 0, 5, 5, 0, 0, 0x01])

    result = _parse_light_state(data)

    assert result["type"] == "light_state"
    assert result["zone_modes_raw"] == [1, 0, 0, 0]
    assert result["zone_colours_raw"] == [5, 5, 0, 0]
    assert result["zone1_on"] is True
    assert result["zone2_on"] is False
    assert result["zone3_on"] is False
    assert result["zone4_on"] is False
    assert "active_timer" not in result


def test_parse_light_state_real_flag_bits_zone1_and_zone3() -> None:
    data = bytes([0, 1, 2, 3, 9, 8, 7, 6, 0x05])

    result = _parse_light_state(data)

    assert result["zone1_mode"] == "Off"
    assert result["zone2_mode"] == "Auto"
    assert result["zone3_mode"] == "On"
    assert result["zone4_mode"] == "Unknown(3)"
    assert result["zone1_on"] is True
    assert result["zone2_on"] is False
    assert result["zone3_on"] is True
    assert result["zone4_on"] is False
    # zone1 mode=Off + on=True -> "on" (light illuminated despite Off mode)
    assert result["zone1_active_source"] == "on"
    # zone2 mode=Auto + on=False -> "off"
    assert result["zone2_active_source"] == "off"
    # zone3 mode=On + on=True -> "manual_on"
    assert result["zone3_active_source"] == "manual_on"
    # zone4 mode=Unknown(3) + on=False -> "off"
    assert result["zone4_active_source"] == "off"
    assert result["zone_colours_raw"] == [9, 8, 7, 6]


def test_parse_light_state_too_short() -> None:
    result = _parse_light_state(b"\x01\x02\x03")

    assert result["type"] == "light_state"
    assert result["raw"] == "010203"
    assert result["error"] == "too short"


@pytest.mark.parametrize(
    ("manual_mode", "zone_on", "expected"),
    [
        # mode=On: manual override
        ("On", True, "manual_on"),
        ("On", False, "manual_off"),
        # mode=Auto: timer-driven
        ("Auto", True, "timer"),
        ("Auto", False, "off"),
        # mode=Off: should be off; if zone_on is True somehow, surface as "on"
        ("Off", True, "on"),
        ("Off", False, "off"),
    ],
)
def test_active_source_derivation(
    manual_mode: str,
    zone_on: bool,
    expected: str,
) -> None:
    assert _derive_active_source(manual_mode, zone_on) == expected


def test_parse_data_payload_dispatches_0x012c() -> None:
    data = bytes([1, 2, 3, 4, 6, 7, 8, 9, 0x0A])

    result = parse_data_payload(_make_raw(0x012C, data))

    assert result["cmd_id"] == 0x012C
    assert result["cmd_hex"] == "0x012c"
    assert result["type"] == "light_state"
    assert result["zone_modes_raw"] == [1, 2, 3, 4]
    assert result["zone2_on"] is True
    assert result["zone4_on"] is True
    assert result["zone_colours_raw"] == [6, 7, 8, 9]
    assert "active_timer" not in result


def test_light_state_updates_live_data_model() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    raw = _make_raw(0x012C, bytes([1, 2, 3, 4, 5, 6, 7, 8, 0x09]))

    client._update_data(parse_data_payload(raw), raw)

    assert client.data.light_zone1_mode_raw == 1
    assert client.data.light_zone2_mode_raw == 2
    assert client.data.light_zone3_mode_raw == 3
    assert client.data.light_zone4_mode_raw == 4
    assert client.data.light_zone1_mode == "Auto"
    assert client.data.light_mode == "Auto"
    assert client.data.light_zone2_mode == "On"
    assert client.data.light_zone3_mode == "Unknown(3)"
    assert client.data.light_zone4_mode == "Unknown(4)"
    assert client.data.light_zone1_on is True
    assert client.data.light_zone2_on is False
    assert client.data.light_zone3_on is False
    assert client.data.light_zone4_on is True
    assert not hasattr(client.data, "light_active_timer")
    # zone1 mode=Auto + on=True -> "timer" (Auto with output on = timer driving it)
    assert client.data.light_zone1_active_source == "timer"
    # zone2 mode=On + on=False -> "manual_off" (manual override, output not yet on)
    assert client.data.light_zone2_active_source == "manual_off"
    # zone3 mode=Unknown(3) + on=False -> "off"
    assert client.data.light_zone3_active_source == "off"
    # zone4 mode=Unknown(4) + on=True -> "on"
    assert client.data.light_zone4_active_source == "on"
