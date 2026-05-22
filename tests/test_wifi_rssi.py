"""Tests for chlorinator-side WiFi RSSI live data and sensor exposure."""

from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from types import ModuleType
from unittest.mock import MagicMock

from pychlorinator_cloud.websocket_client import ChlorinatorLiveData, HaloWebSocketClient


class WifiRssiLiveDataTests(unittest.TestCase):
    def test_dataclass_field_defaults_to_none(self) -> None:
        data = ChlorinatorLiveData()

        self.assertIsNone(data.wifi_rssi_dbm)

    def test_valid_preflight_response_populates_rssi(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        payload = {
            "avail": 1,
            "connectivityinfo": {"wifirssi": -70, "interface": 1},
        }

        client._update_rssi_from_payload(payload)

        self.assertEqual(client.data.wifi_rssi_dbm, -70)

    def test_out_of_range_rssi_values_are_rejected(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")

        client._update_rssi_from_payload({"connectivityinfo": {"wifirssi": 99}})
        self.assertIsNone(client.data.wifi_rssi_dbm)

        client.data.wifi_rssi_dbm = -71
        client._update_rssi_from_payload({"connectivityinfo": {"wifirssi": -999}})
        self.assertEqual(client.data.wifi_rssi_dbm, -71)

    def test_wrong_type_rssi_values_are_rejected(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")

        client._update_rssi_from_payload({"connectivityinfo": {"wifirssi": "strong"}})
        self.assertIsNone(client.data.wifi_rssi_dbm)

        client.data.wifi_rssi_dbm = -72
        client._update_rssi_from_payload({"connectivityinfo": {"wifirssi": None}})
        self.assertEqual(client.data.wifi_rssi_dbm, -72)


def _install_homeassistant_stubs() -> None:
    """Install minimal Home Assistant module stubs for importing sensor.py."""
    modules = [
        "homeassistant",
        "homeassistant.components",
        "homeassistant.config_entries",
        "homeassistant.const",
        "homeassistant.core",
        "homeassistant.exceptions",
        "homeassistant.helpers",
        "homeassistant.helpers.device_registry",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.entity_registry",
        "homeassistant.helpers.restore_state",
        "homeassistant.helpers.update_coordinator",
        "homeassistant.util",
    ]
    for name in modules:
        sys.modules.setdefault(name, ModuleType(name))

    sensor_module = ModuleType("homeassistant.components.sensor")

    class EntityCategory:
        DIAGNOSTIC = "diagnostic"

    class SensorDeviceClass:
        SIGNAL_STRENGTH = "signal_strength"
        TEMPERATURE = "temperature"
        TIMESTAMP = "timestamp"
        VOLUME_STORAGE = "volume_storage"
        ENUM = "enum"
        PH = "ph"
        DURATION = "duration"

    class SensorStateClass:
        MEASUREMENT = "measurement"
        TOTAL = "total"
        TOTAL_INCREASING = "total_increasing"

    class SensorEntity:
        pass

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str = ""
        name: str = ""
        icon: str | None = None
        native_unit_of_measurement: str | None = None
        device_class: object | None = None
        state_class: object | None = None
        entity_category: object | None = None
        entity_registry_enabled_default: bool = True
        options: list[str] | None = None

    sensor_module.EntityCategory = EntityCategory
    sensor_module.SensorDeviceClass = SensorDeviceClass
    sensor_module.SensorEntity = SensorEntity
    sensor_module.SensorEntityDescription = SensorEntityDescription
    sensor_module.SensorStateClass = SensorStateClass
    sys.modules["homeassistant.components.sensor"] = sensor_module

    const_module = sys.modules["homeassistant.const"]
    const_module.EVENT_HOMEASSISTANT_STARTED = "homeassistant_started"
    const_module.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
    const_module.UnitOfElectricCurrent = MagicMock(AMPERE="A", MILLIAMPERE="mA")
    const_module.UnitOfTemperature = MagicMock(CELSIUS="C")
    const_module.UnitOfTime = MagicMock(MINUTES="min", HOURS="h", DAYS="d")
    const_module.UnitOfVolume = MagicMock(LITERS="L")

    core_module = sys.modules["homeassistant.core"]
    core_module.CALLBACK_TYPE = object
    core_module.CoreState = MagicMock()
    core_module.HomeAssistant = MagicMock
    core_module.ServiceCall = MagicMock
    core_module.callback = lambda f: f

    config_entries_module = sys.modules["homeassistant.config_entries"]
    config_entries_module.ConfigEntry = MagicMock

    exceptions_module = sys.modules["homeassistant.exceptions"]

    class HomeAssistantError(Exception):
        pass

    exceptions_module.HomeAssistantError = HomeAssistantError

    helpers_module = sys.modules["homeassistant.helpers"]
    helpers_module.device_registry = sys.modules["homeassistant.helpers.device_registry"]
    helpers_module.entity_registry = sys.modules["homeassistant.helpers.entity_registry"]

    device_registry_module = sys.modules["homeassistant.helpers.device_registry"]
    device_registry_module.DeviceInfo = dict
    device_registry_module.async_get = MagicMock()
    device_registry_module.async_entries_for_config_entry = MagicMock(return_value=[])

    entity_registry_module = sys.modules["homeassistant.helpers.entity_registry"]
    entity_registry_module.async_get = MagicMock()

    entity_platform_module = sys.modules["homeassistant.helpers.entity_platform"]
    entity_platform_module.AddEntitiesCallback = MagicMock

    restore_state_module = sys.modules["homeassistant.helpers.restore_state"]

    class RestoreEntity:
        pass

    restore_state_module.RestoreEntity = RestoreEntity

    update_coordinator_module = sys.modules["homeassistant.helpers.update_coordinator"]

    class CoordinatorEntity:
        def __init__(self, coordinator) -> None:
            self.coordinator = coordinator

        def __class_getitem__(cls, item):
            return cls

    class DataUpdateCoordinator:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __class_getitem__(cls, item):
            return cls

    update_coordinator_module.CoordinatorEntity = CoordinatorEntity
    update_coordinator_module.DataUpdateCoordinator = DataUpdateCoordinator

    util_module = sys.modules["homeassistant.util"]
    util_module.slugify = lambda value: value.lower().replace(" ", "_")


class WifiRssiSensorDescriptionTests(unittest.TestCase):
    def test_sensor_entity_description_exists(self) -> None:
        _install_homeassistant_stubs()

        from custom_components.astralpool_halo_cloud.sensor import (  # noqa: PLC0415
            SENSOR_DESCRIPTIONS,
        )

        description = next(
            item for item in SENSOR_DESCRIPTIONS if item.key == "wifi_rssi"
        )

        self.assertEqual(description.name, "WiFi Signal Strength")
        self.assertEqual(description.device_class, "signal_strength")
        self.assertEqual(description.native_unit_of_measurement, "dBm")
        self.assertEqual(description.state_class, "measurement")
        self.assertEqual(description.entity_category, "diagnostic")
        self.assertTrue(description.entity_registry_enabled_default)
        self.assertFalse(description.restore_on_startup)
        self.assertEqual(description.value_fn(ChlorinatorLiveData(wifi_rssi_dbm=-70)), -70)
