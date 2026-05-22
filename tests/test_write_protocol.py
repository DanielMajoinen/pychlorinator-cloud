"""Wire-format regression tests for Halo write commands."""

from __future__ import annotations

import datetime
import struct

import pytest

from pychlorinator_cloud.setpoints import build_setpoint_command
from pychlorinator_cloud.websocket_client import (
    ACTION_CMD_ID,
    CUSTOM_NAMES_VOMIT_CMD_ID,
    LIGHT_CMD_ID,
    MAINTENANCE_STATE_CMD_ID,
    MANDATORY_REFRESH_CMD_IDS,
    MEASUREMENTS_CMD_ID,
    PROBE_STATISTICS_CMD_ID,
    STATISTICS_B_CMD_ID,
    TEMPERATURE_CMD_ID,
    TIMER_CAPABILITIES_CMD_ID,
    TIMER_SETUP_CMD_ID,
    HaloWebSocketClient,
)


class CapturingClient(HaloWebSocketClient):
    def __init__(self) -> None:
        super().__init__("serial", "user", "pass")
        self.sent: list[bytes] = []
        self.requested: list[int] = []

    async def send_command(self, command_bytes: bytes, *, source: str = "command") -> None:
        self.sent.append(command_bytes)

    async def request_data(self, cmd_id: int, *, source: str = "request_data") -> None:
        self.requested.append(cmd_id)


@pytest.fixture(autouse=True)
def no_refresh_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fast_sleep(delay_seconds: float) -> None:
        return None

    monkeypatch.setattr("pychlorinator_cloud.websocket_client._sleep_briefly", _fast_sleep)


@pytest.mark.asyncio
async def test_send_action_default_no_refresh() -> None:
    client = CapturingClient()

    await client.send_action(1, b"")

    expected = bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x01" + b"\x00" * 16
    assert client.sent == [expected]
    assert len(client.sent[0]) == 20
    assert client.requested == []


@pytest.mark.asyncio
async def test_send_action_acid_hold_refreshes_006a() -> None:
    start = CapturingClient()

    await start.disable_acid_dosing()

    expected_start = (
        bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x0a\x01" + b"\x00" * 15
    )
    assert start.sent == [expected_start]
    assert start.requested == [MAINTENANCE_STATE_CMD_ID]

    cancel = CapturingClient()
    cancel.data.acid_dosing_state = "OffIndefinitely"

    await cancel.enable_acid_dosing()

    expected_cancel = (
        bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x0a\x00" + b"\x00" * 15
    )
    assert cancel.sent == [expected_cancel]
    assert cancel.requested == [MAINTENANCE_STATE_CMD_ID]


@pytest.mark.asyncio
async def test_post_action_refresh_skips_if_recently_pushed() -> None:
    client = CapturingClient()
    client.data.cmd_last_seen[MAINTENANCE_STATE_CMD_ID] = (
        datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=1.0)
    )

    await client._refresh_after_action(MAINTENANCE_STATE_CMD_ID)

    assert client.requested == []


@pytest.mark.asyncio
async def test_post_action_refresh_fires_if_stale() -> None:
    client = CapturingClient()
    client.data.cmd_last_seen[MAINTENANCE_STATE_CMD_ID] = (
        datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=5.0)
    )

    await client._refresh_after_action(MAINTENANCE_STATE_CMD_ID)

    assert client.requested == [MAINTENANCE_STATE_CMD_ID]


@pytest.mark.asyncio
async def test_refresh_optional_fires_optional_tier_only() -> None:
    client = CapturingClient()

    await client.refresh_optional_values()

    assert client.requested == [
        PROBE_STATISTICS_CMD_ID,
        STATISTICS_B_CMD_ID,
        MEASUREMENTS_CMD_ID,
        TEMPERATURE_CMD_ID,
        TIMER_CAPABILITIES_CMD_ID,
        TIMER_SETUP_CMD_ID,
        CUSTOM_NAMES_VOMIT_CMD_ID,
    ]
    assert set(client.requested).isdisjoint(MANDATORY_REFRESH_CMD_IDS)


