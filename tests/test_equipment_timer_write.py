"""Tests for equipment timer writes and timer-slot readback."""

from __future__ import annotations

import asyncio
import datetime
import importlib
import logging
import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pychlorinator_cloud.payload_parsers import parse_data_payload
from pychlorinator_cloud.websocket_client import (
    EQUIPMENT_ENABLE_MASKS,
    EQUIPMENT_NAMES,
    TIMER_CONFIG_CMD_ID,
    ChlorinatorLiveData,
    HaloWebSocketClient,
    build_equipment_timer_payload,
)


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix, cmd_id & 0xFF, (cmd_id >> 8) & 0xFF]) + data


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _sleep(_delay_seconds: float) -> None:
        return None

    monkeypatch.setattr("pychlorinator_cloud.websocket_client._sleep_briefly", _sleep)


@pytest.fixture(autouse=True)
def restore_ha_modules():
    """Keep local Home Assistant stubs from leaking into other test modules."""
    original = {
        name: module
        for name, module in sys.modules.items()
        if name == "homeassistant"
        or name.startswith("homeassistant.")
        or name.startswith("custom_components.astralpool_halo_cloud")
    }
    yield
    for name in [
        name
        for name in sys.modules
        if name == "homeassistant"
        or name.startswith("homeassistant.")
        or name.startswith("custom_components.astralpool_halo_cloud")
    ]:
        sys.modules.pop(name, None)
    sys.modules.update(original)


def _sent_payload(sent: list[bytes]) -> bytes:
    assert len(sent) == 1
    assert sent[0][0] == 0x03
    assert sent[0][1:3] == bytes([0x93, 0x01])
    return sent[0][3:16]


def test_payload_construction_known_good_config() -> None:
    payload = build_equipment_timer_payload(
        season="Summer",
        slot_index=0,
        enabled=True,
        start_hour=6,
        start_min=0,
        stop_hour=18,
        stop_min=0,
        equipment=["FilterPump", "PoolSpa"],
        pump_speed="Medium",
    )

    assert payload == bytes(
        [0, 0, 1, 1, 0x03, 0x00, 0, 6, 0, 0, 18, 0, 2]
    )


def test_enables_mask_empty_and_all_equipment() -> None:
    empty = build_equipment_timer_payload(
        season="Winter",
        slot_index=0,
        enabled=False,
        start_hour=0,
        start_min=0,
        stop_hour=0,
        stop_min=0,
        equipment=[],
    )
    all_equipment = build_equipment_timer_payload(
        season="Winter",
        slot_index=0,
        enabled=False,
        start_hour=0,
        start_min=0,
        stop_hour=0,
        stop_min=0,
        equipment=EQUIPMENT_NAMES,
    )

    assert empty[4:6] == b"\x00\x00"
    assert all_equipment[4:6] == b"\xff\x1f"


@pytest.mark.parametrize("name", EQUIPMENT_NAMES)
def test_single_equipment_masks(name: str) -> None:
    payload = build_equipment_timer_payload(
        season="Winter",
        slot_index=0,
        enabled=False,
        start_hour=0,
        start_min=0,
        stop_hour=0,
        stop_min=0,
        equipment=[name],
    )
    enables = payload[4] | (payload[5] << 8)
    assert enables == EQUIPMENT_ENABLE_MASKS[name]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"slot_index": -1}, "slot_index"),
        ({"slot_index": 8}, "slot_index"),
        ({"start_hour": 24}, "start_hour"),
        ({"stop_min": 60}, "stop_min"),
        ({"equipment": ["BoardCleaner"]}, "BoardCleaner"),
        ({"start_mode": "Sunrise"}, "start_mode"),
        ({"season": "Spring"}, "season"),
        ({"pump_speed": "Ultra"}, "pump_speed"),
    ],
)
def test_validation_rejects_invalid_values(kwargs: dict[str, object], message: str) -> None:
    config = dict(
        season="Winter",
        slot_index=0,
        enabled=True,
        start_hour=6,
        start_min=0,
        start_mode="Normal",
        stop_hour=18,
        stop_min=0,
        stop_mode="Normal",
        equipment=["FilterPump"],
        pump_speed="Medium",
    )
    config.update(kwargs)

    with pytest.raises(ValueError, match=message):
        build_equipment_timer_payload(**config)  # type: ignore[arg-type]


