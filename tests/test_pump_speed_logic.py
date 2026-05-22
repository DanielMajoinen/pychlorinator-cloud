"""Tests for pump speed state machine logic in HaloWebSocketClient._update_data."""

from __future__ import annotations

import struct
import unittest

from pychlorinator_cloud.payload_parsers import parse_data_payload
from pychlorinator_cloud.websocket_client import HaloWebSocketClient


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


def _state_raw(
    flags: int = 0,
    cell_level: int = 0,
    cell_current_ma: int = 1000,
    main_text: int = 5,
    sub1: int = 0,
    orp_mv: int = 700,
    sub2: int = 3,
    ph_raw: int = 74,
    sub3: int = 0,
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
    ) + b"\x00\x00\x00\x00\x00")
    data[1] = (flags >> 8) & 0xFF if flags > 0xFF else cell_level
    return _make_raw(0x0068, bytes(data))


def _config_speed_raw(sub_command: int, action_or_speed_code: int) -> bytes:
    if sub_command == 0x00:
        # data: [sub_command, 0x00, 0x00, 0x00, action_code]
        data = bytes([sub_command, 0x00, 0x00, 0x00, action_or_speed_code])
    else:
        # sub_command=0x03: [sub_command, 0x00, speed_code]
        data = bytes([sub_command, 0x00, action_or_speed_code])
    return _make_raw(0x0324, data)


def _timer_pump_speed_raw(code: int) -> bytes:
    return _make_raw(0x00CA, bytes([code, 0x00]))


def _timer_state_raw(profile_index: int, next_profile_index: int = 0) -> bytes:
    return _make_raw(0x0192, bytes([profile_index, next_profile_index]))


def _feed(client: HaloWebSocketClient, raw: bytes) -> None:
    parsed = parse_data_payload(raw)
    client._update_data(parsed, raw)


