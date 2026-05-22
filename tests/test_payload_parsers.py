"""Tests for pychlorinator_cloud.payload_parsers."""

from __future__ import annotations

import struct
import unittest

from pychlorinator_cloud.payload_parsers import parse_data_payload


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


class TestParseStateTooShort(unittest.TestCase):
    def test_returns_error(self):
        raw = _make_raw(0x0068, b"\x00" * 5)
        result = parse_data_payload(raw)
        self.assertEqual(result.get("type"), "state")
        self.assertIn("error", result)


class TestParseStateFlags(unittest.TestCase):
    def _state_bytes(
        self,
        flags: int = 0,
        cell_level: int = 0,
        cell_current_ma: int = 1000,
        main_text: int = 5,
        sub1: int = 0,
        orp_mv: int = 700,
        sub2: int = 3,
        ph_raw: int = 74,
        sub3: int = 0,
        pad: bytes = b"\x00\x00\x00\x00\x00",
    ) -> bytes:
        data = bytearray(struct.pack(
            "<BBHBBHBBBxx",
            flags & 0xFF,
            cell_level,
            cell_current_ma,
            main_text,
            sub1,
            orp_mv,
            sub2,
            ph_raw,
            sub3,
        ) + pad)
        data[1] = (flags >> 8) & 0xFF if flags > 0xFF else cell_level
        return bytes(data)

    def test_standby_mode(self):
        data = self._state_bytes(main_text=5)  # Standby
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertEqual(result["type"], "state")
        self.assertEqual(result["info_message"], "Standby")
        self.assertFalse(result["ai_mode_active"])
        self.assertFalse(result["cell_is_operating"])

    def test_ai_mode_sanitising(self):
        flags = 0x820  # FLAG_CELL_ON | FLAG_AI_MODE_ACTIVE
        data = self._state_bytes(flags=flags, main_text=2)  # AIModeSanitising
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertTrue(result["ai_mode_active"])
        self.assertTrue(result["cell_is_operating"])
        self.assertEqual(result["info_message"], "AIModeSanitising")

    def test_off_mode(self):
        data = self._state_bytes(flags=0x00, main_text=0)  # Off
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertEqual(result["info_message"], "Off")
        self.assertFalse(result["ai_mode_active"])

    def test_ph_measurement_decoded(self):
        data = self._state_bytes(ph_raw=74, sub2=3)  # PHIsGreen
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertAlmostEqual(result["ph_measurement"], 7.4)
        self.assertEqual(result["ph_control_status"], "PHIsGreen")

    def test_orp_mv_decoded(self):
        data = self._state_bytes(orp_mv=650)
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertEqual(result["orp_mv"], 650)

    def test_priming_fields_and_orp_decoded(self):
        data = bytearray(self._state_bytes(orp_mv=650, sub3=7))  # PrimingFor
        data[11] = 210
        data[12] = 3
        result = parse_data_payload(_make_raw(0x0068, bytes(data)))
        self.assertEqual(result["timer_info"], "PrimingFor")
        self.assertTrue(result["priming_active"])
        self.assertEqual(result["priming_countdown"], 210)
        self.assertEqual(result["priming_phase_code"], 3)
        # Bytes 6-7 remain ORP little-endian; byte 6 is not water temperature.
        self.assertEqual(result["orp_mv"], 650)

    def test_all_flags(self):
        flags = 0xFFF
        data = self._state_bytes(flags=flags, main_text=1)
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertTrue(result["spa_mode"])
        self.assertTrue(result["pump_is_operating"])
        self.assertTrue(result["cell_is_operating"])
        self.assertTrue(result["cell_is_reversed"])
        self.assertTrue(result["sanitising_until_next_timer_tomorrow"])
        self.assertTrue(result["cooling_fan_on"])
        self.assertTrue(result["light_output_on"])
        self.assertTrue(result["dosing_pump_on"])
        self.assertFalse(result["cell_is_reversing"])
        self.assertTrue(result["ai_mode_active"])

    def test_unknown_main_text(self):
        data = self._state_bytes(main_text=99)
        result = parse_data_payload(_make_raw(0x0068, data))
        self.assertEqual(result["info_message"], "Unknown(99)")


