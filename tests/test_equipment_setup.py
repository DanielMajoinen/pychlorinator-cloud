"""Tests for built-in GPO/valve equipment setup readback."""

from __future__ import annotations

import struct

import pytest

from pychlorinator_cloud.payload_parsers import parse_data_payload
from pychlorinator_cloud.websocket_client import (
    GPO_SETUP_CMD_ID,
    HaloWebSocketClient,
    VALVE_SETUP_CMD_ID,
)


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


def test_parse_gpo_setup_jets() -> None:
    result = parse_data_payload(_make_raw(GPO_SETUP_CMD_ID, b"\x07\x00\x01\x00\x08\x00\x01"))

    assert result["type"] == "gpo_setup"
    assert result["gpo_slot"] == 1
    assert result["name_label"] == "Jets"
    assert result["is_custom_name"] is False


def test_parse_gpo_setup_other_marks_custom() -> None:
    result = parse_data_payload(_make_raw(GPO_SETUP_CMD_ID, b"\x07\x01\x01\x00\x01\x00\x00"))

    assert result["gpo_slot"] == 2
    assert result["name_label"] == "Other"
    assert result["is_custom_name"] is True


def test_parse_valve_setup_pool_spa_combo() -> None:
    pool = parse_data_payload(_make_raw(VALVE_SETUP_CMD_ID, b"\x00\x01\x02\x01"))
    spa = parse_data_payload(_make_raw(VALVE_SETUP_CMD_ID, b"\x01\x01\x03\x00"))

    assert pool["type"] == "valve_setup"
    assert pool["valve_slot"] == 1
    assert pool["name_label"] == "Pool Valve"
    assert pool["is_custom_name"] is False
    assert spa["valve_slot"] == 2
    assert spa["name_label"] == "Spa Valve"
    assert spa["is_custom_name"] is False


def test_parse_valve_setup_too_short() -> None:
    result = parse_data_payload(_make_raw(VALVE_SETUP_CMD_ID, b"\x00\x01"))

    assert result["type"] == "valve_setup"
    assert result["error"] == "too short"


def test_get_equipment_name_resolves_from_dict() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    client.data.gpo_names = {1: "Jets"}

    assert client.get_equipment_name(3) == "Jets"


def test_get_equipment_name_resolves_custom_valve_name() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    client.data.valve_names = {1: "Other"}
    client.data.valve_is_custom_name = {1: True}
    client.data.valve_custom_names = {0: "Solar Bypass"}

    assert client.get_equipment_name(7) == "Solar Bypass"


def test_get_equipment_name_custom_valve_falls_back_to_other() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    client.data.valve_names = {1: "Other"}
    client.data.valve_is_custom_name = {1: True}

    assert client.get_equipment_name(7) == "Other"


def test_get_equipment_name_falls_back_when_unpopulated() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")

    assert client.get_equipment_name(3) == "GPO1"
    assert client.get_equipment_name(7) == "Valve1"


def test_get_equipment_name_pool_spa_toggle() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")

    client.data.spa_selection = True
    assert client.get_equipment_name(0) == "Spa"
    client.data.spa_selection = False
    assert client.get_equipment_name(0) == "Pool"


@pytest.mark.asyncio
async def test_request_equipment_setup_sends_eight_selectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    sent: list[bytes] = []

    async def send_command(command_bytes: bytes, *, source: str = "command") -> None:
        sent.append(command_bytes)

    async def fast_sleep(delay_seconds: float) -> None:
        return None

    monkeypatch.setattr(client, "send_command", send_command)
    monkeypatch.setattr("pychlorinator_cloud.websocket_client._sleep_briefly", fast_sleep)

    await client.request_equipment_setup()

    assert len(sent) == 8
    assert [struct.unpack_from("<H", payload, 1)[0] for payload in sent] == [
        GPO_SETUP_CMD_ID,
        GPO_SETUP_CMD_ID,
        GPO_SETUP_CMD_ID,
        GPO_SETUP_CMD_ID,
        VALVE_SETUP_CMD_ID,
        VALVE_SETUP_CMD_ID,
        VALVE_SETUP_CMD_ID,
        VALVE_SETUP_CMD_ID,
    ]
    assert [(payload[3], payload[4]) for payload in sent] == [
        (7, 0),
        (7, 1),
        (8, 0),
        (8, 1),
        (0, 0),
        (1, 0),
        (2, 0),
        (3, 0),
    ]
    assert all(len(payload) == 20 for payload in sent)


@pytest.mark.asyncio
async def test_refresh_optional_values_includes_equipment_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    called = False
    custom_names_called = False

    async def request_data(cmd_id: int, *, source: str = "request_data") -> None:
        return None

    async def request_equipment_setup() -> None:
        nonlocal called
        called = True

    async def request_custom_names_vomit() -> None:
        nonlocal custom_names_called
        custom_names_called = True

    async def fast_sleep(delay_seconds: float) -> None:
        return None

    monkeypatch.setattr(client, "request_data", request_data)
    monkeypatch.setattr(client, "request_equipment_setup", request_equipment_setup)
    monkeypatch.setattr(client, "request_custom_names_vomit", request_custom_names_vomit)
    monkeypatch.setattr("pychlorinator_cloud.websocket_client._sleep_briefly", fast_sleep)

    await client.refresh_optional_values()

    assert called is True
    assert custom_names_called is True
