"""Tests verifying entity availability contracts.

Verifies that:
- Read-only base entities remain available after first payload (last-known reads)
- Control entities require data.connected = True to be available

HomeAssistant is not installed; we stub the required modules before importing.
"""

from __future__ import annotations

import datetime
import sys
import unittest
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub homeassistant modules
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
    "homeassistant.components.number",
    "homeassistant.components.select",
    "homeassistant.components.binary_sensor",
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

# CoordinatorEntity and DataUpdateCoordinator both need to be subscriptable.
class _StubCoordinatorEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
    def __class_getitem__(cls, item):
        return cls

class _StubDataUpdateCoordinator:
    def __init__(self, *args, **kwargs):
        pass
    def __class_getitem__(cls, item):
        return cls

_centry_module = MagicMock()
_centry_module.CoordinatorEntity = _StubCoordinatorEntity
_centry_module.DataUpdateCoordinator = _StubDataUpdateCoordinator
sys.modules["homeassistant.helpers.update_coordinator"] = _centry_module

# Stub SelectEntity and SelectEntityDescription as proper base classes
from dataclasses import dataclass as _dataclass  # noqa: E402

class _StubSelectEntity:
    pass

@_dataclass(frozen=True, kw_only=True)
class _StubSelectEntityDescription:
    key: str = ""
    name: str = ""
    options: list = None
    entity_registry_enabled_default: bool = True
    def __class_getitem__(cls, item):
        return cls

_select_module = MagicMock()
_select_module.SelectEntity = _StubSelectEntity
_select_module.SelectEntityDescription = _StubSelectEntityDescription
sys.modules["homeassistant.components.select"] = _select_module

# Stub NumberEntity / NumberEntityDescription / NumberMode as proper base classes
class _StubNumberEntity:
    pass

@_dataclass(frozen=True, kw_only=True)
class _StubNumberEntityDescription:
    key: str = ""
    name: str = ""
    icon: str | None = None
    native_unit_of_measurement: str | None = None
    native_min_value: float | int | None = None
    native_max_value: float | int | None = None
    native_step: float | int | None = None
    mode: object | None = None
    entity_category: object | None = None
    entity_registry_enabled_default: bool = True
    def __class_getitem__(cls, item):
        return cls

class _StubNumberMode:
    SLIDER = "slider"
    BOX = "box"

_number_module = MagicMock()
_number_module.NumberEntity = _StubNumberEntity
_number_module.NumberEntityDescription = _StubNumberEntityDescription
_number_module.NumberMode = _StubNumberMode
sys.modules["homeassistant.components.number"] = _number_module

# Stub BinarySensorEntity / EntityDescription / DeviceClass as proper base classes
class _StubBinarySensorEntity:
    pass

@_dataclass(frozen=True, kw_only=True)
class _StubBinarySensorEntityDescription:
    key: str = ""
    name: str = ""
    icon: str | None = None
    device_class: object | None = None
    entity_category: object | None = None
    entity_registry_enabled_default: bool = True
    def __class_getitem__(cls, item):
        return cls

class _StubBinarySensorDeviceClass:
    CONNECTIVITY = "connectivity"
    PROBLEM = "problem"
    RUNNING = "running"
    POWER = "power"
    HEAT = "heat"
    BATTERY = "battery"
    OPENING = "opening"

_binary_sensor_module = MagicMock()
_binary_sensor_module.BinarySensorEntity = _StubBinarySensorEntity
_binary_sensor_module.BinarySensorEntityDescription = _StubBinarySensorEntityDescription
_binary_sensor_module.BinarySensorDeviceClass = _StubBinarySensorDeviceClass
sys.modules["homeassistant.components.binary_sensor"] = _binary_sensor_module

# Stub HomeAssistantError
_exc_module = MagicMock()
class _StubHAError(Exception):
    pass
_exc_module.HomeAssistantError = _StubHAError
sys.modules["homeassistant.exceptions"] = _exc_module