class TestParseSetpoint(unittest.TestCase):
    def test_known_values(self):
        data = struct.pack("<BHBBB", 74, 700, 5, 2, 3)
        result = parse_data_payload(_make_raw(0x0066, data))
        self.assertEqual(result["type"], "setpoint")
        self.assertAlmostEqual(result["ph_setpoint"], 7.4)
        self.assertEqual(result["orp_setpoint"], 700)
        self.assertEqual(result["pool_chlorine_setpoint"], 5)
        self.assertEqual(result["acid_setpoint"], 2)
        self.assertEqual(result["spa_chlorine_setpoint"], 3)

    def test_too_short_returns_error(self):
        result = parse_data_payload(_make_raw(0x0066, b"\x00\x01"))
        self.assertIn("error", result)


class TestParseMeasurements(unittest.TestCase):
    def test_statistics_a(self):
        data = bytes.fromhex("4e04a81300002a0200002200005a019000")
        result = parse_data_payload(_make_raw(0x0259, data))
        self.assertEqual(result["type"], "statistics_a")
        self.assertEqual(result["operating_days"], 1102)
        self.assertEqual(result["unknown_counter_a"], 5032)
        self.assertEqual(result["cell_reversal_count"], 554)
        self.assertEqual(result["previous_days_cell_load_percent"], 34)
        self.assertEqual(result["today_cell_runtime_minutes"], 346)
        self.assertEqual(result["stats_flag_byte"], 144)
        self.assertNotIn("water_temperature_c", result)
        self.assertNotIn("cell_current_ma", result)

    def test_too_short_returns_error(self):
        result = parse_data_payload(_make_raw(0x0259, b"\x00\x01"))
        self.assertIn("error", result)


class TestParseHeaterState(unittest.TestCase):
    def _heater_bytes(
        self,
        status: int = 0x01,  # heater_on
        pump_mode: int = 1,  # Auto
        heater_mode: int = 1,  # On
        setpoint: int = 28,
        hp_mode: int = 1,  # Heating
        forced: int = 0,
        pad: bytes = b"\x00\x00",
        water_valid: int = 1,
        water_temp_raw: int = 280,  # 28.0°C
        error: int = 0,
    ) -> bytes:
        return struct.pack(
            "<BBBBBBxxBHB",
            status,
            pump_mode,
            heater_mode,
            setpoint,
            hp_mode,
            forced,
            water_valid,
            water_temp_raw,
            error,
        )

    def test_known_values(self):
        data = self._heater_bytes()
        result = parse_data_payload(_make_raw(0x044E, data))
        self.assertEqual(result["type"], "heater_state")
        self.assertTrue(result["heater_on"])
        self.assertEqual(result["heater_pump_mode"], "Auto")
        self.assertEqual(result["heater_mode"], "On")
        self.assertEqual(result["heater_setpoint_c"], 28)
        self.assertEqual(result["heat_pump_mode"], "Heating")
        self.assertAlmostEqual(result["heater_water_temp_c"], 28.0)

    def test_heater_off(self):
        data = self._heater_bytes(status=0x00, heater_mode=0, pump_mode=0)
        result = parse_data_payload(_make_raw(0x044E, data))
        self.assertFalse(result["heater_on"])
        self.assertEqual(result["heater_mode"], "Off")
        self.assertEqual(result["heater_pump_mode"], "Off")

    def test_too_short_returns_error(self):
        result = parse_data_payload(_make_raw(0x044E, b"\x00" * 5))
        self.assertIn("error", result)


