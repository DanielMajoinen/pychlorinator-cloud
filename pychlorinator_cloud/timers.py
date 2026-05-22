"""Timer models and parsers for Halo cloud timer payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

TIMER_SETUP_SEASONS = {
    0: "Winter",
    1: "Summer",
}

TIMER_STATE_SEASONS = {
    1: "Winter",
    2: "Summer",
}

TIMER_EQUIPMENT_FLAGS = {
    0x0001: "PoolSpa",
    0x0002: "FilterPump",
    0x0004: "Heater",
    0x0008: "Outlet1",
    0x0010: "Outlet2",
    0x0020: "Outlet3",
    0x0040: "Outlet4",
    0x0080: "Valve1",
    0x0100: "Valve2",
    0x0200: "Valve3",
    0x0400: "Valve4",
    0x0800: "Relay1",
    0x1000: "Relay2",
}

KNOWN_TIMER_EQUIPMENT_MASK = sum(TIMER_EQUIPMENT_FLAGS)
TIMER_BASE_CLASS_FLAG = 0x02
TIMER_SPEED_LEVELS = {
    0: "Low",
    1: "Medium",
    2: "High",
    3: "AI",
}


@dataclass(slots=True, frozen=True)
class TimerCapabilities:
    """Decoded timer capability counts."""

    equipment_timer_slots: int
    lighting_timer_slots: int
    flags: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        data = asdict(self)
        data["type"] = "timer_capabilities"
        data["flags"] = list(self.flags)
        return data


@dataclass(slots=True, frozen=True)
class TimerSetup:
    """Decoded timer setup/profile selection state."""

    no_timer_model: int
    timer_master_is_present: int
    season_byte: int
    season: str
    dusk_time_hour: int
    dusk_time_mins: int
    dawn_time_hour: int
    dawn_time_mins: int
    raw_bytes: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        data = asdict(self)
        data["type"] = "timer_setup"
        data["raw_bytes"] = list(self.raw_bytes)
        return data


@dataclass(slots=True, frozen=True)
class TimerState:
    """Decoded timer state/profile pointer."""

    profile_index: int
    next_profile_index: int | None = None
    season: str | None = None
    raw_bytes: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        data = asdict(self)
        data["type"] = "timer_state"
        data["raw_bytes"] = list(self.raw_bytes)
        return data


@dataclass(slots=True, frozen=True)
class TimerConfig:
    """Decoded per-slot timer record."""

    timer_type: int
    slot_index: int
    timer_mode: int
    season: str
    active: bool
    equipment_flags: int
    equipment_enabled: tuple[str, ...] = ()
    has_base_timer_flag: bool = False
    unknown_equipment_flags: tuple[int, ...] = ()
    start_mode: int = 0
    start_hour: int = 0
    start_minute: int = 0
    start_time: str | None = None
    stop_mode: int = 0
    stop_hour: int = 0
    stop_minute: int = 0
    stop_time: str | None = None
    duration_minutes: int | None = None
    overnight: bool = False
    speed_code: int = 0
    speed: str | None = None
    raw_bytes: tuple[int, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly dictionary."""
        data = asdict(self)
        data["type"] = "timer_config"
        data["equipment_enabled"] = list(self.equipment_enabled)
        data["unknown_equipment_flags"] = list(self.unknown_equipment_flags)
        data["raw_bytes"] = list(self.raw_bytes)
        return data


def _format_time(hour: int, minute: int) -> str | None:
    """Format a validated 24h time value."""
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


def _duration_minutes(
    start_hour: int,
    start_minute: int,
    stop_hour: int,
    stop_minute: int,
) -> tuple[int | None, bool]:
    """Return duration in minutes and whether the timer crosses midnight."""
    start_time = _format_time(start_hour, start_minute)
    stop_time = _format_time(stop_hour, stop_minute)
    if start_time is None or stop_time is None:
        return None, False

    start_total = start_hour * 60 + start_minute
    stop_total = stop_hour * 60 + stop_minute
    overnight = stop_total < start_total
    if overnight:
        stop_total += 24 * 60
    return stop_total - start_total, overnight


def parse_timer_capabilities(data: bytes) -> dict[str, Any]:
    """Parse cmd 0x0190 timer capabilities."""
    if len(data) < 2:
        return {"type": "timer_capabilities", "raw": data.hex(), "error": "too short"}

    return TimerCapabilities(
        equipment_timer_slots=data[0],
        lighting_timer_slots=data[1],
        flags=tuple(data[2:]),
    ).to_dict()


def parse_timer_setup(data: bytes) -> dict[str, Any]:
    """Parse cmd 0x0191 timer setup/profile state."""
    if len(data) < 7:
        return {"type": "timer_setup", "raw": data.hex(), "error": "too short"}

    season_byte = data[2]
    return TimerSetup(
        no_timer_model=data[0],
        timer_master_is_present=data[1],
        season_byte=season_byte,
        season=TIMER_SETUP_SEASONS.get(season_byte, f"Unknown({season_byte})"),
        dusk_time_hour=data[3],
        dusk_time_mins=data[4],
        dawn_time_hour=data[5],
        dawn_time_mins=data[6],
        raw_bytes=tuple(data),
    ).to_dict()


def parse_timer_state(data: bytes) -> dict[str, Any]:
    """Parse cmd 0x0192 timer profile pointer/state."""
    if len(data) < 1:
        return {"type": "timer_state", "raw": data.hex(), "error": "too short"}

    profile_index = data[0]
    return TimerState(
        profile_index=profile_index,
        next_profile_index=data[1] if len(data) > 1 else None,
        season=TIMER_STATE_SEASONS.get(profile_index),
        raw_bytes=tuple(data),
    ).to_dict()


def parse_timer_config(data: bytes) -> dict[str, Any]:
    """Parse cmd 0x0193 per-slot timer config."""
    if len(data) < 13:
        return {"type": "timer_config", "raw": data.hex(), "error": "too short"}

    equipment_flags = data[4] | (data[5] << 8)
    known_equipment = tuple(
        name for bit, name in TIMER_EQUIPMENT_FLAGS.items() if equipment_flags & bit
    )
    unknown_equipment_flags = tuple(
        1 << bit
        for bit in range(16)
        if equipment_flags & (1 << bit) and not (KNOWN_TIMER_EQUIPMENT_MASK & (1 << bit))
    )
    duration, overnight = _duration_minutes(data[7], data[8], data[10], data[11])

    return TimerConfig(
        timer_type=data[0],
        slot_index=data[1],
        timer_mode=data[2],
        season=TIMER_SETUP_SEASONS.get(data[2], f"Unknown({data[2]})"),
        active=bool(data[3]),
        equipment_flags=equipment_flags,
        equipment_enabled=known_equipment,
        has_base_timer_flag=bool(equipment_flags & TIMER_BASE_CLASS_FLAG),
        unknown_equipment_flags=unknown_equipment_flags,
        start_mode=data[6],
        start_hour=data[7],
        start_minute=data[8],
        start_time=_format_time(data[7], data[8]),
        stop_mode=data[9],
        stop_hour=data[10],
        stop_minute=data[11],
        stop_time=_format_time(data[10], data[11]),
        duration_minutes=duration,
        overnight=overnight,
        speed_code=data[12],
        speed=TIMER_SPEED_LEVELS.get(data[12], f"Unknown({data[12]})"),
        raw_bytes=tuple(data),
    ).to_dict()