@pytest.mark.parametrize("start_mode", ["Normal", "Dusk", "Dawn"])
@pytest.mark.parametrize("stop_mode", ["Normal", "Dusk", "Dawn"])
def test_mode_encoding_combinations(start_mode: str, stop_mode: str) -> None:
    payload = build_equipment_timer_payload(
        season="Winter",
        slot_index=0,
        enabled=False,
        start_hour=0,
        start_min=0,
        start_mode=start_mode,  # type: ignore[arg-type]
        stop_hour=1,
        stop_min=0,
        stop_mode=stop_mode,  # type: ignore[arg-type]
        equipment=[],
    )

    assert payload[6] == {"Normal": 0, "Dusk": 1, "Dawn": 2}[start_mode]
    assert payload[9] == {"Normal": 0, "Dusk": 1, "Dawn": 2}[stop_mode]


@pytest.mark.parametrize(("season", "encoded"), [("Winter", 0), ("Summer", 1)])
def test_season_encoding(season: str, encoded: int) -> None:
    payload = build_equipment_timer_payload(
        season=season,  # type: ignore[arg-type]
        slot_index=0,
        enabled=False,
        start_hour=0,
        start_min=0,
        stop_hour=0,
        stop_min=0,
        equipment=[],
    )
    assert payload[2] == encoded


@pytest.mark.parametrize(("speed", "encoded"), [("Low", 1), ("Medium", 2), ("High", 3)])
def test_pump_speed_encoding(speed: str, encoded: int) -> None:
    payload = build_equipment_timer_payload(
        season="Winter",
        slot_index=0,
        enabled=False,
        start_hour=0,
        start_min=0,
        stop_hour=0,
        stop_min=0,
        equipment=[],
        pump_speed=speed,  # type: ignore[arg-type]
    )
    assert payload[12] == encoded


@pytest.mark.asyncio
async def test_write_equipment_timer_sends_payload_and_verify_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    sent: list[bytes] = []
    reads: list[tuple[int, int, str]] = []

    async def send_command(command_bytes: bytes, *, source: str = "command") -> None:
        sent.append(command_bytes)

    async def request_timer_config(
        *, timer_type: int, slot_index: int | None = None, season: str | None = None, **_: object
    ) -> None:
        assert slot_index is not None
        assert season is not None
        reads.append((timer_type, slot_index, season))
        client.data.timer_configs_summer[slot_index] = {
            "timer_type": 0,
            "slot_index": slot_index,
            "timer_mode": 1,
            "active": True,
            "equipment_flags": 3,
            "start_mode": 0,
            "start_hour": 6,
            "start_minute": 0,
            "stop_mode": 0,
            "stop_hour": 18,
            "stop_minute": 0,
            "speed_code": 2,
        }

    monkeypatch.setattr(client, "send_command", send_command)
    monkeypatch.setattr(client, "request_timer_config", request_timer_config)

    await client.write_equipment_timer(
        season="Summer",
        slot_index=0,
        enabled=True,
        start_hour=6,
        start_min=0,
        stop_hour=18,
        stop_min=0,
        equipment=["FilterPump", "PoolSpa"],
    )

    assert _sent_payload(sent) == bytes(
        [0, 0, 1, 1, 0x03, 0x00, 0, 6, 0, 0, 18, 0, 2]
    )
    assert reads == [(0, 0, "Summer")]


