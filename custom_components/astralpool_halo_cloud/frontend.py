"""Frontend asset registration for AstralPool Halo Cloud."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

FRONTEND_URL_BASE = f"/{DOMAIN}"
FRONTEND_DIR = Path(__file__).parent / "www"
_REGISTERED_HASS_IDS: set[int] = set()


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve bundled Lovelace card modules."""
    hass_id = id(hass)
    if hass_id in _REGISTERED_HASS_IDS:
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_URL_BASE, str(FRONTEND_DIR), True)]
    )
    _REGISTERED_HASS_IDS.add(hass_id)
