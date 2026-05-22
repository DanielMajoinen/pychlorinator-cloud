"""Tests for 0x051B valve custom-name chunk reassembly."""

from __future__ import annotations

import struct

import pytest

from pychlorinator_cloud.payload_parsers import _parse_valve_custom_name_chunk, parse_data_payload
from pychlorinator_cloud.websocket_client import (
    CUSTOM_NAMES_VOMIT_CMD_ID,
    HaloWebSocketClient,
    VALVE_CUSTOM_NAME_CMD_ID,
)


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


def _chunk(valve_index: int, message_number: int, name_bytes: bytes) -> bytes:
    start = message_number * 13
    fragment = name_bytes[start : start + 13].ljust(13, b"\x00")
    return bytes([valve_index, message_number, len(name_bytes)]) + fragment


def _apply_chunk(client: HaloWebSocketClient, valve_index: int, message_number: int, name: str) -> None:
    raw = _make_raw(
        VALVE_CUSTOM_NAME_CMD_ID,
        _chunk(valve_index, message_number, name.encode("utf-8")),
    )
    client._update_data(parse_data_payload(raw), raw)


def test_parse_valve_custom_name_chunk() -> None:
    result = _parse_valve_custom_name_chunk(b"\x02\x01\x05hello\x00\x00")

    assert result["type"] == "valve_custom_name_chunk"
    assert result["valve_index"] == 2
    assert result["message_number"] == 1
    assert result["custom_name_length"] == 5
    assert result["fragment_bytes"] == b"hello\x00\x00"


def test_parse_valve_custom_name_chunk_too_short() -> None:
    result = _parse_valve_custom_name_chunk(b"\x00\x01\x02")

    assert result["type"] == "valve_custom_name_chunk"
    assert result["error"] == "too short"


def test_valve_custom_name_assembles_in_order() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    name = "Solar Bypass Valve"

    for message_number in (0, 1, 2):
        _apply_chunk(client, 0, message_number, name)

    assert client.data.valve_custom_names[0] == name


def test_valve_custom_name_assembles_out_of_order() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    name = "Water Feature"

    for message_number in (2, 0, 1):
        _apply_chunk(client, 1, message_number, name)

    assert client.data.valve_custom_names[1] == name


def test_valve_custom_name_incomplete_returns_none() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    name = "Incomplete"

    _apply_chunk(client, 0, 0, name)
    _apply_chunk(client, 0, 2, name)

    assert client._assemble_valve_custom_name(0) is None
    assert client.data.valve_custom_names == {}


def test_valve_custom_name_empty_name() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")

    for message_number in (0, 1, 2):
        raw = _make_raw(
            VALVE_CUSTOM_NAME_CMD_ID,
            bytes([0, message_number, 0]) + b"\x00" * 13,
        )
        client._update_data(parse_data_payload(raw), raw)

    assert client.data.valve_custom_names[0] == ""


def test_valve_custom_name_multibyte_split_across_chunk_boundary() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    name = "ABCDEFGHIJKLé Valve"

    for message_number in (0, 1, 2):
        _apply_chunk(client, 0, message_number, name)

    assert client.data.valve_custom_names[0] == name


def test_valve_custom_names_multiple_valves_buffered_separately() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")

    for message_number in (0, 1, 2):
        _apply_chunk(client, 0, message_number, "Spa Bypass")
        _apply_chunk(client, 2, message_number, "Feature")

    assert client.data.valve_custom_names[0] == "Spa Bypass"
    assert client.data.valve_custom_names[2] == "Feature"


@pytest.mark.asyncio
async def test_request_custom_names_vomit_uses_cmd_27_read_frame() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    sent: list[bytes] = []

    async def send_command(command_bytes: bytes, *, source: str = "command") -> None:
        sent.append(command_bytes)

    client.send_command = send_command

    await client.request_custom_names_vomit()

    assert sent == [bytes([0x02]) + struct.pack("<H", CUSTOM_NAMES_VOMIT_CMD_ID) + bytes(17)]
    assert len(sent[0]) == 20