@pytest.mark.asyncio
async def test_readback_mismatch_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = HaloWebSocketClient("serial", "user", "pass")

    async def send_command(_command_bytes: bytes, *, source: str = "command") -> None:
        return None

    async def request_timer_config(**_: object) -> None:
        client.data.timer_configs_summer[0] = {
            "timer_type": 0,
            "slot_index": 0,
            "timer_mode": 1,
            "active": False,
            "equipment_flags": 0,
            "start_mode": 0,
            "start_hour": 6,
            "start_minute": 0,
            "stop_mode": 0,
            "stop_hour": 18,
            "stop_minute": 0,
            "speed_code": 2,
        }

    monkeypatch.setattr(client, "send_command", send_command)
    monkeypatch.setattr(client, "request_timer_config", request_timer_config)

    with caplog.at_level(logging.WARNING):
        await client.write_equipment_timer(
            season="Summer",
            slot_index=0,
            enabled=True,
            start_hour=6,
            start_min=0,
            stop_hour=18,
            stop_min=0,
            equipment=["FilterPump"],
        )

    assert "Equipment timer read-back mismatch" in caplog.text


@pytest.mark.asyncio
async def test_request_full_timer_config_sends_eight_selector_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    client.data.timer_season = "Summer"
    sent: list[bytes] = []

    async def send_command(command_bytes: bytes, *, source: str = "command") -> None:
        sent.append(command_bytes)

    monkeypatch.setattr(client, "send_command", send_command)

    await client.request_full_timer_config(source="startup_sweep")

    assert len(sent) == 8
    assert [payload[0] for payload in sent] == [0x02] * 8
    assert [payload[1:3] for payload in sent] == [bytes([0x93, 0x01])] * 8
    assert [(payload[3], payload[4], payload[5]) for payload in sent] == [
        (0, index, 1) for index in range(8)
    ]
    assert all(len(payload) == 20 for payload in sent)


def test_per_season_timer_config_dict_separation() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    winter = parse_data_payload(
        _make_raw(TIMER_CONFIG_CMD_ID, bytes([0, 1, 0, 1, 0x02, 0, 0, 6, 0, 0, 18, 0, 2]))
    )
    summer = parse_data_payload(
        _make_raw(TIMER_CONFIG_CMD_ID, bytes([0, 1, 1, 1, 0x04, 0, 0, 7, 0, 0, 19, 0, 3]))
    )

    client._update_data(winter, b"winter")
    client._update_data(summer, b"summer")

    assert client.data.timer_configs_winter[1]["equipment_flags"] == 0x02
    assert client.data.timer_configs_summer[1]["equipment_flags"] == 0x04
    client.data.timer_season = "Winter"
    assert client.data.timer_configs[1]["equipment_flags"] == 0x02
    client.data.timer_season = "Summer"
    assert client.data.timer_configs[1]["equipment_flags"] == 0x04