@pytest.mark.asyncio
async def test_refresh_optional_rate_limited_to_30s() -> None:
    client = CapturingClient()

    await client.refresh_optional_values()
    with pytest.raises(RuntimeError, match=r"Refresh rate-limited; try again in \d+s"):
        await client.refresh_optional_values()


@pytest.mark.asyncio
async def test_disable_acid_indefinite_sends_01_byte() -> None:
    client = CapturingClient()

    await client.disable_acid_dosing()

    expected = bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x0a\x01" + b"\x00" * 15
    assert client.sent == [expected]
    assert client.requested == [MAINTENANCE_STATE_CMD_ID]
    assert client.data.acid_dosing_state == "OffIndefinitely"


@pytest.mark.asyncio
async def test_enable_acid_indefinite_sends_00_byte() -> None:
    client = CapturingClient()
    client.data.acid_dosing_state = "OffIndefinitely"

    await client.enable_acid_dosing()

    expected = bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x0a\x00" + b"\x00" * 15
    assert client.sent == [expected]
    assert client.requested == [MAINTENANCE_STATE_CMD_ID]


@pytest.mark.asyncio
async def test_sanitise_until_tomorrow_sends_action_22_empty_data() -> None:
    client = CapturingClient()

    await client.start_sanitise_until_timer_tomorrow()

    expected = bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x16" + b"\x00" * 16
    assert client.sent == [expected]
    assert len(client.sent[0]) == 20
    assert client.requested == [MAINTENANCE_STATE_CMD_ID]


@pytest.mark.asyncio
async def test_filter_for_period_sends_action_23_with_i32_minutes() -> None:
    client = CapturingClient()

    await client.start_filter_for_period(60)

    expected = (
        bytes([0x03])
        + struct.pack("<H", ACTION_CMD_ID)
        + b"\x17"
        + struct.pack("<i", 60)
        + b"\x00" * 12
    )
    assert client.sent == [expected]
    assert client.sent[0][:8] == bytes.fromhex("03 f4 01 17 3c 00 00 00")
    assert len(client.sent[0]) == 20
    assert client.requested == [MAINTENANCE_STATE_CMD_ID]


@pytest.mark.asyncio
async def test_sanitise_for_period_sends_action_31_with_i32_minutes() -> None:
    client = CapturingClient()

    await client.start_sanitise_for_period(60)

    expected = (
        bytes([0x03])
        + struct.pack("<H", ACTION_CMD_ID)
        + b"\x1f"
        + struct.pack("<i", 60)
        + b"\x00" * 12
    )
    assert client.sent == [expected]
    assert len(client.sent[0]) == 20
    assert client.requested == [MAINTENANCE_STATE_CMD_ID]


@pytest.mark.asyncio
async def test_abort_maintenance_sends_action_21_empty_data() -> None:
    client = CapturingClient()

    await client.abort_maintenance_task()

    expected = bytes([0x03]) + struct.pack("<H", ACTION_CMD_ID) + b"\x15" + b"\x00" * 16
    assert client.sent == [expected]
    assert len(client.sent[0]) == 20
    assert client.requested == [MAINTENANCE_STATE_CMD_ID]


def test_setpoint_write_padded_to_20_bytes() -> None:
    command = build_setpoint_command(
        ph_setpoint=7.4,
        orp_setpoint=700,
        pool_chlorine_setpoint=5,
        acid_setpoint=2,
        spa_chlorine_setpoint=3,
    )

    assert len(command) == 20
    assert command[:3] == b"\x03\x66\x00"
    assert command[9:] == b"\x00" * 11


@pytest.mark.asyncio
async def test_light_mode_off_sends_03_with_zone() -> None:
    client = CapturingClient()

    await client.set_light_mode("Off")

    expected = bytes([0x03]) + struct.pack("<H", LIGHT_CMD_ID) + b"\x03\x00" + b"\x00" * 15
    assert client.sent == [expected]
    assert len(client.sent[0]) == 20
    assert client.requested == []
    assert client.data.light_mode == "Off"
