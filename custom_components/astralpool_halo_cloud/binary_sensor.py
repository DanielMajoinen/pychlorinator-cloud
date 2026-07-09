"""Binary sensor platform for the AstralPool Halo Cloud integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import datetime

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .pychlorinator_cloud.websocket_client import ChlorinatorLiveData
from homeassistant.util import dt as dt_util

from .pychlorinator_cloud.error_codes import (
    controller_fault_active,
    controller_notice_active,
    error_info_attributes,
)

from .const import CONF_TIME_DRIFT_THRESHOLD_MINUTES, DOMAIN
from .coordinator import HaloCloudCoordinator
from .entity import HaloCloudEntity


SANITISING_INFO_MESSAGES = {
    "Sanitising",
    "AIModeSanitising",
    "SanitisingUntilFirstTimer",
    "SanitisingForPeriod",
    "SanitisingAndCleaningForPeriod",
}

SAMPLING_INFO_MESSAGES = {"Sampling", "AIModeSampling"}
LIGHT_DEVICE_CLASS = getattr(BinarySensorDeviceClass, "LIGHT", None)


def _light_zone_index_from_key(key: str) -> int | None:
    """Return the light zone index encoded in a binary sensor key, if any."""
    return {
        "light_zone1_on": 1,
        "light_zone2_on": 2,
        "light_zone3_on": 3,
        "light_zone4_on": 4,
    }.get(key)


def _light_zone_available(data: ChlorinatorLiveData, zone_index: int) -> bool:
    """Return whether a light zone exists on this controller."""
    if data.lighting_enabled is False:
        return False
    if data.lighting_num_zones_in_use is not None:
        return zone_index <= data.lighting_num_zones_in_use
    return True


def match_error(data: ChlorinatorLiveData, expected: str) -> bool | None:
    """Return whether the current error message matches the expected value.

    Returns ``None`` when the underlying error_message field has not yet been
    populated (pre-data window) so HA renders ``unknown`` instead of ``off``.
    """
    if data.error_message is None:
        return None
    return data.error_message == expected


def match_info(data: ChlorinatorLiveData, expected: str) -> bool | None:
    """Return whether the current info message matches the expected value.

    Returns ``None`` while data.info_message has not yet been populated.
    """
    if data.info_message is None:
        return None
    return data.info_message == expected


def match_info_any(data: ChlorinatorLiveData, expected_values: set[str]) -> bool | None:
    """Return whether the current info message matches any expected value.

    Returns ``None`` while data.info_message has not yet been populated.
    """
    if data.info_message is None:
        return None
    return data.info_message in expected_values


def controller_clock_drift_gt_threshold(
    data: ChlorinatorLiveData,
    threshold_minutes: float,
) -> bool | None:
    """Return whether the controller clock differs from HA by more than the configured threshold."""
    if data.controller_datetime is None:
        return None
    controller_dt = data.controller_datetime
    now = dt_util.now()
    if controller_dt.tzinfo is None:
        controller_dt = dt_util.as_local(
            controller_dt.replace(tzinfo=datetime.timezone.utc)
        )
    delta = abs((dt_util.as_local(controller_dt) - now).total_seconds())
    return delta > (threshold_minutes * 60)


@dataclass(frozen=True, kw_only=True)
class HaloBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Halo Cloud binary sensor."""

    value_fn: Callable[[ChlorinatorLiveData], bool | None]
    attributes_fn: Callable[[ChlorinatorLiveData], dict[str, object]] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[HaloBinarySensorEntityDescription, ...] = (
    HaloBinarySensorEntityDescription(
        key="connected",
        name="Cloud Connected",
        icon="mdi:cloud-check",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.connected,
    ),
    HaloBinarySensorEntityDescription(
        key="pump_operating",
        name="Pump Operating",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.pump_is_operating,
    ),
    HaloBinarySensorEntityDescription(
        key="pump_priming",
        name="Pump Priming",
        icon="mdi:timer-sand",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.priming_active,
    ),
    HaloBinarySensorEntityDescription(
        key="valve_0_active",
        name="Valve 0",
        icon="mdi:valve",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda data: data.valve_0_active,
    ),
    HaloBinarySensorEntityDescription(
        key="valve_1_active",
        name="Valve 1",
        icon="mdi:valve",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda data: data.valve_1_active,
    ),
    HaloBinarySensorEntityDescription(
        key="cell_operating",
        name="Cell Operating",
        icon="mdi:fuel-cell",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.cell_is_operating,
    ),
    HaloBinarySensorEntityDescription(
        key="cell_reversed",
        name="Cell Reversed",
        icon="mdi:swap-horizontal",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.cell_is_reversed,
    ),
    HaloBinarySensorEntityDescription(
        key="cell_reversing",
        name="Cell Reversing",
        icon="mdi:swap-horizontal-bold",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.cell_is_reversing,
    ),
    HaloBinarySensorEntityDescription(
        key="chemistry_values_current",
        name="Chemistry Values Current",
        icon="mdi:test-tube",
        value_fn=lambda data: data.chemistry_values_current,
    ),
    HaloBinarySensorEntityDescription(
        key="chemistry_values_valid",
        name="Chemistry Values Valid",
        icon="mdi:test-tube-check",
        value_fn=lambda data: data.chemistry_values_valid,
    ),
    HaloBinarySensorEntityDescription(
        key="sanitising_until_next_timer_tomorrow",
        name="Sanitising Until Next Timer Tomorrow",
        icon="mdi:timer-check-outline",
        value_fn=lambda data: data.sanitising_until_next_timer_tomorrow,
    ),
    HaloBinarySensorEntityDescription(
        key="cooling_fan_on",
        name="Cooling Fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.cooling_fan_on,
    ),
    HaloBinarySensorEntityDescription(
        key="dosing_pump_on",
        name="Dosing Pump",
        icon="mdi:beaker",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.dosing_pump_on,
    ),
    HaloBinarySensorEntityDescription(
        key="ai_mode_active",
        name="AI Mode Active",
        icon="mdi:brain",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.ai_mode_active,
    ),
    HaloBinarySensorEntityDescription(
        key="spa_selection",
        name="Spa Selected",
        icon="mdi:hot-tub",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.spa_selection,
    ),
    HaloBinarySensorEntityDescription(
        key="heater_on",
        name="Heater On",
        icon="mdi:fire",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda data: data.heater_on,
    ),
    # Gas-heater diagnostics from HeaterStateCharacteristic (0x044E). Parsed
    # all along but previously dropped before reaching HA; disabled by default
    # (most relevant for gas heaters).
    HaloBinarySensorEntityDescription(
        key="heater_flame",
        name="Heater Flame",
        icon="mdi:fire",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heater_flame,
    ),
    HaloBinarySensorEntityDescription(
        key="heater_pressure",
        name="Heater Water Pressure",
        icon="mdi:gauge",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heater_pressure,
    ),
    HaloBinarySensorEntityDescription(
        key="heater_gas_valve",
        name="Heater Gas Valve",
        icon="mdi:valve",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heater_gas_valve,
    ),
    HaloBinarySensorEntityDescription(
        key="heater_lockout",
        name="Heater Lockout",
        icon="mdi:lock-alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heater_lockout,
    ),
    HaloBinarySensorEntityDescription(
        key="heater_service_required",
        name="Heater Service Required",
        icon="mdi:wrench-clock",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heater_service_required,
    ),
    HaloBinarySensorEntityDescription(
        key="solar_pump",
        name="Solar Pump",
        icon="mdi:solar-power",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.solar_pump_on,
    ),
    HaloBinarySensorEntityDescription(
        key="solar_flush_active",
        name="Solar Flush Active",
        icon="mdi:pipe",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.solar_flush_active,
    ),
    # Lights deliberately do NOT use BinarySensorDeviceClass.LIGHT — HA's
    # translation pack renders that as "Light detected" / "No light",
    # which is confusing for a pool light ("No light" sounds like the
    # entity isn't reporting, not that the light is off). Plain on/off
    # with a state-aware lightbulb icon is clearer.
    HaloBinarySensorEntityDescription(
        key="light_zone1_on",
        name="Pool Light",
        icon="mdi:lightbulb",
        value_fn=lambda data: data.light_zone1_on,
    ),
    HaloBinarySensorEntityDescription(
        key="light_zone2_on",
        name="Light Zone 2",
        icon="mdi:lightbulb",
        value_fn=lambda data: data.light_zone2_on,
    ),
    HaloBinarySensorEntityDescription(
        key="light_zone3_on",
        name="Light Zone 3",
        icon="mdi:lightbulb",
        value_fn=lambda data: data.light_zone3_on,
    ),
    HaloBinarySensorEntityDescription(
        key="light_zone4_on",
        name="Light Zone 4",
        icon="mdi:lightbulb",
        value_fn=lambda data: data.light_zone4_on,
    ),
    HaloBinarySensorEntityDescription(
        key="time_drift",
        name="Time Drift",
        icon="mdi:clock-alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: None,
    ),
    HaloBinarySensorEntityDescription(
        key="controller_notice_active",
        name="Controller Notice Active",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=controller_notice_active,
        attributes_fn=error_info_attributes,
    ),
    HaloBinarySensorEntityDescription(
        key="controller_fault_active",
        name="Controller Fault Active",
        icon="mdi:alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=controller_fault_active,
        attributes_fn=error_info_attributes,
    ),
    HaloBinarySensorEntityDescription(
        key="no_flow",
        name="No Flow",
        icon="mdi:waves",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "No Flow"),
    ),
    HaloBinarySensorEntityDescription(
        key="low_salt",
        name="Low Salt",
        icon="mdi:shaker-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "Low Salt"),
    ),
    HaloBinarySensorEntityDescription(
        key="high_salt",
        name="High Salt",
        icon="mdi:shaker-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "High Salt"),
    ),
    HaloBinarySensorEntityDescription(
        key="sampling_only",
        name="Sampling Only",
        icon="mdi:test-tube",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "Water Sampling"),
    ),
    HaloBinarySensorEntityDescription(
        key="dosing_disabled",
        name="Dosing Disabled",
        icon="mdi:beaker-remove",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "Dosing Disabled"),
    ),
    HaloBinarySensorEntityDescription(
        key="daily_acid_dose_limit_reached",
        name="Daily Acid Dose Limit Reached",
        icon="mdi:beaker-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "Daily Acid Dose Limit"),
    ),
    HaloBinarySensorEntityDescription(
        key="cell_disabled",
        name="Cell Disabled",
        icon="mdi:fuel-cell-off",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_error(data, "Cell Disconnected"),
    ),
    HaloBinarySensorEntityDescription(
        key="sanitising_active",
        name="Sanitising Active",
        icon="mdi:sparkles",
        value_fn=lambda data: match_info_any(data, SANITISING_INFO_MESSAGES),
    ),
    HaloBinarySensorEntityDescription(
        key="filtering_only",
        name="Filtering Only",
        icon="mdi:filter",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "Filtering"),
    ),
    HaloBinarySensorEntityDescription(
        key="sampling_active",
        name="Sampling Active",
        icon="mdi:test-tube",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info_any(data, SAMPLING_INFO_MESSAGES),
    ),
    HaloBinarySensorEntityDescription(
        key="standby",
        name="Standby",
        icon="mdi:pause-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "Standby"),
    ),
    HaloBinarySensorEntityDescription(
        key="low_speed_no_chlorinating",
        name="Low Speed No Chlorinating",
        icon="mdi:speedometer-slow",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "LowSpeedNoChlorinating"),
    ),
    HaloBinarySensorEntityDescription(
        key="reduced_output_low_temperature",
        name="Reduced Output Low Temperature",
        icon="mdi:thermometer-low",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "LowTemperatureReducedOutput"),
    ),
    HaloBinarySensorEntityDescription(
        key="heater_cooldown_active",
        name="Heater Cooldown Active",
        icon="mdi:radiator",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "HeaterCooldownInProgress"),
    ),
    HaloBinarySensorEntityDescription(
        key="manual_acid_dose_active",
        name="Manual Acid Dose Active",
        icon="mdi:beaker-plus",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "ManualAcidDose"),
    ),
    HaloBinarySensorEntityDescription(
        key="backwashing",
        name="Backwashing",
        icon="mdi:water",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: match_info(data, "Backwashing"),
    ),
    HaloBinarySensorEntityDescription(
        key="heat_demand_enabled",
        name="Heat Demand Enabled",
        icon="mdi:radiator",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heat_demand_enabled,
    ),
    HaloBinarySensorEntityDescription(
        key="heat_demand_window_enabled",
        name="Heat Demand Window Enabled",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.heat_demand_window_enabled,
    ),
    HaloBinarySensorEntityDescription(
        key="heat_demand_activated",
        name="Heat Demand Activated",
        icon="mdi:radiator-disabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda data: data.heat_demand_activated,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AstralPool Halo Cloud binary sensors."""
    coordinator: HaloCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HaloCloudBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class HaloCloudBinarySensor(HaloCloudEntity, BinarySensorEntity):
    """Representation of a Halo Cloud binary sensor."""

    entity_description: HaloBinarySensorEntityDescription

    @property
    def available(self) -> bool:
        """Keep connectivity visible even before the first live payload arrives."""
        if self.entity_description.key == "connected":
            return self.coordinator.data is not None
        if not super().available:
            return False
        zone_index = _light_zone_index_from_key(self.entity_description.key)
        if zone_index is not None:
            data = self.coordinator.data
            return data is not None and _light_zone_available(data, zone_index)
        return True

    @property
    def icon(self) -> str | None:
        """State-aware icon for the light zones (lightbulb on/off variants)."""
        key = self.entity_description.key
        if key.startswith("light_zone") and key.endswith("_on"):
            if self.coordinator.data is None:
                return "mdi:lightbulb"
            zone_idx = _light_zone_index_from_key(key)
            if zone_idx is None:
                return "mdi:lightbulb"
            on = getattr(
                self.coordinator.data,
                f"light_zone{zone_idx}_on",
                False,
            )
            return "mdi:lightbulb-on" if on else "mdi:lightbulb-off"
        return self.entity_description.icon

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        if self.coordinator.data is None:
            return None
        if self.entity_description.key == "time_drift":
            threshold = float(
                self.coordinator._entry.options.get(
                    CONF_TIME_DRIFT_THRESHOLD_MINUTES,
                    3,
                )
            )
            return controller_clock_drift_gt_threshold(self.coordinator.data, threshold)
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return optional extra state attributes."""
        if (
            self.coordinator.data is None
            or self.entity_description.attributes_fn is None
        ):
            return None
        attributes = self.entity_description.attributes_fn(self.coordinator.data)
        return attributes or None
