"""The AstralPool Halo Cloud integration."""

from __future__ import annotations

from collections.abc import Iterable
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
)
try:
    import voluptuous as vol
except ModuleNotFoundError:  # pragma: no cover - Home Assistant provides this.
    vol = None

from pychlorinator_cloud.exceptions import SignallingError
from pychlorinator_cloud.websocket_client import EQUIPMENT_NAMES

from .const import CONF_AREA_ID, CONF_SERIAL_NUMBER, DOMAIN, PLATFORMS
from .coordinator import HaloCloudCoordinator

SERVICE_WRITE_EQUIPMENT_TIMER = "write_equipment_timer"
SERVICE_WRITE_HEAT_DEMAND = "write_heat_demand"
LOGGER = logging.getLogger(__name__)

if vol is not None:
    WRITE_EQUIPMENT_TIMER_SCHEMA = vol.Schema(
        {
            vol.Required("season"): vol.In(["Winter", "Summer"]),
            vol.Required("slot_index"): vol.All(int, vol.Range(min=0, max=7)),
            vol.Required("enabled"): bool,
            vol.Required("start_hour"): vol.All(int, vol.Range(min=0, max=23)),
            vol.Required("start_min"): vol.All(int, vol.Range(min=0, max=59)),
            vol.Optional("start_mode", default="Normal"): vol.In(
                ["Normal", "Dusk", "Dawn"]
            ),
            vol.Required("stop_hour"): vol.All(int, vol.Range(min=0, max=23)),
            vol.Required("stop_min"): vol.All(int, vol.Range(min=0, max=59)),
            vol.Optional("stop_mode", default="Normal"): vol.In(
                ["Normal", "Dusk", "Dawn"]
            ),
            vol.Required("equipment"): [vol.In(EQUIPMENT_NAMES)],
            vol.Optional("pump_speed", default="Medium"): vol.In(
                ["Low", "Medium", "High"]
            ),
            vol.Optional("device_id"): vol.Any(str, [str]),
        }
    )
else:
    WRITE_EQUIPMENT_TIMER_SCHEMA = None

if vol is not None:
    WRITE_HEAT_DEMAND_SCHEMA = vol.Schema(
        {
            vol.Optional("enabled"): bool,
            vol.Optional("window_enabled"): bool,
            vol.Optional("start_hour"): vol.All(int, vol.Range(min=0, max=23)),
            vol.Optional("start_minute"): vol.All(int, vol.Range(min=0, max=59)),
            vol.Optional("stop_hour"): vol.All(int, vol.Range(min=0, max=23)),
            vol.Optional("stop_minute"): vol.All(int, vol.Range(min=0, max=59)),
            vol.Optional("activated"): bool,
            vol.Optional("device_id"): vol.Any(str, [str]),
        }
    )
else:
    WRITE_HEAT_DEMAND_SCHEMA = None


async def _async_apply_area_to_entry_devices(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Apply the configured area to devices created by this config entry."""
    area_id = entry.data.get(CONF_AREA_ID)
    if not area_id:
        return

    device_registry = dr.async_get(hass)
    for device_entry in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        if device_entry.area_id == area_id:
            continue
        device_registry.async_update_device(device_entry.id, area_id=area_id)


def _as_list(value: Any) -> list[str]:
    """Return a HA service value as a string list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value]
    return [str(value)]


def _coordinator_by_serial(hass: HomeAssistant, serial_number: str) -> HaloCloudCoordinator | None:
    """Return the loaded coordinator for a chlorinator serial number."""
    for coordinator in hass.data.get(DOMAIN, {}).values():
        entry_serial = coordinator._entry.data.get(CONF_SERIAL_NUMBER)
        if entry_serial == serial_number:
            return coordinator
    return None


def _coordinator_from_device_id(
    hass: HomeAssistant, device_id: str
) -> HaloCloudCoordinator | None:
    """Resolve a target device_id to a Halo coordinator."""
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(device_id)
    if device_entry is None:
        return None
    for domain, serial_number in device_entry.identifiers:
        if domain == DOMAIN:
            return _coordinator_by_serial(hass, serial_number)
    return None


def _resolve_service_coordinator(
    hass: HomeAssistant, call: ServiceCall
) -> HaloCloudCoordinator:
    """Resolve a service target to exactly one coordinator."""
    device_ids = _as_list(call.data.get("device_id"))
    if device_ids:
        coordinators = [
            coordinator
            for device_id in device_ids
            if (coordinator := _coordinator_from_device_id(hass, device_id)) is not None
        ]
        if len(coordinators) == 1:
            return coordinators[0]
        raise HomeAssistantError("Target exactly one AstralPool Halo Cloud device")

    coordinators = list(hass.data.get(DOMAIN, {}).values())
    if len(coordinators) == 1:
        return coordinators[0]
    raise HomeAssistantError("Target an AstralPool Halo Cloud device")


