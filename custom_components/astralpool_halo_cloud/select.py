"""Select platform for the AstralPool Halo Cloud integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HaloCloudCoordinator
from .entity import HaloCloudEntity


@dataclass(frozen=True, kw_only=True)
class HaloSelectEntityDescription(SelectEntityDescription):
    """Describes a Halo Cloud select entity."""

    entity_category: EntityCategory | None = None
    value_fn: Callable[[Any], str | None] | None = None
    command_fn: Callable[[Any, str], Awaitable[None]] | None = None
    is_supported_fn: Callable[[Any], bool] | None = None


MODE_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="mode_select",
    name="System Mode",
)

PUMP_SPEED_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="pump_speed_select",
    name="Manual Pump Speed",
)

LIGHT_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="light_mode_select",
    name="Light Mode",
    options=["Off", "On", "Auto"],
    value_fn=lambda data: data.light_mode,
    command_fn=lambda client, option: client.set_light_mode(option),
)

BLADE_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="blade_mode_select",
    name="Blade Mode",
    options=["Off", "Auto", "On"],
    value_fn=lambda data: data.blade_mode,
    command_fn=lambda client, option: client.set_blade_mode(option),
    is_supported_fn=lambda data: data.gpo_modes[2] is not None,
)

JETS_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="jets_mode_select",
    name="Jets Mode",
    options=["Off", "Auto", "On"],
    value_fn=lambda data: data.jets_mode,
    command_fn=lambda client, option: client.set_jets_mode(option),
    is_supported_fn=lambda data: data.gpo_modes[3] is not None,
)


def _gpo_select_description(slot: int) -> HaloSelectEntityDescription:
    """Build a guarded mode selector for a generic GPO outlet."""
    index = slot - 1
    return HaloSelectEntityDescription(
        key=f"gpo{slot}_mode",
        name=f"GPO{slot} Mode",
        options=["Off", "Auto", "On"],
        value_fn=lambda data, index=index: data.gpo_modes[index],
        command_fn=lambda client, option, slot=slot: client.set_gpo_mode(
            slot, option
        ),
        is_supported_fn=lambda data, index=index: data.gpo_modes[index] is not None,
    )


GPO_SELECT_DESCRIPTIONS = tuple(
    _gpo_select_description(slot) for slot in (1, 2)
)

HEATER_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="heater_mode_select",
    name="Heater Mode Control",
    options=["Off", "On"],
    value_fn=lambda data: data.heater_mode,
    command_fn=lambda client, option: client.set_heater_off() if option == "Off" else client.set_heater_on(),
    is_supported_fn=lambda data: data.heater_mode is not None,
)

TIMER_SEASON_SELECT_DESCRIPTION = HaloSelectEntityDescription(
    key="timer_season",
    name="Timer Season",
    options=["Winter", "Summer"],
    value_fn=lambda data: data.timer_season,
    command_fn=lambda client, option: client.write_timer_season(option),
    is_supported_fn=lambda data: data.timer_season in {"Winter", "Summer"},
)


ACID_DOSING_OPTIONS = [
    "Resume now",
    "Off 1 minute",
    "Off 2 minutes",
    "Off 3 minutes",
    "Off 4 minutes",
    "Off 5 minutes",
    "Off 15 minutes",
    "Off 30 minutes",
    "Off 45 minutes",
    "Off 1 hour",
    "Off 2 hours",
    "Off 3 hours",
    "Off 6 hours",
    "Off 12 hours",
    "Off 24 hours",
    "Off indefinitely",
]

ACID_DOSING_MINUTES = {
    "Off 1 minute": 1,
    "Off 2 minutes": 2,
    "Off 3 minutes": 3,
    "Off 4 minutes": 4,
    "Off 5 minutes": 5,
    "Off 15 minutes": 15,
    "Off 30 minutes": 30,
    "Off 45 minutes": 45,
    "Off 1 hour": 60,
    "Off 2 hours": 120,
    "Off 3 hours": 180,
    "Off 6 hours": 360,
    "Off 12 hours": 720,
    "Off 24 hours": 1440,
}

# Fixed period options for maintenance programs (Filter For Period,
# Sanitise For Period). Same time increments as acid dosing.
MAINTENANCE_PERIOD_OPTIONS = [
    "1 minute",
    "2 minutes",
    "3 minutes",
    "4 minutes",
    "5 minutes",
    "15 minutes",
    "30 minutes",
    "45 minutes",
    "1 hour",
    "2 hours",
    "3 hours",
    "6 hours",
    "12 hours",
    "24 hours",
]

MAINTENANCE_PERIOD_MINUTES = {
    "1 minute": 1,
    "2 minutes": 2,
    "3 minutes": 3,
    "4 minutes": 4,
    "5 minutes": 5,
    "15 minutes": 15,
    "30 minutes": 30,
    "45 minutes": 45,
    "1 hour": 60,
    "2 hours": 120,
    "3 hours": 180,
    "6 hours": 360,
    "12 hours": 720,
    "24 hours": 1440,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AstralPool Halo Cloud select entities."""
    coordinator: HaloCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            HaloModeSelect(coordinator),
            HaloPumpSpeedSelect(coordinator),
            HaloActionSelect(coordinator, LIGHT_SELECT_DESCRIPTION),
            HaloActionSelect(coordinator, BLADE_SELECT_DESCRIPTION),
            HaloActionSelect(coordinator, JETS_SELECT_DESCRIPTION),
            *(
                HaloActionSelect(coordinator, description)
                for description in GPO_SELECT_DESCRIPTIONS
            ),
            HaloActionSelect(coordinator, HEATER_SELECT_DESCRIPTION),
            HaloActionSelect(coordinator, TIMER_SEASON_SELECT_DESCRIPTION),
            HaloAcidDosingSelect(coordinator),
            HaloConnectionPauseSelect(coordinator),
            HaloMaintenancePeriodSelect(
                coordinator,
                key="filter_for_period",
                name="Filter For Period",
                action_fn="start_filter_for_period",
            ),
            HaloMaintenancePeriodSelect(
                coordinator,
                key="sanitise_for_period",
                name="Sanitise For Period",
                action_fn="start_sanitise_for_period",
            ),
        ]
    )