class TestParseSettings(unittest.TestCase):
    def test_known_values(self):
        # general=0x88 (3_speed=128, ai_enabled=8), cell_model=2, reversal=4,
        # ai_water_turns=3, acid_pump=1, filter_pump=2, default_speed=2
        general = 128 | 8  # three_speed_pump | ai_enabled
        data = struct.pack("<HBBBBBB", general, 2, 4, 3, 1, 2, 2)
        result = parse_data_payload(_make_raw(0x0064, data))
        self.assertEqual(result["type"], "settings")
        self.assertTrue(result["three_speed_pump"])
        self.assertTrue(result["ai_enabled"])
        self.assertFalse(result["dosing_enabled"])
        self.assertEqual(result["cell_model"], 2)
        self.assertEqual(result["reversal_period"], 4)


class TestParseControllerTime(unittest.TestCase):
    def test_known_values(self):
        data = bytes([30, 45, 14, 3])  # sec=30, min=45, hour=14, weekday=3
        result = parse_data_payload(_make_raw(0x0002, data))
        self.assertEqual(result["type"], "controller_time")
        self.assertEqual(result["controller_second"], 30)
        self.assertEqual(result["controller_minute"], 45)
        self.assertEqual(result["controller_hour"], 14)
        self.assertEqual(result["controller_weekday"], 3)


class TestParseControllerDate(unittest.TestCase):
    def test_known_values(self):
        data = bytes([15, 6, 26])  # day=15, month=6, year=26 → 2026
        result = parse_data_payload(_make_raw(0x0003, data))
        self.assertEqual(result["type"], "controller_date")
        self.assertEqual(result["controller_day"], 15)
        self.assertEqual(result["controller_month"], 6)
        self.assertEqual(result["controller_year"], 2026)


class TestParseDataPayloadIntegration(unittest.TestCase):
    def test_full_state_payload_has_all_keys(self):
        state_data = struct.pack("<BBHBBHBBBxx", 0x02, 5, 1000, 5, 0, 700, 3, 74, 0) + b"\x00" * 5
        raw = _make_raw(0x0068, state_data)
        result = parse_data_payload(raw)
        self.assertEqual(result["cmd_id"], 0x0068)
        self.assertEqual(result["cmd_hex"], "0x0068")
        self.assertIn("prefix", result)
        self.assertIn("data_len", result)
        self.assertEqual(result["type"], "state")
        self.assertIn("info_message", result)

    def test_config_0x0324_sub00_action_low(self):
        # sub_command=0x00, pad, pad, pad, action_code=4 (Low)
        data = bytes([0x00, 0x00, 0x00, 0x00, 0x04])
        result = parse_data_payload(_make_raw(0x0324, data))
        self.assertEqual(result.get("type"), "config")
        self.assertEqual(result.get("pump_speed"), "Low")

    def test_config_0x0324_sub03_speed_high(self):
        # sub_command=0x03, pad, speed_code=2 (High)
        data = bytes([0x03, 0x00, 0x02])
        result = parse_data_payload(_make_raw(0x0324, data))
        self.assertEqual(result.get("type"), "config")
        self.assertEqual(result.get("pump_speed"), "High")

    def test_0x00ca_timer_pump_speed_mapping(self):
        for code, speed in ((0, "Low"), (1, "Medium"), (2, "High")):
            with self.subTest(code=code):
                result = parse_data_payload(_make_raw(0x00CA, bytes([code, 0x00])))
                self.assertEqual(result.get("type"), "timer_pump_speed")
                self.assertEqual(result.get("timer_pump_speed_code"), code)
                self.assertEqual(result.get("timer_pump_speed"), speed)
                self.assertEqual(result.get("transition_index"), code)
                self.assertEqual(result.get("index"), code)
                self.assertEqual(result.get("raw_data_hex"), f"{code:02x}00")

    def test_0x0192_timer_state_next_profile_index(self):
        result = parse_data_payload(_make_raw(0x0192, bytes([3, 4])))
        self.assertEqual(result.get("type"), "timer_state")
        self.assertEqual(result.get("profile_index"), 3)
        self.assertEqual(result.get("next_profile_index"), 4)

    def test_unknown_cmd_id(self):
        result = parse_data_payload(_make_raw(0xDEAD, b"\x00\x00"))
        self.assertIn("unknown", result.get("type", ""))

    def test_too_short_payload(self):
        result = parse_data_payload(b"\x03\x68")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
