"""Tests for equipment timer summary restore across HA restarts."""

from __future__ import annotations

import datetime
import json
import sys
from typing import Any

import pytest

from pychlorinator_cloud.websocket_client import (
    TIMER_CONFIG_CMD_ID,
    ChlorinatorLiveData,
    HaloWebSocketClient,
)
from test_equipment_timer_write import (
    _install_ha_stubs,
    _make_coordinator,
    _reload_ha_module,
)


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


def _sensor_module():
    _install_ha_stubs()
    return _reload_ha_module("custom_components.astralpool_halo_cloud.sensor")


def _timer_summary_entity(sensor_module, data: ChlorinatorLiveData | None = None):
    coordinator = _make_coordinator()
    if data is not None:
        coordinator.data = data
        coordinator.client.data = data
    description = next(
        desc
        for desc in sensor_module.SENSOR_DESCRIPTIONS
        if desc.key == "equipment_timer_summary"
    )
    return sensor_module.HaloCloudRestoringSensor(coordinator, description)


def _realistic_attrs() -> dict[str, Any]:
    return {
        "season": "Summer",
        "current_season": "Summer",
        "season_source": "state",
        "profile_index": 2,
        "equipment_timer_slots": 8,
        "winter_slots": [
            {
                "slot_index": 0,
                "season": "Winter",
                "active": True,
                "start_hour": 7,
                "start_minute": 15,
                "stop_hour": 9,
                "stop_minute": 45,
                "equipment_flags": 0x0002,
                "equipment_enabled": ["FilterPump"],
                "speed": "Medium",
            }
        ],
        "summer_slots": [
            {
                "slot_index": 0,
                "season": "Summer",
                "active": False,
                "start_hour": 6,
                "start_minute": 0,
                "stop_hour": 8,
                "stop_minute": 0,
                "equipment_flags": 0x0802,
                "equipment_enabled": ["FilterPump", "Relay1"],
                "speed": "High",
            },
            {
                "slot_index": 3,
                "season": "Summer",
                "active": True,
                "start_hour": 18,
                "start_minute": 30,
                "stop_hour": 20,
                "stop_minute": 0,
                "equipment_flags": 0x0004,
                "equipment_enabled": ["Heater"],
                "speed": "Low",
            },
        ],
        "slot_labels": {"0": "Timer 1", "3": "Timer 4"},
        "equipment_catalog": [
            {
                "key": "FilterPump",
                "label": "Filter",
                "present": True,
                "kind": "builtin",
            }
        ],
        "timer_config_last_seen": "2026-05-21T01:14:00+00:00",
    }


def test_restore_timer_summary_attrs_hydrates_live_data() -> None:
    sensor_module = _sensor_module()
    entity = _timer_summary_entity(sensor_module, ChlorinatorLiveData())

    restored = entity._restore_timer_summary_attrs(_realistic_attrs())
    data = entity.coordinator.data

    assert restored is True
    assert data.timer_configs_winter[0]["start_hour"] == 7
    assert data.timer_configs_summer[3]["equipment_enabled"] == ["Heater"]
    assert data.timer_season == "Summer"
    assert data.timer_season_source == "state"
    assert data.timer_profile_index == 2
    assert data.equipment_timer_slots == 8
    assert data.cmd_last_seen[0x0193] == datetime.datetime(
        2026, 5, 21, 1, 14, tzinfo=datetime.timezone.utc
    )
    assert data.timer_summary_restored is True
    assert data.timer_summary_restored_from == "2026-05-21T01:14:00+00:00"
    assert data.timer_summary_restored_equipment_catalog == [
        {
            "key": "FilterPump",
            "label": "Filter",
            "present": True,
            "kind": "builtin",
        }
    ]
    assert data.timer_summary_restored_slot_labels == {
        "0": "Timer 1",
        "3": "Timer 4",
    }