class HaloModeSelect(HaloCloudEntity, SelectEntity):
    """Representation of the Halo system mode selector."""

    _attr_options = ["Off", "Auto", "On"]

    @property
    def available(self) -> bool:
        """Only allow control while the cloud session is actively connected."""
        data = self.coordinator.data
        return (
            super().available
            and self.coordinator.client.data.connected
            and data is not None
            and data.mode in self._attr_options
        )

    def __init__(self, coordinator: HaloCloudCoordinator) -> None:
        """Initialise the mode selector."""
        super().__init__(coordinator, MODE_SELECT_DESCRIPTION)

    @property
    def current_option(self) -> str | None:
        """Return the current selected mode."""
        data = self.coordinator.data
        if data is None or data.mode is None:
            return None

        if data.mode in self._attr_options:
            return data.mode

        # Fallback for any unexpected mode value
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the selected system mode."""
        client = self.coordinator.client
        if not client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")
        if option == "Off":
            await client.set_mode_off()
        elif option == "Auto":
            await client.set_mode_auto()
        elif option == "On":
            await client.set_mode_manual()
        else:
            raise ValueError(f"Invalid option: {option}")


class HaloPumpSpeedSelect(HaloCloudEntity, SelectEntity):
    """Representation of the Halo manual pump speed selector."""

    _attr_options = ["Low", "Medium", "High"]

    @property
    def available(self) -> bool:
        """Only allow control while the cloud session is actively connected."""
        data = self.coordinator.data
        return (
            super().available
            and self.coordinator.client.data.connected
            and data is not None
            and data.pump_speed in self._attr_options
        )

    def __init__(self, coordinator: HaloCloudCoordinator) -> None:
        """Initialise the pump-speed selector."""
        super().__init__(coordinator, PUMP_SPEED_SELECT_DESCRIPTION)

    @property
    def current_option(self) -> str | None:
        """Return the current manual pump-speed selection when known."""
        data = self.coordinator.data
        if data is None:
            return None
        if data.pump_speed in self._attr_options:
            return data.pump_speed
        return None

    async def async_select_option(self, option: str) -> None:
        """Set the selected manual pump speed."""
        client = self.coordinator.client
        if not client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")

        if option == "Low":
            await client.set_pump_speed_low()
        elif option == "Medium":
            await client.set_pump_speed_medium()
        elif option == "High":
            await client.set_pump_speed_high()
        else:
            raise ValueError(f"Invalid option: {option}")


class HaloActionSelect(HaloCloudEntity, SelectEntity):
    """Generic app-style action select for controls with discrete states."""

    entity_description: HaloSelectEntityDescription

    @property
    def available(self) -> bool:
        """Only allow control while the cloud session is actively connected."""
        data = self.coordinator.data
        supported = (
            data is not None
            and (
                self.entity_description.is_supported_fn is None
                or self.entity_description.is_supported_fn(data)
            )
        )
        return super().available and self.coordinator.client.data.connected and supported

    def __init__(self, coordinator: HaloCloudCoordinator, description: HaloSelectEntityDescription) -> None:
        super().__init__(coordinator, description)
        self._attr_options = list(description.options or [])

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if data is None or self.entity_description.value_fn is None:
            return None
        value = self.entity_description.value_fn(data)
        if value is None and self.entity_description.key in {
            "blade_mode_select",
            "jets_mode_select",
        }:
            return "Off"
        if value in self._attr_options:
            return value
        return None

    async def async_select_option(self, option: str) -> None:
        client = self.coordinator.client
        if not client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")
        if option not in self._attr_options:
            raise ValueError(f"Invalid option: {option}")
        if self.entity_description.command_fn is None:
            raise HomeAssistantError("This control is not configured")
        await self.entity_description.command_fn(client, option)


class HaloAcidDosingSelect(HaloCloudEntity, SelectEntity):
    """Action select for acid dosing hold presets."""

    _attr_options = ACID_DOSING_OPTIONS

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return (
            super().available
            and self.coordinator.client.data.connected
            and data is not None
            and data.acid_dosing_state is not None
        )

    def __init__(self, coordinator: HaloCloudCoordinator) -> None:
        super().__init__(
            coordinator,
            HaloSelectEntityDescription(
                key="acid_dosing_select",
                name="Acid Dosing Hold",
            ),
        )

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data
        if data is None:
            return None
        if data.acid_dosing_state == "ResumeNow":
            return "Resume now"
        if data.acid_dosing_state == "OffIndefinitely":
            return "Off indefinitely"
        if data.acid_dosing_state == "OffForPeriod" and data.acid_dosing_hold_minutes is not None:
            for label, minutes in ACID_DOSING_MINUTES.items():
                if minutes == data.acid_dosing_hold_minutes:
                    return label
        return None

    async def async_select_option(self, option: str) -> None:
        client = self.coordinator.client
        if not client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")
        if option == "Resume now":
            await client.enable_acid_dosing()
        elif option == "Off indefinitely":
            await client.disable_acid_dosing(0)
        else:
            minutes = ACID_DOSING_MINUTES.get(option)
            if minutes is None:
                raise ValueError(f"Invalid option: {option}")
            await client.disable_acid_dosing(minutes)


_PAUSE_MINUTES = {
    "5 minutes": 5,
    "10 minutes": 10,
    "30 minutes": 30,
    "1 hour": 60,
    "2 hours": 120,
}

# Idle indicator option for the Connection Hold select. Shown as the
# `current_option` when no pause is active so HA renders a stable label
# instead of `unknown`. Selecting this option is a no-op (treated like
# "Resume connection" — a safe idempotent action).
_PAUSE_IDLE_OPTION = "Connected"

_PAUSE_OPTIONS = [_PAUSE_IDLE_OPTION, "Resume connection", *_PAUSE_MINUTES]


class HaloConnectionPauseSelect(HaloCloudEntity, SelectEntity):
    """Select to pause the cloud connection so the vendor app or BLE can connect."""

    _attr_options = _PAUSE_OPTIONS

    def __init__(self, coordinator: HaloCloudCoordinator) -> None:
        super().__init__(
            coordinator,
            HaloSelectEntityDescription(
                key="connection_pause_select",
                name="Connection Hold",
                entity_category=EntityCategory.CONFIG,
            ),
        )

    @property
    def available(self) -> bool:
        """Always available — works whether connected or paused."""
        return True

    @property
    def current_option(self) -> str | None:
        """Return a stable label so HA never renders ``unknown`` for this select.

        While paused: ``Resume connection`` (so the user's next click resumes).
        While idle:   ``Connected`` (cosmetic; selecting it is a no-op).
        """
        if self.coordinator.is_connection_paused:
            return "Resume connection"
        return _PAUSE_IDLE_OPTION

    async def async_select_option(self, option: str) -> None:
        """Pause or resume the cloud connection."""
        if option in (_PAUSE_IDLE_OPTION, "Resume connection"):
            # Idempotent resume — if not paused this is a no-op; if paused it
            # cancels the hold cleanly.
            if self.coordinator.is_connection_paused:
                await self.coordinator.async_resume_connection()
            return
        minutes = _PAUSE_MINUTES.get(option)
        if minutes is None:
            raise ValueError(f"Invalid option: {option}")
        await self.coordinator.async_pause_connection(minutes)


class HaloMaintenancePeriodSelect(HaloCloudEntity, SelectEntity):
    """Select to run a maintenance program for a fixed time period.

    Two instances: Filter For Period (action 23) and Sanitise For Period
    (action 31). Same fixed time options as acid dosing hold.
    """

    _attr_options = MAINTENANCE_PERIOD_OPTIONS
    _attr_icon = "mdi:wrench-clock"

    def __init__(
        self,
        coordinator: HaloCloudCoordinator,
        key: str,
        name: str,
        action_fn: str,
    ) -> None:
        self._action_fn_name = action_fn
        super().__init__(
            coordinator,
            HaloSelectEntityDescription(
                key=key,
                name=name,
                entity_category=EntityCategory.CONFIG,
            ),
        )

    @property
    def available(self) -> bool:
        data = self.coordinator.data
        return (
            super().available
            and self.coordinator.client.data.connected
            and data is not None
        )

    @property
    def current_option(self) -> str | None:
        """No persistent state — always None (action-trigger select)."""
        return None

    async def async_select_option(self, option: str) -> None:
        """Trigger the maintenance program for the selected period."""
        client = self.coordinator.client
        if not client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")
        minutes = MAINTENANCE_PERIOD_MINUTES.get(option)
        if minutes is None:
            raise ValueError(f"Invalid option: {option}")
        action_fn = getattr(client, self._action_fn_name)
        await action_fn(minutes)