def _install_ha_stubs() -> type[Exception]:
    ha_modules = [
        "homeassistant",
        "homeassistant.components",
        "homeassistant.components.binary_sensor",
        "homeassistant.components.button",
        "homeassistant.components.select",
        "homeassistant.components.sensor",
        "homeassistant.config_entries",
        "homeassistant.const",
        "homeassistant.core",
        "homeassistant.exceptions",
        "homeassistant.helpers",
        "homeassistant.helpers.device_registry",
        "homeassistant.helpers.entity_registry",
        "homeassistant.helpers.entity_platform",
        "homeassistant.helpers.restore_state",
        "homeassistant.helpers.update_coordinator",
        "homeassistant.util",
    ]
    for module in ha_modules:
        sys.modules[module] = types.ModuleType(module)

    class HomeAssistantError(Exception):
        pass

    sys.modules["homeassistant.exceptions"].HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.core"].HomeAssistant = object
    sys.modules["homeassistant.core"].ServiceCall = object
    sys.modules["homeassistant.core"].CALLBACK_TYPE = object
    sys.modules["homeassistant.core"].CoreState = SimpleNamespace(running="running")
    sys.modules["homeassistant.core"].callback = lambda f: f
    sys.modules["homeassistant.config_entries"].ConfigEntry = object
    sys.modules["homeassistant.const"].EVENT_HOMEASSISTANT_STOP = "stop"
    sys.modules["homeassistant.const"].EVENT_HOMEASSISTANT_STARTED = "started"
    sys.modules["homeassistant.const"].UnitOfElectricCurrent = SimpleNamespace(
        MILLIAMPERE="mA"
    )
    sys.modules["homeassistant.const"].UnitOfTemperature = SimpleNamespace(
        CELSIUS="°C"
    )
    sys.modules["homeassistant.const"].UnitOfTime = SimpleNamespace(
        SECONDS="s",
        MINUTES="min",
        HOURS="h",
        DAYS="d",
    )
    sys.modules["homeassistant.const"].UnitOfVolume = SimpleNamespace(LITERS="L")

    class EntityCategory:
        CONFIG = "config"
        DIAGNOSTIC = "diagnostic"

    sys.modules["homeassistant.const"].EntityCategory = EntityCategory
    sys.modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object

    class SensorDeviceClass:
        ENUM = "enum"
        PH = "ph"
        SIGNAL_STRENGTH = "signal_strength"
        TEMPERATURE = "temperature"
        DURATION = "duration"
        TIMESTAMP = "timestamp"
        VOLUME_STORAGE = "volume_storage"

    class SensorStateClass:
        MEASUREMENT = "measurement"
        TOTAL_INCREASING = "total_increasing"
        TOTAL = "total"

    class SensorEntity:
        pass

    @dataclass(frozen=True, kw_only=True)
    class SensorEntityDescription:
        key: str = ""
        name: str = ""
        icon: str | None = None
        device_class: object | None = None
        state_class: object | None = None
        native_unit_of_measurement: str | None = None
        entity_category: object | None = None
        entity_registry_enabled_default: bool = True
        options: list[str] | None = None

    sys.modules["homeassistant.components.sensor"].SensorDeviceClass = SensorDeviceClass
    sys.modules["homeassistant.components.sensor"].EntityCategory = EntityCategory
    sys.modules["homeassistant.components.sensor"].SensorEntity = SensorEntity
    sys.modules["homeassistant.components.sensor"].SensorEntityDescription = SensorEntityDescription
    sys.modules["homeassistant.components.sensor"].SensorStateClass = SensorStateClass

    class ButtonEntity:
        pass

    @dataclass(frozen=True, kw_only=True)
    class ButtonEntityDescription:
        key: str = ""
        name: str = ""
        icon: str | None = None
        entity_category: object | None = None
        entity_registry_enabled_default: bool = True

    sys.modules["homeassistant.components.button"].ButtonEntity = ButtonEntity
    sys.modules["homeassistant.components.button"].ButtonEntityDescription = (
        ButtonEntityDescription
    )

    class BinarySensorDeviceClass:
        CONNECTIVITY = "connectivity"
        RUNNING = "running"
        OPENING = "opening"
        PROBLEM = "problem"
        LIGHT = "light"
        HEAT = "heat"

    class BinarySensorEntity:
        pass

    @dataclass(frozen=True, kw_only=True)
    class BinarySensorEntityDescription:
        key: str = ""
        name: str = ""
        icon: str | None = None
        device_class: object | None = None
        entity_category: object | None = None
        entity_registry_enabled_default: bool = True

    sys.modules[
        "homeassistant.components.binary_sensor"
    ].BinarySensorDeviceClass = BinarySensorDeviceClass
    sys.modules[
        "homeassistant.components.binary_sensor"
    ].BinarySensorEntity = BinarySensorEntity
    sys.modules[
        "homeassistant.components.binary_sensor"
    ].BinarySensorEntityDescription = BinarySensorEntityDescription

    class SelectEntity:
        pass

    @dataclass(frozen=True, kw_only=True)
    class SelectEntityDescription:
        key: str = ""
        name: str = ""
        options: list[str] | None = None
        entity_registry_enabled_default: bool = True

    sys.modules["homeassistant.components.select"].SelectEntity = SelectEntity
    sys.modules["homeassistant.components.select"].SelectEntityDescription = (
        SelectEntityDescription
    )

    class RestoreEntity:
        pass

    sys.modules["homeassistant.helpers.restore_state"].RestoreEntity = RestoreEntity

    class CoordinatorEntity:
        def __init__(self, coordinator: object) -> None:
            self.coordinator = coordinator

        def __class_getitem__(cls, _item: object) -> type:
            return cls

    sys.modules["homeassistant.helpers.update_coordinator"].CoordinatorEntity = (
        CoordinatorEntity
    )
    class DataUpdateCoordinator:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def __class_getitem__(cls, _item: object) -> type:
            return cls

    sys.modules["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = (
        DataUpdateCoordinator
    )
    sys.modules["homeassistant.helpers.device_registry"].DeviceInfo = dict

    def _stub_async_get(_hass: object) -> object:
        return SimpleNamespace(async_remove=lambda _entity_id: None)

    def _stub_entries_for_config_entry(_registry: object, _entry_id: str) -> list:
        return []

    sys.modules["homeassistant.helpers.entity_registry"].async_get = _stub_async_get
    sys.modules[
        "homeassistant.helpers.entity_registry"
    ].async_entries_for_config_entry = _stub_entries_for_config_entry
    sys.modules["homeassistant.util"].slugify = lambda value: value.lower().replace(" ", "_")

    util_dt = types.ModuleType("homeassistant.util.dt")
    util_dt.now = lambda: datetime.datetime.now(datetime.timezone.utc)
    util_dt.utcnow = lambda: datetime.datetime.now(datetime.timezone.utc)
    util_dt.as_local = lambda value: value
    sys.modules["homeassistant.util.dt"] = util_dt
    sys.modules["homeassistant.util"].dt = util_dt
    return HomeAssistantError