def test_timer_summary_attributes_emit_restore_flags() -> None:
    sensor_module = _sensor_module()
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.timer_configs_summer[0] = {"slot_index": 0, "active": True}
    data.timer_summary_restored = True
    data.timer_summary_restored_from = "2026-05-21T01:14:00+00:00"

    attrs = sensor_module._timer_summary_attributes(data)

    assert attrs["restored"] is True
    assert attrs["restored_from_at"] == "2026-05-21T01:14:00+00:00"


def test_coerce_slots_with_string_slot_index() -> None:
    sensor_module = _sensor_module()
    entity = _timer_summary_entity(sensor_module, ChlorinatorLiveData())

    restored = entity._restore_timer_summary_attrs(
        {
            "season": "Winter",
            "winter_slots": [
                {"slot_index": "0", "active": True, "equipment_flags": 0x0002},
                {"slot_index": "1", "active": False, "equipment_flags": 0x0004},
            ],
        }
    )
    data = entity.coordinator.data

    assert restored is True
    assert sorted(data.timer_configs_winter) == [0, 1]
    assert all(isinstance(slot_index, int) for slot_index in data.timer_configs_winter)
    assert data.timer_configs_winter[0]["equipment_flags"] == 0x0002
    assert data.timer_configs_winter[1]["equipment_flags"] == 0x0004


def test_summary_attrs_no_slots_key() -> None:
    sensor_module = _sensor_module()
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.timer_configs_winter[0] = {"slot_index": 0, "season": "Winter"}
    data.timer_configs_summer[0] = {"slot_index": 0, "season": "Summer"}

    attrs = sensor_module._timer_summary_attributes(data)

    assert "slots" not in attrs
    assert attrs["winter_slots"] == [{"slot_index": 0, "season": "Winter"}]
    assert attrs["summer_slots"] == [{"slot_index": 0, "season": "Summer"}]


def test_summary_attrs_payload_under_cap() -> None:
    sensor_module = _sensor_module()
    data = ChlorinatorLiveData()
    data.timer_season = "Summer"
    data.timer_season_source = "state"
    data.timer_profile_index = 2
    data.equipment_timer_slots = 8
    data.lighting_timer_slots = 4
    data.timer_capability_flags = [0x01, 0x02, 0x08, 0x10]
    data.spa_selection = True
    data.valve_enabled = {index: True for index in range(1, 5)}
    data.valve_names = {
        index: f"Valve {index} water feature"
        for index in range(1, 5)
    }
    data.valve_is_custom_name = {index: True for index in range(1, 5)}
    data.valve_custom_names = {
        index: f"Custom valve {index + 1}"
        for index in range(4)
    }
    data.gpo_enabled = {index: True for index in range(1, 5)}
    data.gpo_names = {
        index: f"Outlet {index} accessory"
        for index in range(1, 5)
    }
    equipment_keys = [
        "PoolSpa",
        "FilterPump",
        "Heater",
        "Valve1",
        "Valve2",
        "Valve3",
        "Valve4",
        "Outlet1",
        "Outlet2",
        "Outlet3",
        "Outlet4",
        "Relay1",
        "Relay2",
    ]
    for season, slots in (
        ("Winter", data.timer_configs_winter),
        ("Summer", data.timer_configs_summer),
    ):
        for slot_index in range(8):
            slots[slot_index] = {
                "slot_index": slot_index,
                "season": season,
                "active": slot_index % 2 == 0,
                "enabled": slot_index % 2 == 0,
                "start_hour": (5 + slot_index) % 24,
                "start_minute": (slot_index * 7) % 60,
                "stop_hour": (7 + slot_index) % 24,
                "stop_minute": (slot_index * 11) % 60,
                "equipment_flags": 0x1FFF,
                "equipment_enabled": equipment_keys,
                "speed": "High" if slot_index % 3 == 0 else "Medium",
            }

    attrs = sensor_module._timer_summary_attributes(data)
    payload_size = len(json.dumps(attrs, separators=(",", ":"), default=str))

    assert payload_size < 12_000


