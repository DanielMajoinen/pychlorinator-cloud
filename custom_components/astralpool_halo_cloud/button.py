"""Button platform for the AstralPool Halo Cloud integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HaloCloudCoordinator
from .entity import HaloCloudEntity


async def _press_pause_cloud_connection(coordinator: HaloCloudCoordinator) -> None:
    """Pause the cloud connection for the user-configured duration.

    Reads the duration from the coordinator's `default_pause_minutes` accessor
    which in turn reads the Cloud Pause Duration number entity
    (CONF_CONNECTION_PAUSE_MINUTES, default 15 minutes). Idempotent: pressing
    while already paused extends the hold to a fresh window.
    """
    await coordinator.async_pause_connection(coordinator.default_pause_minutes)


async def _press_resume_cloud_connection(coordinator: HaloCloudCoordinator) -> None:
    """Resume the cloud connection. No-op if not currently paused."""
    if coordinator.is_connection_paused:
        await coordinator.async_resume_connection()


# Filter For Period and Sanitise For Period are now select entities
# (select.py: HaloMaintenancePeriodSelect) with fixed time options.


async def _press_refresh_optional_values(coordinator: HaloCloudCoordinator) -> None:
    """Refresh optional-tier readbacks without requesting mandatory state."""
    try:
        await coordinator.client.refresh_optional_values()
    except RuntimeError as err:
        raise HomeAssistantError(str(err)) from err


async def _press_refresh_timer_config(coordinator: HaloCloudCoordinator) -> None:
    """Refresh current-season timer slots."""
    try:
        await coordinator.client.refresh_timer_config()
    except RuntimeError as err:
        raise HomeAssistantError(str(err)) from err


@dataclass(frozen=True, kw_only=True)
class HaloButtonEntityDescription(ButtonEntityDescription):
    """Describes a Halo Cloud button."""

    press_fn: Callable[[HaloCloudCoordinator], Awaitable[None]]
    requires_connection: bool = True


BUTTON_DESCRIPTIONS: tuple[HaloButtonEntityDescription, ...] = (
    HaloButtonEntityDescription(
        key="sync_controller_time",
        name="Sync Controller Time",
        icon="mdi:clock-sync",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=lambda coordinator: coordinator.client.sync_controller_clock(),
    ),
    HaloButtonEntityDescription(
        key="refresh_optional_values",
        name="Refresh Optional Values",
        icon="mdi:refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=_press_refresh_optional_values,
    ),
    HaloButtonEntityDescription(
        key="refresh_timer_config",
        name="Refresh Timer Config",
        icon="mdi:timer-refresh-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=_press_refresh_timer_config,
    ),
    # Cloud-connection control buttons. Read-side users find a button-pair
    # cleaner than a single select with mixed action/idle options.
    # Pause uses the Cloud Pause Duration number entity for its duration.
    # Resume is idempotent (no-op if not currently paused).
    HaloButtonEntityDescription(
        key="pause_cloud_connection",
        name="Pause Cloud Connection",
        icon="mdi:pause-circle-outline",
        entity_category=EntityCategory.CONFIG,
        # Pause is allowed even when the connection isn't currently established
        # (e.g. coordinator is between reconnect attempts) — it sets the pause
        # window which the reconnect loop will then honour.
        requires_connection=False,
        press_fn=_press_pause_cloud_connection,
    ),
    HaloButtonEntityDescription(
        key="resume_cloud_connection",
        name="Resume Cloud Connection",
        icon="mdi:play-circle-outline",
        entity_category=EntityCategory.CONFIG,
        # Resume must work whether currently paused or not (idempotent), so
        # don't require a live connection to enable the button.
        requires_connection=False,
        press_fn=_press_resume_cloud_connection,
    ),
    HaloButtonEntityDescription(
        key="sanitise_until_tomorrow",
        name="Sanitise Until Tomorrow",
        icon="mdi:calendar-clock",
        entity_category=EntityCategory.CONFIG,
        press_fn=(
            lambda coordinator: coordinator.client.start_sanitise_until_timer_tomorrow()
        ),
    ),
    # Filter For Period + Sanitise For Period removed — now select entities
    # with fixed time options (see select.py: HaloMaintenancePeriodSelect).
    HaloButtonEntityDescription(
        key="abort_maintenance_task",
        name="Abort Maintenance Task",
        icon="mdi:stop-circle-outline",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.abort_maintenance_task(),
    ),
    # Vendor-app parity: BLE/cloud app has a "Hide Error" button on the
    # error-info popup. Sends action 9 (DismissInfoMessage) to the controller.
    # Useful for clearing transient information codes like "Low Salt" or
    # "Dosing Disabled" from the display without changing actual state.
    HaloButtonEntityDescription(
        key="dismiss_info_message",
        name="Hide Error",
        icon="mdi:notification-clear-all",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.dismiss_info_message(),
        requires_connection=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up AstralPool Halo Cloud buttons."""
    coordinator: HaloCloudCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            *(HaloCloudButton(coordinator, description) for description in BUTTON_DESCRIPTIONS),
            HaloCloudAcidRefillButton(coordinator),
        ]
    )


class HaloCloudAcidRefillButton(HaloCloudEntity, ButtonEntity):
    """Log a fresh acid bottle: reset the reservoir estimate to full."""

    _attr_icon = "mdi:bottle-tonic-plus"

    def __init__(self, coordinator: HaloCloudCoordinator) -> None:
        super().__init__(
            coordinator,
            ButtonEntityDescription(key="acid_log_refill", name="Log Acid Refill"),
        )

    @property
    def available(self) -> bool:
        # HA-side action; usable even while the cloud is disconnected.
        return True

    async def async_press(self) -> None:
        await self.coordinator.acid.async_log_refill()
        self.coordinator.async_update_listeners()


class HaloCloudButton(HaloCloudEntity, ButtonEntity):
    """Representation of a Halo Cloud button."""

    entity_description: HaloButtonEntityDescription

    @property
    def available(self) -> bool:
        """Return whether the button can be used right now."""
        if not super().available:
            return False
        if self.entity_description.requires_connection:
            return self.coordinator.client.data.connected
        return True

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.entity_description.requires_connection and not self.coordinator.client.data.connected:
            raise HomeAssistantError("Chlorinator cloud is not connected")
        await self.entity_description.press_fn(self.coordinator)
