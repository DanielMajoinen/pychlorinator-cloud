"""Tests for the HeaterDemandSettings (cmd 0x0451) read/write path."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from pychlorinator_cloud.payload_parsers import parse_data_payload
from pychlorinator_cloud.websocket_client import (
    HEAT_DEMAND_CMD_ID,
    HaloWebSocketClient,
    build_heat_demand_payload,
)


def _make_raw(cmd_id: int, data: bytes) -> bytes:
    import struct

    return bytes([0x02]) + struct.pack("<H", cmd_id) + data.ljust(17, b"\x00")


class HeatDemandParserTests(unittest.TestCase):
    def test_parses_enabled_window_with_activation(self):
        # [1,1,18,30,06,00,1] -> enabled, window-enabled, stop 18:30, start 06:00, activated.
        payload = bytes([1, 1, 18, 30, 6, 0, 1])
        parsed = parse_data_payload(_make_raw(HEAT_DEMAND_CMD_ID, payload))
        self.assertEqual(parsed["type"], "heat_demand_settings")
        self.assertTrue(parsed["heat_demand_enabled"])
        self.assertTrue(parsed["heat_demand_window_enabled"])
        self.assertEqual(parsed["heat_demand_window_start_hour"], 6)
        self.assertEqual(parsed["heat_demand_window_start_minute"], 0)
        self.assertEqual(parsed["heat_demand_window_stop_hour"], 18)
        self.assertEqual(parsed["heat_demand_window_stop_minute"], 30)
        self.assertTrue(parsed["heat_demand_activated"])

    def test_parses_all_zero_state(self):
        parsed = parse_data_payload(_make_raw(HEAT_DEMAND_CMD_ID, b"\x00" * 7))
        self.assertEqual(parsed["type"], "heat_demand_settings")
        self.assertFalse(parsed["heat_demand_enabled"])
        self.assertFalse(parsed["heat_demand_window_enabled"])
        self.assertFalse(parsed["heat_demand_activated"])

    def test_too_short_payload_returns_error(self):
        from pychlorinator_cloud.payload_parsers import _parse_heat_demand_settings

        parsed = _parse_heat_demand_settings(b"\x00\x01")
        self.assertEqual(parsed["type"], "heat_demand_settings")
        self.assertEqual(parsed["error"], "too short")


class HeatDemandPayloadTests(unittest.TestCase):
    def test_payload_byte_order_matches_decompile(self):
        # Pack=1: enabled, window_enabled, stop_h, stop_m, start_h, start_m, activated.
        payload = build_heat_demand_payload(
            enabled=True,
            window_enabled=True,
            start_hour=7,
            start_minute=15,
            stop_hour=19,
            stop_minute=45,
            activated=False,
        )
        self.assertEqual(payload, bytes([1, 1, 19, 45, 7, 15, 0]))
        self.assertEqual(len(payload), 7)

    def test_rejects_out_of_range_hour(self):
        with self.assertRaises(ValueError):
            build_heat_demand_payload(
                enabled=True,
                window_enabled=True,
                start_hour=24,  # invalid
                start_minute=0,
                stop_hour=10,
                stop_minute=0,
                activated=False,
            )

    def test_rejects_out_of_range_minute(self):
        with self.assertRaises(ValueError):
            build_heat_demand_payload(
                enabled=True,
                window_enabled=True,
                start_hour=10,
                start_minute=60,  # invalid
                stop_hour=12,
                stop_minute=0,
                activated=False,
            )


class HeatDemandLiveDataTests(unittest.TestCase):
    def test_apply_payload_updates_chlorinator_live_data(self):
        client = HaloWebSocketClient("serial", "user", "pass")
        raw = _make_raw(HEAT_DEMAND_CMD_ID, bytes([1, 1, 18, 30, 6, 0, 1]))
        client._update_data(parse_data_payload(raw), raw)

        self.assertIs(client.data.heat_demand_enabled, True)
        self.assertIs(client.data.heat_demand_window_enabled, True)
        self.assertEqual(client.data.heat_demand_window_start_hour, 6)
        self.assertEqual(client.data.heat_demand_window_start_minute, 0)
        self.assertEqual(client.data.heat_demand_window_stop_hour, 18)
        self.assertEqual(client.data.heat_demand_window_stop_minute, 30)
        self.assertIs(client.data.heat_demand_activated, True)


class HeatDemandWriteFlowTests(unittest.IsolatedAsyncioTestCase):
    async def _capture_write(self, **overrides):
        client = HaloWebSocketClient("serial", "user", "pass")
        # Seed the live snapshot so partial-update merges work.
        client.data.heat_demand_enabled = True
        client.data.heat_demand_window_enabled = True
        client.data.heat_demand_window_start_hour = 6
        client.data.heat_demand_window_start_minute = 0
        client.data.heat_demand_window_stop_hour = 18
        client.data.heat_demand_window_stop_minute = 30
        client.data.heat_demand_activated = False

        sent = []

        async def fake_send_command(command, *, source: str = ""):
            sent.append((source, command))

        async def fake_sleep(_delay):
            return None

        async def fake_request_heat_demand_settings(*, source: str = ""):
            sent.append(("verify", source))

        client.send_command = fake_send_command
        client.request_heat_demand_settings = fake_request_heat_demand_settings
        with patch(
            "pychlorinator_cloud.websocket_client._sleep_briefly", fake_sleep
        ):
            await client.write_heat_demand(**overrides)
        return client, sent

    async def test_full_write_uses_padded_17_byte_frame(self):
        client, sent = await self._capture_write(
            enabled=True,
            window_enabled=True,
            start_hour=7,
            start_minute=15,
            stop_hour=19,
            stop_minute=45,
            activated=True,
        )
        # First send: the actual write.
        write_source, write_command = sent[0]
        self.assertTrue(write_source.startswith("write(0x0451)"))
        self.assertEqual(write_command[0], 0x03)
        self.assertEqual(write_command[1:3], b"\x51\x04")  # LE cmd id
        self.assertEqual(len(write_command), 1 + 2 + 17)
        # Payload first 7 bytes match the decompile byte order.
        self.assertEqual(write_command[3 : 3 + 7], bytes([1, 1, 19, 45, 7, 15, 1]))

    async def test_partial_write_falls_back_to_snapshot(self):
        client, sent = await self._capture_write(activated=True)
        write_source, write_command = sent[0]
        # All other fields preserved from the seeded snapshot, activated flips on.
        self.assertEqual(write_command[3 : 3 + 7], bytes([1, 1, 18, 30, 6, 0, 1]))

    async def test_write_warns_on_readback_mismatch(self):
        client = HaloWebSocketClient("serial", "user", "pass")
        client.data.heat_demand_enabled = False
        client.data.heat_demand_window_enabled = False
        client.data.heat_demand_window_start_hour = 0
        client.data.heat_demand_window_start_minute = 0
        client.data.heat_demand_window_stop_hour = 0
        client.data.heat_demand_window_stop_minute = 0
        client.data.heat_demand_activated = False

        async def fake_send_command(command, *, source: str = ""):
            return None

        async def fake_sleep(_delay):
            return None

        async def fake_request_heat_demand_settings(*, source: str = ""):
            # Simulate the controller storing different values than we asked for.
            client.data.heat_demand_enabled = False  # asked for True
            client.data.heat_demand_window_enabled = True
            client.data.heat_demand_window_start_hour = 6
            client.data.heat_demand_window_start_minute = 0
            client.data.heat_demand_window_stop_hour = 18
            client.data.heat_demand_window_stop_minute = 30
            client.data.heat_demand_activated = False

        client.send_command = fake_send_command
        client.request_heat_demand_settings = fake_request_heat_demand_settings
        with patch(
            "pychlorinator_cloud.websocket_client._sleep_briefly", fake_sleep
        ), self.assertLogs(
            "pychlorinator_cloud.websocket_client", level="WARNING"
        ) as logged:
            await client.write_heat_demand(
                enabled=True,
                window_enabled=True,
                start_hour=6,
                start_minute=0,
                stop_hour=18,
                stop_minute=30,
                activated=False,
            )
        # WARNING only fires if mismatch persists past the reconfirm poll.
        self.assertTrue(
            any(
                "Heat-demand readback mismatch" in msg
                and "persisted past" in msg
                for msg in logged.output
            ),
            logged.output,
        )

    async def test_first_readback_stale_then_reconfirm_clears_warning(self):
        """Vendor race: first readback returns pre-write state, second returns post.

        Live testing showed the controller acks 0x0451
        writes immediately with the PRE-write snapshot, then updates a beat
        later. The race-tolerance fix re-polls once on mismatch; only the
        second readback should drive the warning.
        """
        client = HaloWebSocketClient("serial", "user", "pass")
        client.data.heat_demand_enabled = True
        client.data.heat_demand_window_enabled = True
        client.data.heat_demand_window_start_hour = 10
        client.data.heat_demand_window_start_minute = 0
        client.data.heat_demand_window_stop_hour = 17
        client.data.heat_demand_window_stop_minute = 0
        client.data.heat_demand_activated = False  # current state

        readback_call_count = {"n": 0}

        async def fake_send_command(command, *, source: str = ""):
            return None

        async def fake_sleep(_delay):
            return None

        async def fake_request_heat_demand_settings(*, source: str = ""):
            readback_call_count["n"] += 1
            if readback_call_count["n"] == 1:
                # Race: first readback returns pre-write state.
                client.data.heat_demand_activated = False
            else:
                # Reconfirm: second readback returns post-write state.
                client.data.heat_demand_activated = True

        client.send_command = fake_send_command
        client.request_heat_demand_settings = fake_request_heat_demand_settings
        with patch(
            "pychlorinator_cloud.websocket_client._sleep_briefly", fake_sleep
        ):
            import logging

            logger = logging.getLogger("pychlorinator_cloud.websocket_client")
            with self.assertLogs(logger, level="DEBUG") as logged:
                await client.write_heat_demand(activated=True)
        # Two readbacks performed.
        self.assertEqual(readback_call_count["n"], 2)
        # No WARNING-level mismatch; only the DEBUG ack-then-update note.
        warnings = [m for m in logged.output if m.startswith("WARNING")]
        self.assertFalse(
            warnings, f"unexpected WARNING after race-tolerance fix: {warnings}"
        )
        debug_msgs = [m for m in logged.output if "ack-then-update" in m]
        self.assertTrue(
            debug_msgs,
            "expected DEBUG ack-then-update note when first readback differs",
        )

    async def test_overnight_window_warns(self):
        client = HaloWebSocketClient("serial", "user", "pass")
        client.data.heat_demand_enabled = True
        client.data.heat_demand_window_enabled = True
        client.data.heat_demand_window_start_hour = 0
        client.data.heat_demand_window_start_minute = 0
        client.data.heat_demand_window_stop_hour = 0
        client.data.heat_demand_window_stop_minute = 0
        client.data.heat_demand_activated = False

        async def fake_send_command(command, *, source: str = ""):
            return None

        async def fake_sleep(_delay):
            return None

        async def fake_request_heat_demand_settings(*, source: str = ""):
            return None

        client.send_command = fake_send_command
        client.request_heat_demand_settings = fake_request_heat_demand_settings
        with patch(
            "pychlorinator_cloud.websocket_client._sleep_briefly", fake_sleep
        ), self.assertLogs(
            "pychlorinator_cloud.websocket_client", level="WARNING"
        ) as logged:
            await client.write_heat_demand(
                start_hour=22,
                start_minute=0,
                stop_hour=6,
                stop_minute=0,
            )
        self.assertTrue(
            any("overnight heat-demand window" in msg for msg in logged.output),
            logged.output,
        )

    async def test_write_without_snapshot_raises_runtime_error(self):
        client = HaloWebSocketClient("serial", "user", "pass")
        # All heat_demand_* fields remain None; partial write should fail loudly.
        with self.assertRaises(RuntimeError) as ctx:
            await client.write_heat_demand(activated=True)
        self.assertIn("heat_demand_enabled", str(ctx.exception))


# ---------------------------------------------------------------------------
# HA-side tests (sensor + binary_sensor + service handler).
# Mirrors the bootstrap pattern from test_equipment_timer_write.py. we reload
# the HA modules under stubbed homeassistant imports.
# ---------------------------------------------------------------------------


def _import_helpers():
    from tests.test_equipment_timer_write import (
        _install_ha_stubs,
        _make_coordinator,
        _reload_ha_module,
    )

    return _install_ha_stubs, _make_coordinator, _reload_ha_module


def test_heat_demand_binary_sensor_descriptions_present():
    _install_ha_stubs, _, _reload_ha_module = _import_helpers()
    _install_ha_stubs()
    binary_module = _reload_ha_module(
        "custom_components.astralpool_halo_cloud.binary_sensor"
    )

    keys = {desc.key for desc in binary_module.BINARY_SENSOR_DESCRIPTIONS}
    assert "heat_demand_enabled" in keys
    assert "heat_demand_window_enabled" in keys
    assert "heat_demand_activated" in keys


def test_heat_demand_summary_sensor_states():
    _install_ha_stubs, _, _reload_ha_module = _import_helpers()
    _install_ha_stubs()
    sensor_module = _reload_ha_module(
        "custom_components.astralpool_halo_cloud.sensor"
    )
    from pychlorinator_cloud.websocket_client import ChlorinatorLiveData

    data = ChlorinatorLiveData()
    # Unknown until first snapshot lands.
    assert sensor_module._heat_demand_summary_value(data) is None
    assert sensor_module._heat_demand_summary_attributes(data) == {}

    # Disabled.
    data.heat_demand_enabled = False
    assert sensor_module._heat_demand_summary_value(data) == "Off"

    # Enabled but window off.
    data.heat_demand_enabled = True
    data.heat_demand_window_enabled = False
    assert sensor_module._heat_demand_summary_value(data) == "Always On"

    # Enabled with window.
    data.heat_demand_window_enabled = True
    data.heat_demand_window_start_hour = 6
    data.heat_demand_window_start_minute = 0
    data.heat_demand_window_stop_hour = 18
    data.heat_demand_window_stop_minute = 30
    data.heat_demand_activated = True
    assert sensor_module._heat_demand_summary_value(data) == "06:00-18:30"
    attrs = sensor_module._heat_demand_summary_attributes(data)
    assert attrs["enabled"] is True
    assert attrs["window_enabled"] is True
    assert attrs["window_start_hour"] == 6
    assert attrs["window_stop_minute"] == 30
    assert attrs["activated"] is True


@pytest.mark.asyncio
async def test_write_heat_demand_service_handler_passes_kwargs():
    _install_ha_stubs, _make_coordinator, _reload_ha_module = _import_helpers()
    _install_ha_stubs()
    init_module = _reload_ha_module(
        "custom_components.astralpool_halo_cloud.__init__"
    )
    coordinator = _make_coordinator()
    coordinator.client.write_heat_demand = AsyncMock()
    hass = SimpleNamespace(data={init_module.DOMAIN: {"entry": coordinator}})

    call = SimpleNamespace(
        data={
            "enabled": True,
            "window_enabled": True,
            "start_hour": 6,
            "start_minute": 0,
            "stop_hour": 18,
            "stop_minute": 30,
            "activated": False,
        }
    )
    await init_module._async_handle_write_heat_demand(hass, call)
    coordinator.client.write_heat_demand.assert_awaited_once_with(
        enabled=True,
        window_enabled=True,
        start_hour=6,
        start_minute=0,
        stop_hour=18,
        stop_minute=30,
        activated=False,
    )


def test_async_purge_obsolete_entities_drops_stale_number_rows():
    _install_ha_stubs, _, _reload_ha_module = _import_helpers()
    _install_ha_stubs()
    init_module = _reload_ha_module(
        "custom_components.astralpool_halo_cloud.__init__"
    )

    removed: list[str] = []

    class FakeEntry:
        def __init__(self, entity_id, unique_id, platform=init_module.DOMAIN):
            self.entity_id = entity_id
            self.unique_id = unique_id
            self.platform = platform

    fake_registry = SimpleNamespace(async_remove=removed.append)

    import sys

    er = sys.modules["homeassistant.helpers.entity_registry"]
    er.async_get = lambda _hass: fake_registry
    er.async_entries_for_config_entry = lambda _registry, _entry_id: [
        FakeEntry("number.halo_1234567_filter_period_minutes", "1234567_filter_period_minutes"),
        FakeEntry("number.halo_1234567_sanitise_period_minutes", "1234567_sanitise_period_minutes"),
        FakeEntry("select.halo_1234567_filter_for_period", "1234567_filter_for_period"),
        FakeEntry("sensor.halo_1234567_heat_demand_schedule", "1234567_heat_demand_schedule"),
        # Wrong platform shouldn't be touched even if the suffix matches.
        FakeEntry(
            "number.other_filter_period_minutes",
            "other_filter_period_minutes",
            platform="some_other_integration",
        ),
    ]

    hass = SimpleNamespace()
    entry = SimpleNamespace(entry_id="abc")
    init_module._async_purge_obsolete_entities(hass, entry)

    assert removed == [
        "number.halo_1234567_filter_period_minutes",
        "number.halo_1234567_sanitise_period_minutes",
    ]


@pytest.mark.asyncio
async def test_write_heat_demand_service_handler_supports_partial_update():
    _install_ha_stubs, _make_coordinator, _reload_ha_module = _import_helpers()
    _install_ha_stubs()
    init_module = _reload_ha_module(
        "custom_components.astralpool_halo_cloud.__init__"
    )
    coordinator = _make_coordinator()
    coordinator.client.write_heat_demand = AsyncMock()
    hass = SimpleNamespace(data={init_module.DOMAIN: {"entry": coordinator}})

    call = SimpleNamespace(data={"activated": True})
    await init_module._async_handle_write_heat_demand(hass, call)
    coordinator.client.write_heat_demand.assert_awaited_once_with(activated=True)


if __name__ == "__main__":
    unittest.main()