def test_timer_config_readback_clears_restore_flags() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")
    client.data.timer_summary_restored = True
    client.data.timer_summary_restored_from = "2026-05-21T01:14:00+00:00"
    client.data.timer_summary_restored_equipment_catalog = [{"key": "FilterPump"}]
    client.data.timer_summary_restored_slot_labels = {"0": "Timer 1"}

    client._update_data(
        {
            "cmd_id": TIMER_CONFIG_CMD_ID,
            "type": "timer_config",
            "slot_index": 0,
            "season": "Summer",
            "active": True,
            "equipment_flags": 0x0002,
        },
        b"timer-config",
    )

    assert client.data.timer_summary_restored is False
    assert client.data.timer_summary_restored_from is None
    assert client.data.timer_summary_restored_equipment_catalog is None
    assert client.data.timer_summary_restored_slot_labels is None


def test_timer_summary_attrs_round_trip_preserves_relevant_fields() -> None:
    sensor_module = _sensor_module()
    data1 = ChlorinatorLiveData()
    data1.timer_season = "Summer"
    data1.timer_season_source = "state"
    data1.timer_profile_index = 4
    data1.equipment_timer_slots = 8
    data1.timer_configs_winter[0] = {
        "slot_index": 0,
        "season": "Winter",
        "active": False,
        "equipment_flags": 0x0002,
    }
    data1.timer_configs_summer[2] = {
        "slot_index": 2,
        "season": "Summer",
        "active": True,
        "equipment_flags": 0x0802,
        "speed": "High",
    }
    data1.cmd_last_seen[0x0193] = datetime.datetime(
        2026, 5, 21, 1, 14, tzinfo=datetime.timezone.utc
    )

    attrs = sensor_module._timer_summary_attributes(data1)
    entity = _timer_summary_entity(sensor_module, ChlorinatorLiveData())
    assert entity._restore_timer_summary_attrs(attrs) is True
    data2 = entity.coordinator.data

    assert data2.timer_season == data1.timer_season
    assert data2.timer_season_source == data1.timer_season_source
    assert data2.timer_profile_index == data1.timer_profile_index
    assert data2.equipment_timer_slots == data1.equipment_timer_slots
    assert data2.timer_configs_winter == data1.timer_configs_winter
    assert data2.timer_configs_summer == data1.timer_configs_summer
    assert data2.cmd_last_seen[0x0193] == data1.cmd_last_seen[0x0193]


def test_restore_timer_summary_attrs_tolerates_malformed_input() -> None:
    sensor_module = _sensor_module()
    entity = _timer_summary_entity(sensor_module, ChlorinatorLiveData())

    restored = entity._restore_timer_summary_attrs(
        {
            "season": "Winter",
            "season_source": 123,
            "profile_index": True,
            "equipment_timer_slots": "8",
            "timer_config_last_seen": "not-a-timestamp",
            "winter_slots": [
                {"slot_index": "not-an-int", "active": True},
                {"slot_index": True, "active": True},
                ["not", "a", "dict"],
            ],
        }
    )

    assert restored is False
    assert entity.coordinator.data.timer_configs_winter == {}
    assert entity.coordinator.data.cmd_last_seen.get(0x0193) is None
    assert entity.coordinator.data.timer_summary_restored is False


def test_restore_timer_summary_attrs_accepts_summer_without_winter_slots() -> None:
    sensor_module = _sensor_module()
    entity = _timer_summary_entity(sensor_module, ChlorinatorLiveData())

    restored = entity._restore_timer_summary_attrs(
        {
            "season": "Summer",
            "summer_slots": [{"slot_index": 1, "active": True}],
            "timer_config_last_seen": "2026-05-21T01:14:00+00:00",
        }
    )

    assert restored is True
    assert entity.coordinator.data.timer_configs_winter == {}
    assert entity.coordinator.data.timer_configs_summer == {
        1: {"slot_index": 1, "active": True}
    }
