"""Tests for coordinator backoff and circuit-breaker logic.

HomeAssistant is not installed in the test environment; we stub the required
modules before importing the coordinator.
"""

from __future__ import annotations

import asyncio
import datetime
import sys
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub homeassistant modules before any import of the coordinator
# ---------------------------------------------------------------------------
_HA_MODULES = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.const",
    "homeassistant.core",
    "homeassistant.helpers",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.entity_platform",
    "homeassistant.components",
    "homeassistant.components.select",
    "homeassistant.exceptions",
    "homeassistant.util",
    "homeassistant.util.dt",
]
for _mod in _HA_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# callback must be a pass-through decorator
_core_mock = MagicMock()
_core_mock.callback = lambda f: f
_core_mock.CoreState = MagicMock()
_core_mock.HomeAssistant = MagicMock
_core_mock.CALLBACK_TYPE = MagicMock
sys.modules["homeassistant.core"] = _core_mock

_const_mock = MagicMock()
_const_mock.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
sys.modules["homeassistant.const"] = _const_mock

# Patch DataUpdateCoordinator to a subscriptable no-op base class.
class _StubDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        pass
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
    def __class_getitem__(cls, item):
        return cls

_coord_mock = MagicMock()
_coord_mock.DataUpdateCoordinator = _StubDataUpdateCoordinator
sys.modules["homeassistant.helpers.update_coordinator"] = _coord_mock

from custom_components.astralpool_halo_cloud.coordinator import (  # noqa: E402
    HaloCloudCoordinator,
    _JITTER_MAX_SECONDS,
    _RECONNECT_BACKOFF_MAX,
    _SHORT_SESSION_CIRCUIT_BREAKER_BACKOFF,
    _SHORT_SESSION_LIMIT,
    _SHORT_SESSION_SECONDS,
    _SHORT_SESSION_WINDOW_SECONDS,
)


def _make_coordinator() -> HaloCloudCoordinator:
    """Build a minimally mocked coordinator without a live HA instance."""
    mock_hass = MagicMock()
    mock_hass.loop = asyncio.new_event_loop()
    mock_hass.state = MagicMock()
    mock_hass.is_running = False

    mock_entry = MagicMock()
    mock_entry.data = {
        "serial_number": "TEST123",
        "username": "testuser",
        "password": "testpass",
        "device_name": "Test Halo",
    }

    coord = HaloCloudCoordinator.__new__(HaloCloudCoordinator)
    # Manually initialise only the fields we need
    coord._entry = mock_entry
    coord._shutdown_event = asyncio.Event()
    coord._connection_task = None
    coord._startup_task = None
    coord._started_listener = None
    coord._connect_lock = asyncio.Lock()
    coord._wake_event = asyncio.Event()
    coord._last_connection_issue = None
    coord._pause_until = None
    coord._pending_publish = None
    coord._reconnect_backoff_override = None
    coord._next_connect_at = None
    coord._short_session_disconnects = []
    coord.hass = mock_hass

    from pychlorinator_cloud.websocket_client import HaloWebSocketClient
    coord.client = HaloWebSocketClient("TEST123", "testuser", "testpass")

    return coord


class TestComputeBackoff(unittest.TestCase):
    def _coord(self) -> HaloCloudCoordinator:
        return _make_coordinator()

    def test_backoff_60_within_expected_range(self):
        coord = self._coord()
        result = coord._compute_backoff(60)
        jitter_max = min(_JITTER_MAX_SECONDS, max(1, int(60 * 0.1)))
        self.assertGreaterEqual(result, 60)
        self.assertLessEqual(result, 60 + jitter_max)

    def test_backoff_at_max_capped(self):
        coord = self._coord()
        result = coord._compute_backoff(_RECONNECT_BACKOFF_MAX)
        # Result may be slightly above max due to jitter but is capped
        self.assertLessEqual(result, _RECONNECT_BACKOFF_MAX)

    def test_backoff_above_max_capped(self):
        coord = self._coord()
        result = coord._compute_backoff(2000)
        self.assertLessEqual(result, _RECONNECT_BACKOFF_MAX)

    def test_backoff_small_value_has_minimum_jitter_ceiling(self):
        coord = self._coord()
        result = coord._compute_backoff(5)
        self.assertGreaterEqual(result, 5)
        self.assertLessEqual(result, 5 + _JITTER_MAX_SECONDS)


class TestShortSessionCircuitBreaker(unittest.TestCase):
    def _coord(self) -> HaloCloudCoordinator:
        return _make_coordinator()

    def _trigger_short_session(self, coord: HaloCloudCoordinator) -> int | None:
        coord.client.last_session_duration_seconds = _SHORT_SESSION_SECONDS - 1
        return coord._short_session_reconnect_delay()

    def test_single_short_session_no_circuit_break(self):
        coord = self._coord()
        result = self._trigger_short_session(coord)
        self.assertIsNone(result)
        self.assertEqual(len(coord._short_session_disconnects), 1)

    def test_two_short_sessions_no_circuit_break(self):
        coord = self._coord()
        for _ in range(_SHORT_SESSION_LIMIT - 1):
            result = self._trigger_short_session(coord)
        self.assertIsNone(result)

    def test_limit_reached_triggers_circuit_breaker(self):
        coord = self._coord()
        result = None
        for _ in range(_SHORT_SESSION_LIMIT):
            result = self._trigger_short_session(coord)
        self.assertEqual(result, _SHORT_SESSION_CIRCUIT_BREAKER_BACKOFF)

    def test_long_session_clears_history(self):
        coord = self._coord()
        # First add some short sessions
        for _ in range(_SHORT_SESSION_LIMIT - 1):
            self._trigger_short_session(coord)
        self.assertGreater(len(coord._short_session_disconnects), 0)
        # Now a long session
        coord.client.last_session_duration_seconds = _SHORT_SESSION_SECONDS + 10
        result = coord._short_session_reconnect_delay()
        self.assertIsNone(result)
        self.assertEqual(len(coord._short_session_disconnects), 0)

    def test_none_duration_does_not_trigger(self):
        coord = self._coord()
        coord.client.last_session_duration_seconds = None
        result = coord._short_session_reconnect_delay()
        self.assertIsNone(result)

    def test_old_disconnects_outside_window_are_pruned(self):
        coord = self._coord()
        # Manually insert old disconnects outside the window
        old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            seconds=_SHORT_SESSION_WINDOW_SECONDS + 60
        )
        coord._short_session_disconnects = [old_time] * (_SHORT_SESSION_LIMIT - 1)
        # One new short session should not trigger circuit breaker
        result = self._trigger_short_session(coord)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