class TestPumpSpeedLogic(unittest.TestCase):
    def _client(self) -> HaloWebSocketClient:
        return HaloWebSocketClient("TEST_SERIAL", "testuser", "testpass")

    def test_standby_gives_auto_mode_and_no_operating_speed(self):
        client = self._client()
        _feed(client, _state_raw(main_text=5))  # Standby
        self.assertEqual(client.data.mode, "Auto")
        self.assertFalse(client.data.pump_is_operating)
        self.assertIsNone(client.data.current_operating_speed)

    def test_sanitising_gives_on_mode(self):
        client = self._client()
        _feed(client, _state_raw(main_text=1))  # Sanitising
        self.assertEqual(client.data.mode, "On")
        self.assertTrue(client.data.pump_is_operating)

    def test_off_gives_off_mode(self):
        client = self._client()
        _feed(client, _state_raw(main_text=0))  # Off
        self.assertEqual(client.data.mode, "Off")
        self.assertFalse(client.data.pump_is_operating)

    def test_config_sub00_action_does_not_set_pump_speed(self):
        """sub=0x00 carries the stale manual-speed action-code echo, NOT
        live state. It must NOT update pump_speed. prior to this fix the
        carousel cycle between sub=0x00 (echo Medium) and sub=0x03
        (authoritative High) caused a visible Medium↔High flap in the HA
        selector every 5-10s (observed during live testing 2026-05-21).
        """
        client = self._client()
        _feed(client, _state_raw(main_text=1))  # Sanitising → On
        _feed(client, _config_speed_raw(0x00, 6))  # action_code=6 → High
        # pump_speed stays None; sub=0x00 is now diagnostic-only.
        self.assertIsNone(client.data.pump_speed)

    def test_config_sub00_does_not_override_sub03_authoritative(self):
        """Carousel race: sub=0x03 sets the authoritative speed; a
        subsequent stale sub=0x00 must NOT overwrite it. This was the
        observed Medium↔High flap.
        """
        client = self._client()
        _feed(client, _state_raw(main_text=1))
        _feed(client, _config_speed_raw(0x03, 2))  # authoritative High
        self.assertEqual(client.data.pump_speed, "High")
        _feed(client, _config_speed_raw(0x00, 5))  # stale Medium echo
        self.assertEqual(client.data.pump_speed, "High")  # NOT flipped
        _feed(client, _config_speed_raw(0x03, 2))  # next carousel rotation
        self.assertEqual(client.data.pump_speed, "High")

    def test_low_speed_no_chlorinating_sets_low_and_on(self):
        client = self._client()
        _feed(client, _state_raw(main_text=15))  # LowSpeedNoChlorinating
        self.assertEqual(client.data.mode, "On")
        self.assertEqual(client.data.pump_speed, "Low")
        self.assertEqual(client.data.current_operating_speed, "Low")

    def test_conflict_guard_during_low_speed_no_chlorinating(self):
        """A non-Low sub=0x03 config update during LowSpeedNoChlorinating
        is ignored implicitly because sub=0x03 only writes when received,
        and the LowSpeedNoChlorinating state path already sets Low.

        (sub=0x00 no longer touches pump_speed at all, so the original
        conflict-guard concern only matters for sub=0x03 now.)
        """
        client = self._client()
        _feed(client, _state_raw(main_text=15))  # LowSpeedNoChlorinating
        self.assertEqual(client.data.pump_speed, "Low")
        # Stale sub=0x00 echo while in LowSpeedNoChlorinating. no effect.
        _feed(client, _config_speed_raw(0x00, 5))
        self.assertEqual(client.data.pump_speed, "Low")

    def test_ai_mode_active_gives_ai_operating_speed(self):
        client = self._client()
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        _feed(client, _state_raw(flags=flags, main_text=2))  # AIModeSanitising
        self.assertTrue(client.data.ai_mode_active)
        self.assertEqual(client.data.mode, "Auto")
        self.assertEqual(client.data.current_operating_speed, "AI")

    def test_ai_speed_requires_auto_mode_not_manual_on(self):
        client = self._client()
        # Use sub=0x03 (authoritative) to seed Medium. sub=0x00 no longer
        # touches pump_speed (Medium↔High flap fix).
        _feed(client, _config_speed_raw(0x03, 1))  # Medium
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        _feed(client, _state_raw(flags=flags, main_text=1))  # Sanitising -> On
        self.assertEqual(client.data.mode, "On")
        self.assertTrue(client.data.ai_mode_active)
        self.assertTrue(client.data.pump_is_operating)
        self.assertEqual(client.data.pump_speed, "Medium")
        self.assertEqual(client.data.current_operating_speed, "Medium")

    def test_ai_speed_in_auto_mode_still_works(self):
        client = self._client()
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        _feed(client, _state_raw(flags=flags, main_text=2))  # AIModeSanitising
        self.assertEqual(client.data.mode, "Auto")
        self.assertTrue(client.data.ai_mode_active)
        self.assertTrue(client.data.pump_is_operating)
        self.assertEqual(client.data.current_operating_speed, "AI")

    def test_ai_flag_stale_in_off_mode_ignored(self):
        client = self._client()
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        _feed(client, _state_raw(flags=flags, main_text=0))  # Off
        self.assertEqual(client.data.mode, "Off")
        self.assertTrue(client.data.ai_mode_active)
        self.assertFalse(client.data.pump_is_operating)
        self.assertIsNone(client.data.current_operating_speed)

    def test_priming_wins_over_ai_in_auto(self):
        client = self._client()
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        data = bytearray(_state_raw(flags=flags, main_text=2)[3:])
        data[10] = 7  # timer_info=PrimingFor
        data[11] = 120
        data[12] = 2
        _feed(client, _make_raw(0x0068, bytes(data)))
        self.assertEqual(client.data.mode, "Auto")
        self.assertTrue(client.data.ai_mode_active)
        self.assertTrue(client.data.priming_active)
        self.assertEqual(client.data.current_operating_speed, "Priming")

    def test_current_operating_speed_uses_manual_pump_speed_in_on_mode(self):
        client = self._client()
        _feed(client, _state_raw(main_text=1))  # Sanitising → On
        # Seed via sub=0x03 (authoritative). sub=0x00 no longer drives
        # pump_speed (Medium↔High flap fix).
        _feed(client, _config_speed_raw(0x03, 2))  # High
        # Feed another state while still in On
        _feed(client, _state_raw(main_text=1))
        self.assertEqual(client.data.current_operating_speed, "High")

    def test_sub03_seeds_pump_speed_when_unknown(self):
        client = self._client()
        self.assertIsNone(client.data.pump_speed)
        _feed(client, _config_speed_raw(0x03, 2))  # speed_code=2 → High
        self.assertEqual(client.data.pump_speed, "High")

    def test_sub03_updates_known_pump_speed(self):
        """sub=0x03 is the authoritative source. Multiple sub=0x03 updates
        from the carousel rotation should each overwrite pump_speed,
        so the selector tracks vendor-app changes and fresh-connect state.
        """
        client = self._client()
        _feed(client, _state_raw(main_text=1))
        _feed(client, _config_speed_raw(0x03, 1))  # Medium
        self.assertEqual(client.data.pump_speed, "Medium")
        # Next carousel rotation lands with authoritative Low.
        _feed(client, _config_speed_raw(0x03, 0))  # Low
        self.assertEqual(client.data.pump_speed, "Low")

    def test_auto_running_without_ai_or_timer_does_not_fabricate_speed(self):
        """In Auto without AI/timer evidence, don't surface a stale manual speed."""
        client = self._client()
        _feed(client, _config_speed_raw(0x03, 2))  # speed_code 2 → High
        self.assertEqual(client.data.pump_speed, "High")
        _feed(client, _state_raw(main_text=8))
        self.assertEqual(client.data.mode, "Auto")
        self.assertTrue(client.data.pump_is_operating)
        self.assertIsNone(client.data.current_operating_speed)

    def test_auto_standby_keeps_operating_speed_unknown(self):
        """In Auto-Standby (idle), don't fabricate a running speed."""
        client = self._client()
        _feed(client, _config_speed_raw(0x03, 1))  # Medium configured
        _feed(client, _state_raw(main_text=5))  # Standby
        self.assertEqual(client.data.mode, "Auto")
        self.assertFalse(client.data.pump_is_operating)
        self.assertIsNone(client.data.current_operating_speed)

    def test_ai_flag_wins_over_auto_running_fallback(self):
        """AI mode flag takes precedence over retained/configured speed."""
        client = self._client()
        _feed(client, _config_speed_raw(0x03, 2))  # High configured
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        _feed(client, _state_raw(flags=flags, main_text=8))  # Auto + AI + running
        self.assertEqual(client.data.mode, "Auto")
        self.assertTrue(client.data.ai_mode_active)
        self.assertEqual(client.data.current_operating_speed, "AI")

    def test_ai_flag_wins_when_timer_profile_index_is_zero(self):
        client = self._client()
        _feed(client, _timer_state_raw(0, 0))
        flags = 0x800  # FLAG_AI_MODE_ACTIVE
        _feed(client, _state_raw(flags=flags, main_text=2))  # AI + running, no active timer profile
        self.assertEqual(client.data.timer_profile_index, 0)
        self.assertTrue(client.data.ai_mode_active)
        self.assertTrue(client.data.pump_is_operating)
        self.assertEqual(client.data.current_operating_speed, "AI")

    def test_timer_profile_uses_0x00ca_timer_pump_speed(self):
        client = self._client()
        _feed(client, _state_raw(main_text=5))  # Auto standby baseline
        _feed(client, _timer_pump_speed_raw(1))  # Medium retained/current timer speed
        _feed(client, _timer_state_raw(3, 4))  # Active profile
        self.assertEqual(client.data.timer_pump_speed, "Medium")
        self.assertEqual(client.data.timer_pump_speed_code, 1)
        self.assertEqual(client.data.timer_profile_index, 3)
        self.assertEqual(client.data.timer_next_profile_index, 4)
        self.assertEqual(client.data.current_operating_speed, "Medium")

    def test_timer_profile_zero_does_not_surface_retained_0x00ca_speed(self):
        client = self._client()
        _feed(client, _timer_pump_speed_raw(2))  # High retained from previous timer run
        _feed(client, _timer_state_raw(0, 1))  # Idle/off profile pointer
        _feed(client, _state_raw(main_text=5))  # Standby
        self.assertEqual(client.data.timer_pump_speed, "High")
        self.assertIsNone(client.data.current_operating_speed)

    def test_priming_wins_as_operating_speed(self):
        client = self._client()
        data = bytearray(_state_raw(main_text=1)[3:])
        data[10] = 7  # timer_info=PrimingFor
        data[11] = 120
        data[12] = 2
        _feed(client, _make_raw(0x0068, bytes(data)))
        _feed(client, _timer_pump_speed_raw(0))  # Low retained value must not beat priming
        self.assertTrue(client.data.priming_active)
        self.assertEqual(client.data.priming_countdown, 120)
        self.assertEqual(client.data.priming_phase_code, 2)
        self.assertEqual(client.data.current_operating_speed, "Priming")