def _reload_ha_module(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def _make_coordinator() -> MagicMock:
    data = ChlorinatorLiveData()
    data.connected = True
    data.last_update = datetime.datetime.now(datetime.timezone.utc)
    data.timer_season = "Summer"
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.client = MagicMock()
    coordinator.client.data = data
    coordinator._entry = MagicMock()
    coordinator._entry.data = {
        "serial_number": "SERIAL",
        "username": "user",
        "password": "pass",
        "device_name": "Halo SERIAL",
    }
    coordinator.is_connection_paused = False
    return coordinator


def test_timer_season_select_entity() -> None:
    _install_ha_stubs()
    select_module = _reload_ha_module("custom_components.astralpool_halo_cloud.select")
    coordinator = _make_coordinator()
    coordinator.client.write_timer_season = AsyncMock()

    entity = select_module.HaloActionSelect(
        coordinator,
        select_module.TIMER_SEASON_SELECT_DESCRIPTION,
    )

    assert entity.current_option == "Summer"
    assert entity._attr_options == ["Winter", "Summer"]
    asyncio.run(entity.async_select_option("Winter"))
    coordinator.client.write_timer_season.assert_awaited_once_with("Winter")


def test_maintenance_period_options_match_acid_dosing_fixed_values() -> None:
    _install_ha_stubs()
    select_module = _reload_ha_module("custom_components.astralpool_halo_cloud.select")

    assert set(select_module.MAINTENANCE_PERIOD_MINUTES.values()) == set(
        select_module.ACID_DOSING_MINUTES.values()
    )
    assert list(select_module.MAINTENANCE_PERIOD_MINUTES.values()) == sorted(
        select_module.MAINTENANCE_PERIOD_MINUTES.values()
    )
    assert "Off indefinitely" not in select_module.MAINTENANCE_PERIOD_OPTIONS


def test_maintenance_period_select_runs_selected_program() -> None:
    _install_ha_stubs()
    select_module = _reload_ha_module("custom_components.astralpool_halo_cloud.select")
    coordinator = _make_coordinator()
    coordinator.client.start_filter_for_period = AsyncMock()

    entity = select_module.HaloMaintenancePeriodSelect(
        coordinator,
        key="filter_for_period",
        name="Filter For Period",
        action_fn="start_filter_for_period",
    )

    assert entity._attr_options == select_module.MAINTENANCE_PERIOD_OPTIONS
    assert entity.current_option is None
    asyncio.run(entity.async_select_option("6 hours"))
    coordinator.client.start_filter_for_period.assert_awaited_once_with(360)


def test_refresh_timer_button_triggers_sweep_and_rate_limits() -> None:
    HomeAssistantError = _install_ha_stubs()
    button_module = _reload_ha_module("custom_components.astralpool_halo_cloud.button")
    coordinator = _make_coordinator()
    coordinator.client.refresh_timer_config = AsyncMock(
        side_effect=[None, RuntimeError("Timer refresh rate-limited; try again in 30s")]
    )
    description = next(
        desc
        for desc in button_module.BUTTON_DESCRIPTIONS
        if desc.key == "refresh_timer_config"
    )
    entity = button_module.HaloCloudButton(coordinator, description)

    asyncio.run(entity.async_press())
    coordinator.client.refresh_timer_config.assert_awaited_once()
    with pytest.raises(HomeAssistantError, match="rate-limited"):
        asyncio.run(entity.async_press())


def test_equipment_timer_summary_attributes_include_season_counts() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.timer_configs_winter[0] = {"active": True}
    data.timer_configs_summer[0] = {"active": False}
    data.timer_configs_summer[1] = {"active": True}

    attrs = sensor_module._timer_summary_attributes(data)

    assert attrs["current_season"] == "Summer"
    assert attrs["winter_slot_count_seen"] == 1
    assert attrs["summer_slot_count_seen"] == 2
    assert attrs["slot_count_seen"] == 2
    assert attrs["winter_slots"] == [{"active": True}]
    assert attrs["summer_slots"] == [{"active": False}, {"active": True}]


def test_slot_descriptor_disabled() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")

    assert sensor_module._slot_descriptor({"active": False}, []) == "Disabled"


def test_slot_descriptor_unconfigured() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")

    assert sensor_module._slot_descriptor(
        {"active": True, "equipment_enabled": []},
        [],
    ) == "Unconfigured"


def test_slot_descriptor_with_catalog() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")
    catalog = [
        {"key": "PoolSpa", "label": "Spa"},
        {"key": "FilterPump", "label": "Pool Pump"},
    ]

    assert sensor_module._slot_descriptor(
        {"active": True, "equipment_enabled": ["PoolSpa", "FilterPump"]},
        catalog,
    ) == "Spa, Pool Pump"


def test_slot_descriptor_catalog_miss() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")

    assert sensor_module._slot_descriptor(
        {"active": True, "equipment_enabled": ["UnknownThing"]},
        [],
    ) == "UnknownThing"


def test_slot_descriptor_custom_valve_name() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")

    assert sensor_module._slot_descriptor(
        {"active": True, "equipment_enabled": ["Valve1"]},
        [{"key": "Valve1", "label": "Backwash"}],
    ) == "Backwash"


def test_summary_attrs_includes_descriptors() -> None:
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.equipment_timer_slots = 8
    data.spa_selection = True
    data.valve_enabled = {1: True}
    data.valve_is_custom_name = {1: True}
    data.valve_custom_names = {0: "Backwash"}
    data.timer_configs_winter[0] = {
        "active": True,
        "slot_index": 0,
        "equipment_flags": 0x0080,
        "equipment_enabled": ["Valve1"],
    }
    data.timer_configs_winter[1] = {
        "active": False,
        "slot_index": 1,
        "equipment_flags": 0,
        "equipment_enabled": [],
    }
    data.timer_configs_summer[0] = {
        "active": True,
        "slot_index": 0,
        "equipment_flags": 0x0003,
        "equipment_enabled": ["PoolSpa", "FilterPump"],
    }
    data.timer_configs_summer[1] = {
        "active": True,
        "slot_index": 1,
        "equipment_flags": 0,
        "equipment_enabled": [],
    }

    attrs = sensor_module._timer_summary_attributes(data)

    assert attrs["slot_descriptors"] == {
        "0": "Spa, Filter",
        "1": "Unconfigured",
    }
    assert attrs["winter_slot_descriptors"] == {
        "0": "Backwash",
        "1": "Disabled",
    }
    assert attrs["summer_slot_descriptors"] == {
        "0": "Spa, Filter",
        "1": "Unconfigured",
    }


def test_equipment_timer_summary_attributes_include_card_metadata() -> None:
    """v0.3.0-beta.1 card UX additions: slot_labels (Timer N), per-chip
    equipment_catalog (key/label/present/kind), and timer_config_last_seen
    ISO timestamp. backs the bundled halo-timer-card refresh button,
    “updated Xm ago” badge, and hide-disconnected-equipment behaviour.
    """
    import datetime as _dt

    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.equipment_timer_slots = 8
    data.spa_selection = False
    # Valve 1 named + custom-labelled “Waterfall”, Valve 2 connected but no
    # custom name, Valves 3 + 4 absent. GPO 1 connected (Outlet “Blower”),
    # GPO 2/3/4 absent. Relays present per capability flag.
    data.valve_enabled = {1: True, 2: True}
    data.valve_names = {1: "Waterfall", 2: "Valve 2"}
    data.valve_is_custom_name = {1: True, 2: False}
    data.valve_custom_names = {0: "Waterfall"}
    data.gpo_enabled = {1: True}
    data.gpo_names = {1: "Blower"}
    seen_at = _dt.datetime(2026, 5, 21, 6, 30, 0, tzinfo=_dt.timezone.utc)
    data.cmd_last_seen[0x0193] = seen_at
    # Need at least one timer_config so the early-return doesn't fire.
    # Slot 0 has Relay1 (0x0800) selected. drives the relay-present derivation.
    data.timer_configs[0] = {
        "active": False,
        "slot_index": 0,
        "equipment_flags": 0x0800,
    }

    attrs = sensor_module._timer_summary_attributes(data)

    # Slot labels match the vendor app: Timer 1..Timer 8.
    assert attrs["slot_labels"]["0"] == "Timer 1"
    assert attrs["slot_labels"]["7"] == "Timer 8"
    # Last-seen ISO timestamp drives the “updated Xm ago” card badge.
    assert attrs["timer_config_last_seen"] == "2026-05-21T06:30:00+00:00"
    # Equipment catalog. 13 chip keys, present flag per-chip.
    catalog = {item["key"]: item for item in attrs["equipment_catalog"]}
    assert catalog["PoolSpa"]["present"] is True
    assert catalog["PoolSpa"]["label"] == "Pool/Spa"
    assert catalog["FilterPump"]["present"] is True
    assert catalog["Heater"]["present"] is True
    # Valve 1 surfaces the custom name; Valve 2 falls back to vendor name.
    assert catalog["Valve1"]["present"] is True
    assert catalog["Valve1"]["label"] == "Waterfall"
    assert catalog["Valve2"]["present"] is True
    assert catalog["Valve2"]["label"] == "Valve 2"
    # Valves 3, 4 absent. card hides these chips when not selected.
    assert catalog["Valve3"]["present"] is False
    assert catalog["Valve4"]["present"] is False
    # GPO 1 connected with custom name, others absent.
    assert catalog["Outlet1"]["present"] is True
    assert catalog["Outlet1"]["label"] == "Blower"
    assert catalog["Outlet2"]["present"] is False
    assert catalog["Outlet3"]["present"] is False
    assert catalog["Outlet4"]["present"] is False
    # Relay1 present because slot 0's equipment_flags has bit 0x0800 set;
    # Relay2 absent (bit 0x1000 not set on any observed slot).
    assert catalog["Relay1"]["present"] is True
    assert catalog["Relay2"]["present"] is False


def test_equipment_timer_summary_relay_absent_when_no_slot_uses_relay_bits() -> None:
    """Once we have slot data, relays are absent if no slot's equipment_flags
    sets the Relay1 (0x0800) or Relay2 (0x1000) bits."""
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.equipment_timer_slots = 8
    data.timer_configs[0] = {
        "active": False,
        "slot_index": 0,
        "equipment_flags": 0x0002,  # FilterPump only, no relay bits
    }

    catalog = {
        item["key"]: item
        for item in sensor_module._timer_summary_attributes(data)["equipment_catalog"]
    }
    assert catalog["Relay1"]["present"] is False
    assert catalog["Relay2"]["present"] is False


def test_equipment_timer_summary_relay_present_during_bootstrap() -> None:
    """Before any slot's equipment_flags has been observed, relay chips stay
    visible so the user can still configure them. Once real data arrives,
    the per-slot derivation takes over.

    Regression guard: live HA deploy of an earlier rev died with
    `TypeError: unsupported operand type(s) for &: 'list' and 'int'`
    because `timer_capability_flags` is a tuple[int, ...] from cmd 0x0190,
    not a scalar bitfield. The derivation now sources from the per-slot
    equipment_flags bytes (0x0193) and defaults relays to visible until
    real slot data is observed.
    """
    _install_ha_stubs()
    sensor_module = _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.equipment_timer_slots = 8
    # No equipment_flags field on any slot (mid-bootstrap).
    data.timer_configs[0] = {"active": False, "slot_index": 0}
    # Realistic cap-flags shape from the controller. a list of bytes.
    data.timer_capability_flags = [0x01, 0x02, 0x08, 0x10]

    # Must NOT raise on the cap-flags shape.
    attrs = sensor_module._timer_summary_attributes(data)
    catalog = {item["key"]: item for item in attrs["equipment_catalog"]}
    assert catalog["Relay1"]["present"] is True
    assert catalog["Relay2"]["present"] is True


@pytest.mark.asyncio
async def test_service_handler_valid_and_invalid_calls() -> None:
    HomeAssistantError = _install_ha_stubs()
    init_module = _reload_ha_module("custom_components.astralpool_halo_cloud.__init__")
    coordinator = _make_coordinator()
    coordinator.client.write_equipment_timer = AsyncMock()
    hass = SimpleNamespace(data={init_module.DOMAIN: {"entry": coordinator}})
    valid_call = SimpleNamespace(
        data={
            "season": "Summer",
            "slot_index": 0,
            "enabled": True,
            "start_hour": 6,
            "start_min": 0,
            "stop_hour": 18,
            "stop_min": 0,
            "equipment": ["FilterPump"],
        }
    )

    await init_module._async_handle_write_equipment_timer(hass, valid_call)

    coordinator.client.write_equipment_timer.assert_awaited_once_with(
        season="Summer",
        slot_index=0,
        enabled=True,
        start_hour=6,
        start_min=0,
        start_mode="Normal",
        stop_hour=18,
        stop_min=0,
        stop_mode="Normal",
        equipment=["FilterPump"],
        pump_speed="Medium",
    )

    coordinator.client.write_equipment_timer = AsyncMock(
        side_effect=ValueError("Invalid slot_index: 8")
    )
    bad_call = SimpleNamespace(data={**valid_call.data, "slot_index": 8})
    with pytest.raises(HomeAssistantError, match="slot_index"):
        await init_module._async_handle_write_equipment_timer(hass, bad_call)


def test_service_registration_schema() -> None:
    _install_ha_stubs()
    init_module = _reload_ha_module("custom_components.astralpool_halo_cloud.__init__")

    class Services:
        def __init__(self) -> None:
            self.registered: list[tuple[object, ...]] = []

        def has_service(self, _domain: str, _service: str) -> bool:
            return False

        def async_register(self, *args: object, **kwargs: object) -> None:
            self.registered.append(args + (kwargs,))

    hass = SimpleNamespace(services=Services())

    init_module._async_register_services(hass)

    by_name = {entry[1]: entry for entry in hass.services.registered}
    assert init_module.SERVICE_WRITE_EQUIPMENT_TIMER in by_name
    timer_entry = by_name[init_module.SERVICE_WRITE_EQUIPMENT_TIMER]
    assert timer_entry[0] == init_module.DOMAIN
    assert timer_entry[-1]["schema"] is init_module.WRITE_EQUIPMENT_TIMER_SCHEMA
    assert init_module.SERVICE_WRITE_HEAT_DEMAND in by_name
    hd_entry = by_name[init_module.SERVICE_WRITE_HEAT_DEMAND]
    assert hd_entry[0] == init_module.DOMAIN
    assert hd_entry[-1]["schema"] is init_module.WRITE_HEAT_DEMAND_SCHEMA