# slugify stub
_util_module = MagicMock()
_util_module.slugify = lambda s: s.lower().replace(" ", "_")
sys.modules["homeassistant.util"] = _util_module

from pychlorinator_cloud.websocket_client import ChlorinatorLiveData  # noqa: E402
from custom_components.astralpool_halo_cloud.entity import HaloCloudEntity  # noqa: E402
from custom_components.astralpool_halo_cloud.select import (  # noqa: E402
    HEATER_SELECT_DESCRIPTION,
    HaloActionSelect,
    HaloModeSelect,
    HaloPumpSpeedSelect,
    HaloConnectionPauseSelect,
)
from custom_components.astralpool_halo_cloud.number import (  # noqa: E402
    NUMBER_DESCRIPTIONS,
    HaloCloudSetpointNumber,
)


def _make_coordinator(connected: bool = False, has_data: bool = True) -> MagicMock:
    """Return a mock coordinator with controllable data state."""
    coord = MagicMock()
    data = ChlorinatorLiveData()
    if has_data:
        data.last_update = datetime.datetime.now(datetime.timezone.utc)
    data.connected = connected
    data.mode = "Auto" if has_data else None
    coord.data = data
    coord.client = MagicMock()
    coord.client.data = data
    coord._entry = MagicMock()
    coord._entry.data = {
        "serial_number": "TEST123",
        "username": "testuser",
        "password": "testpass",
        "device_name": "Test Halo",
    }
    return coord


class TestBaseEntityAvailability(unittest.TestCase):
    def test_unavailable_before_first_payload(self):
        coord = _make_coordinator(has_data=False)
        desc = MagicMock()
        desc.key = "test_key"
        desc.name = "Test"
        entity = HaloCloudEntity(coord, desc)
        self.assertFalse(entity.available)

    def test_available_after_first_payload_even_when_disconnected(self):
        """Base entity stays available (last-known reads) when cloud disconnects."""
        coord = _make_coordinator(connected=False, has_data=True)
        desc = MagicMock()
        desc.key = "test_key"
        desc.name = "Test"
        entity = HaloCloudEntity(coord, desc)
        self.assertTrue(entity.available)

    def test_available_when_connected(self):
        coord = _make_coordinator(connected=True, has_data=True)
        desc = MagicMock()
        desc.key = "test_key"
        desc.name = "Test"
        entity = HaloCloudEntity(coord, desc)
        self.assertTrue(entity.available)


class TestModeSelectAvailability(unittest.TestCase):
    def test_unavailable_when_disconnected(self):
        coord = _make_coordinator(connected=False, has_data=True)
        entity = HaloModeSelect(coord)
        self.assertFalse(entity.available)

    def test_available_when_connected_with_data(self):
        coord = _make_coordinator(connected=True, has_data=True)
        entity = HaloModeSelect(coord)
        self.assertTrue(entity.available)

    def test_unavailable_when_no_data_yet(self):
        coord = _make_coordinator(connected=True, has_data=False)
        entity = HaloModeSelect(coord)
        self.assertFalse(entity.available)


