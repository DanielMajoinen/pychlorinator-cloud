import unittest

from pychlorinator_cloud.websocket_client import (
    CAPABILITIES_CMD_ID,
    EQUIPMENT_PARAMETER_CMD_ID,
    GPO_SETUP_CMD_ID,
    HEAT_DEMAND_CMD_ID,
    HEATER_STATE_CMD_ID,
    LIGHT_CAPABILITIES_CMD_ID,
    LIGHT_STATE_CMD_ID,
    MAINTENANCE_STATE_CMD_ID,
    MEASUREMENTS_CMD_ID,
    MANDATORY_REFRESH_CMD_IDS,
    PROBE_STATISTICS_CMD_ID,
    SETTINGS_CMD_ID,
    SETPOINT_CMD_ID,
    SETTLED_OPTIONAL_CMD_IDS,
    STATISTICS_B_CMD_ID,
    STARTUP_REFRESH_CMD_IDS,
    STATE_CMD_ID,
    TEMPERATURE_CMD_ID,
    TIMER_CAPABILITIES_CMD_ID,
    TIMER_CONFIG_CMD_ID,
    TIMER_SETUP_CMD_ID,
    TIMER_STATE_CMD_ID,
    VALVE_SETUP_CMD_ID,
    HaloWebSocketClient,
)


class StartupRefreshCommandTests(unittest.TestCase):
    def test_startup_refresh_uses_parser_backed_core_ids(self):
        # Read-only-complete extension: temperature 0x0009 + timer
        # capabilities/setup/state 0x0190/0x0191/0x0192 added so the
        # corresponding entities populate at startup instead of waiting
        # indefinitely on a controller-pushed update that doesn't arrive
        # on keepalive.
        self.assertEqual(
            STARTUP_REFRESH_CMD_IDS,
            (
                STATE_CMD_ID,
                SETPOINT_CMD_ID,
                SETTINGS_CMD_ID,
                CAPABILITIES_CMD_ID,
                MAINTENANCE_STATE_CMD_ID,
                EQUIPMENT_PARAMETER_CMD_ID,
                TIMER_STATE_CMD_ID,
                HEATER_STATE_CMD_ID,
                HEAT_DEMAND_CMD_ID,
                LIGHT_STATE_CMD_ID,
                LIGHT_CAPABILITIES_CMD_ID,
                PROBE_STATISTICS_CMD_ID,
                STATISTICS_B_CMD_ID,
                MEASUREMENTS_CMD_ID,
                TEMPERATURE_CMD_ID,
                GPO_SETUP_CMD_ID,
                VALVE_SETUP_CMD_ID,
                TIMER_CAPABILITIES_CMD_ID,
                TIMER_SETUP_CMD_ID,
            ),
        )
        # Earlier diagnostic builds tried these app-observed but unparsed cmd
        # IDs; they must stay out of the startup set.
        self.assertNotIn(0x006B, STARTUP_REFRESH_CMD_IDS)
        self.assertNotIn(0x0005, STARTUP_REFRESH_CMD_IDS)
        self.assertIn(PROBE_STATISTICS_CMD_ID, STARTUP_REFRESH_CMD_IDS)
        self.assertIn(MAINTENANCE_STATE_CMD_ID, MANDATORY_REFRESH_CMD_IDS)
        self.assertNotIn(MAINTENANCE_STATE_CMD_ID, SETTLED_OPTIONAL_CMD_IDS)
        self.assertNotIn(TIMER_CONFIG_CMD_ID, MANDATORY_REFRESH_CMD_IDS)
        self.assertIn(LIGHT_STATE_CMD_ID, MANDATORY_REFRESH_CMD_IDS)
        self.assertIn(LIGHT_CAPABILITIES_CMD_ID, MANDATORY_REFRESH_CMD_IDS)

    def test_mandatory_refresh_includes_all_entity_gates(self):
        required = {
            0x0068,
            0x0066,
            0x0064,
            0x0069,
            0x006A,
            0x00CA,
            0x0192,
            0x044E,
            0x0451,
            0x012C,
            0x012D,
        }
        missing = required - set(MANDATORY_REFRESH_CMD_IDS)
        self.assertFalse(
            missing,
            f"Missing from MANDATORY_REFRESH_CMD_IDS: {[f'0x{x:04x}' for x in missing]}",
        )

    def test_quiet_reconnect_optionals_are_data_aware(self):
        """Quiet-reconnect optionals include only missing non-gate telemetry."""
        optional_missing = [
            PROBE_STATISTICS_CMD_ID,
            STATISTICS_B_CMD_ID,
            MEASUREMENTS_CMD_ID,
            TEMPERATURE_CMD_ID,
            GPO_SETUP_CMD_ID,
            VALVE_SETUP_CMD_ID,
        ]
        client = HaloWebSocketClient("serial", "user", "pass")
        self.assertEqual(client._quiet_reconnect_missing_core_cmds(), optional_missing)

        client.data.highest_ph_measured = 8.1
        client.data.highest_orp_measured = 760
        client.data.power_board_runtime_hours = 120
        client.data.operating_days = 1102
        client.data.board_temperature_c = 30.1
        client.data.water_temperature_c = 27.4
        client.data.gpo_names = {1: "Jets", 2: "Booster Pump", 3: "Blower", 4: "No Name"}
        client.data.valve_names = {1: "Pool Valve", 2: "Spa Valve", 3: "None", 4: "None"}
        self.assertEqual(client._quiet_reconnect_missing_core_cmds(), [])


class QuietReconnectRefreshTests(unittest.IsolatedAsyncioTestCase):
    async def test_quiet_reconnect_fires_mandatory_immediately_without_20s_delay(self):
        from unittest.mock import patch

        events = []
        client = HaloWebSocketClient("serial", "user", "pass")
        client._quiet_reconnect = True
        client._running = True

        async def request_data(cmd_id, *, source="test"):
            events.append(("request", cmd_id, source))

        async def fake_sleep(delay):
            events.append(("sleep", delay, None))

        client.request_data = request_data
        with patch("pychlorinator_cloud.websocket_client.asyncio.sleep", fake_sleep):
            await client._request_all_data()

        requested = [event[1] for event in events if event[0] == "request"]
        delays = [event[1] for event in events if event[0] == "sleep"]

        self.assertEqual(requested[: len(MANDATORY_REFRESH_CMD_IDS)], list(MANDATORY_REFRESH_CMD_IDS))
        self.assertNotIn(20.0, delays)
        self.assertEqual(delays[: len(MANDATORY_REFRESH_CMD_IDS)], [0.3] * len(MANDATORY_REFRESH_CMD_IDS))
        self.assertTrue(all(delay in {0.3, 0.5} for delay in delays))


if __name__ == "__main__":
    unittest.main()
