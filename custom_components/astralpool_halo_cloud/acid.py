"""Acid reservoir tracking for the AstralPool Halo Cloud integration.

The controller has no acid tank-level sensor. It reports acid pump run-time
TODAY (seconds) in 0x0259 as ``acid_dosing_seconds_today``, which resets at the
controller's day rollover. This module tracks a user-managed reservoir HA-side:
the user logs a refill (sets remaining = bottle size), and we decrement the
remaining volume as the controller doses, converting pump-seconds to millilitres
via the acid pump dose rate (mL/min, ``acid_pump_size`` from 0x0064/0x0069).

Units caveat: the vendor field is named DosingPumpSecs and the 1.5.x app renders
the raw value as "ml today", while the 2.x app carries both seconds and mL plus a
mL/min flow rate — strongly implying mL = seconds x rate / 60. We treat the raw
value as SECONDS and convert with the pump rate; the raw seconds are also exposed
so the derived mL can be sanity-checked against a live dose.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

_STORE_VERSION = 1
DEFAULT_BOTTLE_LITRES = 20.0
# Vendor default acid pump dose rate when the capability is unknown (mL/min).
_DEFAULT_PUMP_ML_PER_MIN = 5


class AcidReservoirTracker:
    """Persistent estimate of remaining acid, driven by daily dosing."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._store: Store = Store(
            hass, _STORE_VERSION, f"astralpool_halo_cloud_acid_{entry_id}"
        )
        self.bottle_size_l: float = DEFAULT_BOTTLE_LITRES
        self.remaining_ml: float = DEFAULT_BOTTLE_LITRES * 1000.0
        self.last_refill: Optional[Any] = None  # aware datetime
        self._last_seconds_today: Optional[int] = None
        self._loaded = False

    async def async_load(self) -> None:
        try:
            data = await self._store.async_load()
        except Exception:  # noqa: BLE001
            # A corrupt/unreadable acid store must not fail integration setup;
            # fall back to defaults (a fresh, full bottle).
            _LOGGER.warning(
                "Could not load acid reservoir state; starting from defaults",
                exc_info=True,
            )
            data = None
        if data:
            self.bottle_size_l = float(data.get("bottle_size_l", DEFAULT_BOTTLE_LITRES))
            self.remaining_ml = float(
                data.get("remaining_ml", self.bottle_size_l * 1000.0)
            )
            raw = data.get("last_refill")
            self.last_refill = dt_util.parse_datetime(raw) if raw else None
            self._last_seconds_today = data.get("last_seconds_today")
        self._loaded = True

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "bottle_size_l": self.bottle_size_l,
                "remaining_ml": self.remaining_ml,
                "last_refill": self.last_refill.isoformat() if self.last_refill else None,
                "last_seconds_today": self._last_seconds_today,
            }
        )

    @staticmethod
    def _ml_per_second(pump_ml_per_min: Optional[int]) -> float:
        rate = pump_ml_per_min if pump_ml_per_min else _DEFAULT_PUMP_ML_PER_MIN
        return float(rate) / 60.0

    async def async_ingest(
        self, seconds_today: Optional[int], pump_ml_per_min: Optional[int]
    ) -> bool:
        """Decrement remaining acid from a fresh 0x0259 dosing reading.

        Handles the daily reset: when ``seconds_today`` drops below the previous
        reading the controller has rolled over, so the new value is a fresh day's
        accumulation. Returns True if the estimate changed (caller may refresh).
        """
        if not self._loaded or seconds_today is None:
            return False
        prev = self._last_seconds_today
        if prev is None:
            self._last_seconds_today = seconds_today
            await self._async_save()
            return False
        delta_s = seconds_today - prev if seconds_today >= prev else seconds_today
        changed = False
        if delta_s > 0:
            used_ml = delta_s * self._ml_per_second(pump_ml_per_min)
            new_remaining = max(0.0, self.remaining_ml - used_ml)
            if new_remaining != self.remaining_ml:
                self.remaining_ml = new_remaining
                changed = True
        if seconds_today != prev:
            self._last_seconds_today = seconds_today
            changed = True
        if changed:
            await self._async_save()
        return changed

    async def async_log_refill(self) -> None:
        """Record a fresh bottle: reset remaining to full and stamp the time."""
        self.remaining_ml = self.bottle_size_l * 1000.0
        self.last_refill = dt_util.utcnow()
        await self._async_save()
        _LOGGER.info("Acid refill logged: reservoir reset to %.1f L", self.bottle_size_l)

    async def async_set_bottle_size(self, litres: float) -> None:
        self.bottle_size_l = max(0.1, float(litres))
        # Keep remaining within the new capacity.
        self.remaining_ml = min(self.remaining_ml, self.bottle_size_l * 1000.0)
        await self._async_save()

    # ---- Derived values for sensors ----
    @property
    def remaining_l(self) -> float:
        return round(self.remaining_ml / 1000.0, 2)

    @property
    def percent(self) -> Optional[float]:
        full = self.bottle_size_l * 1000.0
        if full <= 0:
            return None
        return round(min(100.0, 100.0 * self.remaining_ml / full), 1)

    def used_today_ml(
        self, seconds_today: Optional[int], pump_ml_per_min: Optional[int]
    ) -> Optional[float]:
        if seconds_today is None:
            return None
        return round(seconds_today * self._ml_per_second(pump_ml_per_min), 0)

    def _days_since_refill(self) -> Optional[float]:
        if self.last_refill is None:
            return None
        return (dt_util.utcnow() - self.last_refill).total_seconds() / 86400.0

    def avg_daily_ml(self) -> Optional[float]:
        days = self._days_since_refill()
        if days is None or days < 0.5:
            return None
        consumed = self.bottle_size_l * 1000.0 - self.remaining_ml
        if consumed <= 0:
            return None
        return consumed / days

    def days_remaining(self) -> Optional[float]:
        avg = self.avg_daily_ml()
        if not avg or avg <= 0:
            return None
        return round(self.remaining_ml / avg, 1)