class TestPumpSpeedSelectAvailability(unittest.TestCase):
    def test_unavailable_when_disconnected(self):
        coord = _make_coordinator(connected=False, has_data=True)
        coord.data.mode = "On"
        entity = HaloPumpSpeedSelect(coord)
        self.assertFalse(entity.available)

    def test_unavailable_when_mode_is_not_on(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.mode = "Auto"  # Not manual On
        entity = HaloPumpSpeedSelect(coord)
        self.assertFalse(entity.available)

    def test_available_when_connected_and_mode_on(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.mode = "On"
        coord.data.pump_speed = "High"
        entity = HaloPumpSpeedSelect(coord)
        self.assertTrue(entity.available)

    def test_available_when_speed_known_even_if_mode_off(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.mode = "Off"
        coord.data.pump_speed = "Low"
        entity = HaloPumpSpeedSelect(coord)
        self.assertTrue(entity.available)

    def test_unavailable_when_speed_unknown(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.mode = "On"
        coord.data.pump_speed = None
        entity = HaloPumpSpeedSelect(coord)
        self.assertFalse(entity.available)


class TestActionSelectAvailability(unittest.TestCase):
    def test_heater_select_requires_own_readback_only(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.ph_setpoint = None
        coord.data.orp_setpoint = None
        coord.data.pool_chlorine_setpoint = None
        coord.data.acid_setpoint = None
        coord.data.spa_chlorine_setpoint = None
        coord.data.heater_mode = "On"
        entity = HaloActionSelect(coord, HEATER_SELECT_DESCRIPTION)
        self.assertTrue(entity.available)

    def test_heater_select_unavailable_until_own_readback(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.heater_mode = None
        entity = HaloActionSelect(coord, HEATER_SELECT_DESCRIPTION)
        self.assertFalse(entity.available)


class TestSetpointNumberAvailability(unittest.TestCase):
    def _number(self, key: str, coord: MagicMock) -> HaloCloudSetpointNumber:
        description = next(desc for desc in NUMBER_DESCRIPTIONS if desc.key == key)
        return HaloCloudSetpointNumber(coord, description)

    def test_heater_number_requires_only_heater_setpoint(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.ph_setpoint = None
        coord.data.orp_setpoint = None
        coord.data.pool_chlorine_setpoint = None
        coord.data.acid_setpoint = None
        coord.data.spa_chlorine_setpoint = None
        coord.data.heater_setpoint_c = 28
        entity = self._number("heater_setpoint_control", coord)
        self.assertTrue(entity.available)

    def test_heater_number_unavailable_until_heater_setpoint(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.heater_setpoint_c = None
        entity = self._number("heater_setpoint_control", coord)
        self.assertFalse(entity.available)

    def test_ph_number_does_not_require_spa_setpoint(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.ph_setpoint = 7.4
        coord.data.spa_chlorine_setpoint = None
        entity = self._number("ph_setpoint_control", coord)
        self.assertTrue(entity.available)

    def test_orp_number_requires_only_orp_setpoint(self):
        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.ph_setpoint = None
        coord.data.orp_setpoint = 650
        coord.data.pool_chlorine_setpoint = None
        coord.data.acid_setpoint = None
        coord.data.spa_chlorine_setpoint = None
        entity = self._number("orp_setpoint_control", coord)
        self.assertTrue(entity.available)


if __name__ == "__main__":
    unittest.main()


class TestConnectionPauseSelectAvailability(unittest.TestCase):
    def test_always_available_when_connected(self):
        coord = _make_coordinator(connected=True, has_data=True)
        entity = HaloConnectionPauseSelect(coord)
        self.assertTrue(entity.available)

    def test_always_available_when_disconnected(self):
        """Must be available even when cloud is not connected (that's the point)."""
        coord = _make_coordinator(connected=False, has_data=True)
        entity = HaloConnectionPauseSelect(coord)
        self.assertTrue(entity.available)

    def test_always_available_with_no_data(self):
        coord = _make_coordinator(connected=False, has_data=False)
        entity = HaloConnectionPauseSelect(coord)
        self.assertTrue(entity.available)

    def test_current_option_idle_label_when_not_paused(self):
        # Cosmetic fix (2026-05-06): Connection Hold returns the stable
        # "Connected" idle label instead of None when not paused, so HA does
        # not render "unknown" for this select.
        coord = _make_coordinator(connected=True, has_data=True)
        coord.is_connection_paused = False
        entity = HaloConnectionPauseSelect(coord)
        self.assertEqual(entity.current_option, "Connected")

    def test_current_option_resume_when_paused(self):
        coord = _make_coordinator(connected=False, has_data=True)
        coord.is_connection_paused = True
        entity = HaloConnectionPauseSelect(coord)
        self.assertEqual(entity.current_option, "Resume connection")


class TestBinarySensorPreDataWindow(unittest.TestCase):
    """match_error/match_info/match_info_any must return None pre-data."""

    def test_match_error_returns_none_when_error_message_unset(self):
        from pychlorinator_cloud.websocket_client import ChlorinatorLiveData
        from custom_components.astralpool_halo_cloud.binary_sensor import match_error
        data = ChlorinatorLiveData()  # error_message starts as None
        self.assertIsNone(match_error(data, "NoFlow"))
        data.error_message = "NoError"
        self.assertFalse(match_error(data, "NoFlow"))
        data.error_message = "NoFlow"
        self.assertTrue(match_error(data, "NoFlow"))

    def test_match_info_returns_none_when_info_message_unset(self):
        from pychlorinator_cloud.websocket_client import ChlorinatorLiveData
        from custom_components.astralpool_halo_cloud.binary_sensor import match_info
        data = ChlorinatorLiveData()
        self.assertIsNone(match_info(data, "Standby"))
        data.info_message = "Sanitising"
        self.assertFalse(match_info(data, "Standby"))
        data.info_message = "Standby"
        self.assertTrue(match_info(data, "Standby"))

    def test_match_info_any_returns_none_when_info_message_unset(self):
        from pychlorinator_cloud.websocket_client import ChlorinatorLiveData
        from custom_components.astralpool_halo_cloud.binary_sensor import match_info_any
        data = ChlorinatorLiveData()
        self.assertIsNone(match_info_any(data, {"Sanitising", "AIModeSanitising"}))
        data.info_message = "Standby"
        self.assertFalse(match_info_any(data, {"Sanitising", "AIModeSanitising"}))
        data.info_message = "AIModeSanitising"
        self.assertTrue(match_info_any(data, {"Sanitising", "AIModeSanitising"}))


class TestLightZoneCapabilityAvailability(unittest.TestCase):
    """Light zone entities are hidden when 0x012D says the hardware lacks them."""

    def test_binary_zone_above_reported_count_is_unavailable(self):
        from custom_components.astralpool_halo_cloud.binary_sensor import (
            BINARY_SENSOR_DESCRIPTIONS,
            HaloCloudBinarySensor,
        )

        coord = _make_coordinator(connected=True, has_data=True)
        coord.data.lighting_enabled = True
        coord.data.lighting_num_zones_in_use = 1
        desc = next(
            description
            for description in BINARY_SENSOR_DESCRIPTIONS
            if description.key == "light_zone3_on"
        )

        entity = HaloCloudBinarySensor(coord, desc)

        self.assertFalse(entity.available)

    def test_binary_zones_stay_available_until_capabilities_arrive(self):
        from custom_components.astralpool_halo_cloud.binary_sensor import (
            BINARY_SENSOR_DESCRIPTIONS,
            HaloCloudBinarySensor,
        )

        coord = _make_coordinator(connected=True, has_data=True)
        desc = next(
            description
            for description in BINARY_SENSOR_DESCRIPTIONS
            if description.key == "light_zone4_on"
        )

        entity = HaloCloudBinarySensor(coord, desc)

        self.assertTrue(entity.available)


class TestControlTypeFields(unittest.TestCase):
    """Control-type fields are parser-backed by 0x0069 capabilities."""

    def test_ph_control_type_field_exists(self):
        from pychlorinator_cloud.websocket_client import ChlorinatorLiveData
        data = ChlorinatorLiveData()
        self.assertTrue(hasattr(data, "ph_control_type"))

    def test_chlorine_control_type_field_exists(self):
        from pychlorinator_cloud.websocket_client import ChlorinatorLiveData
        data = ChlorinatorLiveData()
        self.assertTrue(hasattr(data, "chlorine_control_type"))