async def _async_handle_write_heat_demand(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Handle the write_heat_demand service."""
    coordinator = _resolve_service_coordinator(hass, call)
    kwargs: dict[str, Any] = {}
    for key in (
        "enabled",
        "window_enabled",
        "start_hour",
        "start_minute",
        "stop_hour",
        "stop_minute",
        "activated",
    ):
        if key in call.data:
            value = call.data[key]
            if key in ("start_hour", "start_minute", "stop_hour", "stop_minute"):
                kwargs[key] = int(value)
            else:
                kwargs[key] = bool(value)
    try:
        await coordinator.client.write_heat_demand(**kwargs)
    except ValueError as err:
        raise HomeAssistantError(f"Invalid heat-demand configuration: {err}") from err
    except (RuntimeError, OSError, SignallingError) as err:
        raise HomeAssistantError(f"Could not write heat-demand settings: {err}") from err


async def _async_handle_write_equipment_timer(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Handle the write_equipment_timer service."""
    coordinator = _resolve_service_coordinator(hass, call)
    try:
        await coordinator.client.write_equipment_timer(
            season=call.data["season"],
            slot_index=int(call.data["slot_index"]),
            enabled=bool(call.data["enabled"]),
            start_hour=int(call.data["start_hour"]),
            start_min=int(call.data["start_min"]),
            start_mode=call.data.get("start_mode", "Normal"),
            stop_hour=int(call.data["stop_hour"]),
            stop_min=int(call.data["stop_min"]),
            stop_mode=call.data.get("stop_mode", "Normal"),
            equipment=list(call.data["equipment"]),
            pump_speed=call.data.get("pump_speed", "Medium"),
        )
    except ValueError as err:
        raise HomeAssistantError(f"Invalid equipment timer configuration: {err}") from err
    except (RuntimeError, OSError, SignallingError) as err:
        raise HomeAssistantError(f"Could not write equipment timer: {err}") from err


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_WRITE_EQUIPMENT_TIMER):
        return

    async def _handle_write_equipment_timer(call: ServiceCall) -> None:
        await _async_handle_write_equipment_timer(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE_EQUIPMENT_TIMER,
        _handle_write_equipment_timer,
        schema=WRITE_EQUIPMENT_TIMER_SCHEMA,
    )

    async def _handle_write_heat_demand(call: ServiceCall) -> None:
        await _async_handle_write_heat_demand(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_WRITE_HEAT_DEMAND,
        _handle_write_heat_demand,
        schema=WRITE_HEAT_DEMAND_SCHEMA,
    )


# Entity-key suffixes that USED to exist but have been replaced by other
# entities (different platform, fixed-duration selects, etc). On entry setup we
# drop any matching registry rows so HACS users don't carry stale `unavailable`
# clutter forward. unique_id format is `{serial}_{key}` per HaloCloudEntity.
OBSOLETE_ENTITY_KEY_SUFFIXES: tuple[str, ...] = (
    "_filter_period_minutes",  # replaced by select.*_filter_for_period
    "_sanitise_period_minutes",  # replaced by select.*_sanitise_for_period
)


def _async_purge_obsolete_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop entity-registry rows for entities this integration no longer creates.

    Matches by config_entry_id + DOMAIN + unique_id suffix. Idempotent; safe to
    call on every setup. Logs each removal at INFO so a user sees what cleared.
    """
    registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(
        registry, entry.entry_id
    ):
        if entity_entry.platform != DOMAIN:
            continue
        unique_id = entity_entry.unique_id or ""
        if any(unique_id.endswith(suffix) for suffix in OBSOLETE_ENTITY_KEY_SUFFIXES):
            LOGGER.info(
                "Removing obsolete Halo Cloud entity %s (unique_id=%s)",
                entity_entry.entity_id,
                unique_id,
            )
            registry.async_remove(entity_entry.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AstralPool Halo Cloud from a config entry."""
    coordinator = HaloCloudCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _async_purge_obsolete_entities(hass, entry)
    _async_register_services(hass)
    try:
        from .frontend import async_register_frontend

        await async_register_frontend(hass)
    except Exception as err:  # pragma: no cover - should not block core entities.
        LOGGER.warning("Could not register Halo Cloud frontend cards: %s", err)

    async def _async_handle_hass_stop(_: object) -> None:
        await coordinator.async_shutdown()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_handle_hass_stop)
    )

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        await _async_apply_area_to_entry_devices(hass, entry)
        coordinator.async_schedule_start()
    except Exception:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await coordinator.async_shutdown()
        raise

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an AstralPool Halo Cloud config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    coordinator: HaloCloudCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    return True