class TestHasSettledBootstrapSnapshot(unittest.TestCase):
    def _client(self) -> HaloWebSocketClient:
        return HaloWebSocketClient("TEST_SERIAL", "testuser", "testpass")

    def test_fresh_client_not_settled(self):
        client = self._client()
        self.assertFalse(client._has_settled_bootstrap_snapshot())

    def test_auto_mode_settles(self):
        client = self._client()
        _feed(client, _state_raw(main_text=5))  # Standby → Auto
        self.assertTrue(client._has_settled_bootstrap_snapshot())

    def test_off_mode_settles(self):
        client = self._client()
        _feed(client, _state_raw(main_text=0))  # Off
        self.assertTrue(client._has_settled_bootstrap_snapshot())

    def test_on_mode_not_settled_without_speed(self):
        client = self._client()
        _feed(client, _state_raw(main_text=1))  # Sanitising → On
        # No manual speed seen yet
        self.assertFalse(client._has_settled_bootstrap_snapshot())

    def test_on_mode_settles_after_manual_speed(self):
        client = self._client()
        _feed(client, _state_raw(main_text=1))  # On
        # sub=0x03 (authoritative) is the only path that marks the manual
        # speed as seen now. sub=0x00 no longer touches pump_speed.
        _feed(client, _config_speed_raw(0x03, 2))  # High via sub03
        self.assertTrue(client._has_settled_bootstrap_snapshot())


if __name__ == "__main__":
    unittest.main()
