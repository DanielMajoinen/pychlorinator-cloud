"""Transport-agnostic Halo payload parsers."""

from __future__ import annotations

import struct
from typing import Any

from .timers import parse_timer_capabilities, parse_timer_config, parse_timer_setup, parse_timer_state

LIGHT_CAPABILITIES_CMD_ID = 0x012D
VALVE_CUSTOM_NAME_CMD_ID = 0x051B

# Enums from pychlorinator halo_parsers.py. authoritative BLE definitions
SPEED_LEVELS = {0: "Low", 1: "Medium", 2: "High", 3: "AI"}
MANUAL_SPEED_ACTIONS = {4: "Low", 5: "Medium", 6: "High"}

# StateCharacteristic3.MainTextValues (info_message / MainText)
MAIN_TEXT_VALUES = {
    0: "Off", 1: "Sanitising", 2: "AIModeSanitising", 3: "AIModeSampling",
    4: "Sampling", 5: "Standby", 6: "PrePurge", 7: "PostPurg",
    8: "SanitisingUntilFirstTimer", 9: "Filtering", 10: "FilteringAndCleaning",
    11: "CalibratingSensor", 12: "Backwashing", 13: "PrimingAcidPump",
    14: "ManualAcidDose", 15: "LowSpeedNoChlorinating", 16: "SanitisingForPeriod",
    17: "SanitisingAndCleaningForPeriod", 18: "LowTemperatureReducedOutput",
    19: "HeaterCooldownInProgress",
}

# StateCharacteristic3.SubText1Values (chlorine status)
SUBTEXT1_CHLORINE = {
    0: "None", 1: "ORPIsYellow", 2: "ORPWasYellow", 3: "ORPIsGreen",
    4: "ORPWasGreen", 5: "ORPIsRed", 6: "ORPWasRed", 7: "ChlorineIsLow",
    8: "ChlorineWasLow", 9: "ChlorineIsOK", 10: "ChlorineWasOK",
    11: "ChlorineIsHigh", 12: "ChlorineWasHigh",
}

# StateCharacteristic3.SubText2Values (pH status)
SUBTEXT2_PH = {
    0: "None", 1: "PHIsYellow", 2: "PHWasYellow", 3: "PHIsGreen",
    4: "PHWasGreen", 5: "PHIsRed", 6: "PHWasRed", 7: "PHIsLow",
    8: "PHWasLow", 9: "PHIsOK", 10: "PHWasOK", 11: "PHIsHigh", 12: "PHWasHigh",
}

# StateCharacteristic3.SubText3Values (timer info)
# Code 0 historically rendered as the bare string "None", which is confusing
# in HA UI (looks like a missing value). Renamed to "Idle" 2026-05-06.
SUBTEXT3_TIMER = {
    0: "Idle", 1: "SanitisingPoolOff", 2: "SanitisingPoolUntil",
    3: "SanitisingSpaOff", 4: "SanitisingSpaUntil", 5: "SanitisingOff",
    6: "SanitisingUntil", 7: "PrimingFor", 8: "HeaterCooldownTimeRemaining",
}

# StateCharacteristic2.FlagsValues from the vendor app decompile.
FLAG_PH_MEASUREMENT_VALID = 0x0001
FLAG_FIRST_PH_RESULT_RECEIVED = 0x0002
FLAG_SPA_MODE = 0x0004
FLAG_PUMP_IS_PRIMING = 0x0008
FLAG_PUMP_ON = 0x0010
FLAG_CELL_ON = 0x0020
FLAG_CELL_REVERSED = 0x0040
FLAG_SANITISING_UNTIL_FIRST_TIMER_TOMORROW = 0x0080
FLAG_COOLING_FAN_ON = 0x0100
FLAG_LIGHT_OUTPUT_ON = 0x0200
FLAG_DOSING_PUMP_ON = 0x0400
FLAG_AI_MODE_ACTIVE = 0x0800

CONTROL_TYPES = {
    0: "None",
    1: "Manual",
    2: "Automatic",
}

# Per-zone mode bytes from 0x012C LightState (controller-side encoding).
# This is DIFFERENT from VENDOR_LIGHT_ACTIONS (which is the AppAction write enum).
# Captured live from a Halo controller on 2026-05-19.
ZONE_MODE_DECODE = {
    0: "Off",
    1: "Auto",
    2: "On",
}

GPO_NAME_LABELS = {
    0: "No Name",
    1: "Other",
    2: "Cleaning Pump",
    3: "Heater Pump",
    4: "Booster Pump",
    5: "Waterfall Pump",
    6: "Fountain Pump",
    7: "Blower",
    8: "Jets",
}

VALVE_NAME_LABELS = {
    0: "None",
    1: "Other",
    2: "Pool Valve",
    3: "Spa Valve",
    4: "Feature Valve",
    5: "Waterfall Valve",
}


def _derive_active_source(
    manual_mode: str | None,
    zone_on: bool,
) -> str:
    """Collapse manual mode and output state into a display label.

    Modes (from 0x012C zone-mode bytes):
      - Off  -> light is off, no timer override
      - Auto -> follows lighting timer schedule
      - On   -> manually forced on by user

    Outputs:
      - off          : mode=Off or mode=Auto with no active timer slot
      - timer        : mode=Auto and a timer slot is currently driving output
      - manual_on    : mode=On and light is illuminated
      - manual_off   : mode=On but light isn't actually illuminated (fault/transition)
    """
    if manual_mode == "On":
        return "manual_on" if zone_on else "manual_off"

    # mode is Auto or Off (or unknown). Output bit drives the source.
    if zone_on:
        return "timer" if manual_mode == "Auto" else "on"
    return "off"


def _parse_state(data: bytes) -> dict[str, Any]:
    """Parse state characteristic (cmd 0x0068)."""
    if len(data) < 10:
        return {"type": "state", "raw": data.hex(), "error": "too short for state"}

    flags = struct.unpack_from("<H", data, 0)[0]
    cell_level = data[1]
    cell_current_ma = struct.unpack_from("<H", data, 2)[0]
    main_text = data[4]
    sub1_chlorine = data[5]
    orp_mv = struct.unpack_from("<H", data, 6)[0] if len(data) > 7 else 0
    sub2_ph = data[8] if len(data) > 8 else 0
    ph_raw = data[9] if len(data) > 9 else 0
    sub3_timer = data[10] if len(data) > 10 else 0
    timer_info = SUBTEXT3_TIMER.get(sub3_timer, f"Unknown({sub3_timer})")
    priming_active = timer_info == "PrimingFor"
    priming_countdown = data[11] if len(data) > 11 else 0
    priming_phase_code = data[12] if len(data) > 12 else 0
    valve_state_raw = data[12] if len(data) > 12 else 0
    error_info = struct.unpack_from("<H", data, 13)[0] if len(data) > 14 else 0

    info_message = MAIN_TEXT_VALUES.get(main_text, f"Unknown({main_text})")

    return {
        "type": "state",
        "flags_raw": flags,
        "chemistry_values_current": bool(flags & FLAG_PH_MEASUREMENT_VALID),
        "chemistry_values_valid": bool(flags & FLAG_FIRST_PH_RESULT_RECEIVED),
        "spa_mode": bool(flags & FLAG_SPA_MODE),
        "pump_is_operating": bool(flags & FLAG_PUMP_ON),
        "cell_is_operating": bool(flags & FLAG_CELL_ON),
        "cell_is_reversed": bool(flags & FLAG_CELL_REVERSED),
        "sanitising_until_next_timer_tomorrow": bool(
            flags & FLAG_SANITISING_UNTIL_FIRST_TIMER_TOMORROW
        ),
        "cooling_fan_on": bool(flags & FLAG_COOLING_FAN_ON),
        "light_output_on": bool(flags & FLAG_LIGHT_OUTPUT_ON),
        "dosing_pump_on": bool(flags & FLAG_DOSING_PUMP_ON),
        "cell_is_reversing": False,
        "ai_mode_active": bool(flags & FLAG_AI_MODE_ACTIVE),
        "cell_level": cell_level,
        "cell_current_ma": cell_current_ma,
        "info_message": info_message,
        "info_message_code": main_text,
        "chlorine_control_status": SUBTEXT1_CHLORINE.get(sub1_chlorine, f"Unknown({sub1_chlorine})"),
        "orp_mv": orp_mv,
        "ph_control_status": SUBTEXT2_PH.get(sub2_ph, f"Unknown({sub2_ph})"),
        "ph_measurement": ph_raw / 10.0 if ph_raw > 0 else None,
        "timer_info": timer_info,
        "priming_active": priming_active,
        "priming_countdown": priming_countdown,
        "priming_phase_code": priming_phase_code,
        "valve_state_raw": valve_state_raw,
        "valve_0_active": bool(valve_state_raw & 0x01),
        "valve_1_active": bool(valve_state_raw & 0x02),
        "error_info": error_info,
    }


def _parse_dosing_state(data: bytes) -> dict[str, Any]:
    """Parse dosing/maintenance state (cmd 0x006a).

    Confirmed field map (2026-05-19, 4-capture verification):
      [0]     u8       state/mode flag (0x00 or 0x02 observed, unconfirmed)
      [1:3]   u16 LE   acid dosing hold remaining (minutes)
      [3]     u8       unknown (stable 0x02)
      [4]     u8       unknown (stable 0x00)
      [5:8]   u24 LE   filter/sanitise countdown remaining (seconds)
      [8:16]  8 bytes  unknown (stable pattern)
    """
    if len(data) < 8:
        return {"type": "dosing_state", "raw": data.hex(), "error": "too short"}

    # Acid dosing hold -- [1:3] u16 LE, minutes
    acid_hold_remaining_minutes = struct.unpack_from("<H", data, 1)[0]

    # Filter/sanitise countdown -- [5:8] u24 LE, seconds
    filter_remaining_seconds = data[5] | (data[6] << 8) | (data[7] << 16)

    # Derive acid dosing state from the acid countdown (not the filter one)
    if acid_hold_remaining_minutes > 0:
        acid_dosing_state = "OffForPeriod"
    else:
        acid_dosing_state = "ResumeNow"

    return {
        "type": "dosing_state",
        "acid_hold_remaining_minutes": acid_hold_remaining_minutes,
        "filter_remaining_seconds": filter_remaining_seconds,
        "acid_dosing_state": acid_dosing_state,
        "state_flag": data[0],
        "mode_byte_3": data[3],
        "mode_byte_4": data[4],
    }


def _parse_light_state(data: bytes) -> dict[str, Any]:
    """Parse light state characteristic (cmd 0x012c, lighting namespace)."""
    if len(data) < 9:
        return {"type": "light_state", "raw": data.hex(), "error": "too short"}

    zone_modes_raw = list(data[0:4])
    zone_modes = [
        ZONE_MODE_DECODE.get(mode, f"Unknown({mode})")
        for mode in zone_modes_raw
    ]
    zone_colours_raw = list(data[4:8])
    zone_state_flags = data[8]
    zone_on = [
        bool(zone_state_flags & 0x01),
        bool(zone_state_flags & 0x02),
        bool(zone_state_flags & 0x04),
        bool(zone_state_flags & 0x08),
    ]

    return {
        "type": "light_state",
        "zone_modes_raw": zone_modes_raw,
        "zone1_mode_raw": zone_modes_raw[0],
        "zone2_mode_raw": zone_modes_raw[1],
        "zone3_mode_raw": zone_modes_raw[2],
        "zone4_mode_raw": zone_modes_raw[3],
        "zone1_mode": zone_modes[0],
        "zone2_mode": zone_modes[1],
        "zone3_mode": zone_modes[2],
        "zone4_mode": zone_modes[3],
        "zone1_on": zone_on[0],
        "zone2_on": zone_on[1],
        "zone3_on": zone_on[2],
        "zone4_on": zone_on[3],
        "zone1_active_source": _derive_active_source(zone_modes[0], zone_on[0]),
        "zone2_active_source": _derive_active_source(zone_modes[1], zone_on[1]),
        "zone3_active_source": _derive_active_source(zone_modes[2], zone_on[2]),
        "zone4_active_source": _derive_active_source(zone_modes[3], zone_on[3]),
        "zone_colours_raw": zone_colours_raw,
    }


def _parse_light_capabilities(data: bytes) -> dict[str, Any]:
    """Parse light capabilities characteristic (cmd 0x012d)."""
    if len(data) < 5:
        return {"type": "light_capabilities", "raw": data.hex(), "error": "too short"}

    multicolour_flags = data[4]
    return {
        "type": "light_capabilities",
        "lighting_enabled": bool(data[0]),
        "onboard_light_enabled": bool(data[1]),
        "lighting_model": data[2],
        "lighting_num_zones_in_use": data[3],
        "zone1_is_multicolour": bool(multicolour_flags & 0x01),
        "zone2_is_multicolour": bool(multicolour_flags & 0x02),
        "zone3_is_multicolour": bool(multicolour_flags & 0x04),
        "zone4_is_multicolour": bool(multicolour_flags & 0x08),
    }


def _parse_setpoint(data: bytes) -> dict[str, Any]:
    """Parse setpoint characteristic (cmd 0x0066)."""
    if len(data) < 5:
        return {"type": "setpoint", "raw": data.hex(), "error": "too short"}

    vals = struct.unpack_from("<BHBBB", data)
    return {
        "type": "setpoint",
        "ph_setpoint": vals[0] / 10.0,
        "orp_setpoint": vals[1],
        "pool_chlorine_setpoint": vals[2],
        "acid_setpoint": vals[3],
        "spa_chlorine_setpoint": vals[4],
    }


def _parse_measurements(data: bytes) -> dict[str, Any]:
    """Parse statistics A characteristic (cmd 0x0259).

    Field map validated across 22 cloud capture sessions (2026-05-19):
      [0:2]   u16 LE  operating_days
      [2:4]   u16 LE  unknown_counter_a
      [4:6]   zero
      [6:8]   u16 LE  cell_reversal_count
      [8:10]  zero
      [10]    u8      previous_days_cell_load_percent (provisional)
      [11:13] zero
      [13:15] u16 LE  today_cell_runtime_minutes
      [15]    u8      stats_flag_byte
      [16]    zero

    This command does not contain live water temperature or cell current.
    Water temperature comes from 0x0009; cell current comes from 0x0068.
    """
    if len(data) < 17:
        return {"type": "statistics_a", "raw": data.hex(), "error": "too short"}

    return {
        "type": "statistics_a",
        "operating_days": struct.unpack_from("<H", data, 0)[0],
        "unknown_counter_a": struct.unpack_from("<H", data, 2)[0],
        "cell_reversal_count": struct.unpack_from("<H", data, 6)[0],
        "previous_days_cell_load_percent": data[10],
        "today_cell_runtime_minutes": struct.unpack_from("<H", data, 13)[0],
        "stats_flag_byte": data[15],
    }


def _parse_probe_statistics(data: bytes) -> dict[str, Any]:
    """Parse probe statistics characteristic (cmd 0x0258)."""
    if len(data) < 6:
        return {"type": "probe_statistics", "raw": data.hex(), "error": "too short"}

    return {
        "type": "probe_statistics",
        "highest_ph_measured": data[0] / 10.0,
        "lowest_ph_measured": data[1] / 10.0,
        "highest_orp_measured": struct.unpack_from("<H", data, 2)[0],
        "lowest_orp_measured": struct.unpack_from("<H", data, 4)[0],
    }


def _parse_statistics_b(data: bytes) -> dict[str, Any]:
    """Parse power-board statistics characteristic (cmd 0x025a)."""
    if len(data) < 4:
        return {"type": "statistics_b", "raw": data.hex(), "error": "too short"}

    return {
        "type": "statistics_b",
        "power_board_runtime_hours": struct.unpack_from("<I", data, 0)[0],
    }


def _parse_capabilities(data: bytes) -> dict[str, Any]:
    """Parse capabilities characteristic (cmd 0x0069).

    CapabilitiesCharacteristic is packed byte-by-byte in the vendor decompile.
    ORP min/max are encoded as byte values scaled by 10.
    """
    if len(data) < 15:
        return {"type": "capabilities", "raw": data.hex(), "error": "too short"}

    flags = data[10]
    min_orp_raw = data[6]
    max_orp_raw = data[7]
    return {
        "type": "capabilities",
        "min_manual_acid_setpoint": data[0],
        "max_manual_acid_setpoint": data[1],
        "min_manual_chlorine_setpoint": data[2],
        "max_manual_chlorine_setpoint": data[3],
        "min_ph_setpoint": data[4] / 10.0,
        "max_ph_setpoint": data[5] / 10.0,
        "min_orp_setpoint": min_orp_raw * 10,
        "max_orp_setpoint": max_orp_raw * 10,
        "ph_control_type_code": data[8],
        "ph_control_type": CONTROL_TYPES.get(data[8], f"Unknown({data[8]})"),
        "chlorine_control_type_code": data[9],
        "chlorine_control_type": CONTROL_TYPES.get(data[9], f"Unknown({data[9]})"),
        "capabilities_flags": flags,
        "three_speed_pump_enabled": bool(flags & 0x01),
        "ai_mode_enabled": bool(flags & 0x02),
        "lighting_enabled": bool(flags & 0x10),
        "dosing_capable": bool(flags & 0x20),
        "cell_size": data[11],
        "acid_pump_size": data[12],
        "filter_pump_size": data[13],
        "reversal_period": data[14],
    }


def _parse_settings(data: bytes) -> dict[str, Any]:
    """Parse settings characteristic (cmd 0x0064)."""
    if len(data) < 7:
        return {"type": "settings", "raw": data.hex(), "error": "too short"}

    vals = struct.unpack_from("<HBBBBBB", data)
    general = vals[0]

    return {
        "type": "settings",
        "general_flags": general,
        "cell_model": vals[1],
        "reversal_period": vals[2],
        "ai_water_turns": vals[3],
        "acid_pump_size": vals[4],
        "filter_pump_size": vals[5],
        "default_manual_speed": vals[6],
        "dosing_enabled": bool(general & 64),
        "three_speed_pump": bool(general & 128),
        "ai_enabled": bool(general & 8),
        "display_orp": bool(general & 32),
        "display_ph": bool(general & 4096),
    }


def _parse_water_volume(data: bytes) -> dict[str, Any]:
    """Parse water volume characteristic (cmd 0x0065)."""
    if len(data) < 14:
        return {"type": "water_volume", "raw": data.hex(), "error": "too short"}

    vals = struct.unpack_from("<BIHIHB", data)
    units = {0: "Litres", 1: "USGallons", 2: "ImperialGallons"}

    return {
        "type": "water_volume",
        "volume_units": units.get(vals[0], f"Unknown({vals[0]})"),
        "pool_volume": vals[1],
        "spa_volume": vals[2],
        "pool_left_filter": vals[3],
        "spa_left_filter": vals[4],
        "pool_enabled": bool(vals[5] & 1),
        "spa_enabled": bool(vals[5] & 2),
    }


def _parse_temperature(data: bytes) -> dict[str, Any]:
    """Parse temperature characteristic (cmd 0x0009)."""
    if len(data) < 16:
        return {"type": "temperature", "raw": data.hex(), "error": "too short"}

    vals = struct.unpack_from("<BBHHHHBHHB", data)
    return {
        "type": "temperature",
        "is_fahrenheit": bool(vals[0]),
        "board_temp_c": round(vals[2] / 10.0, 1),
        "water_temp_c": round(vals[3] / 10.0, 1),
        "chloro_water_temp_c": round(vals[4] / 10.0, 1),
        "solar_water_temp_c": round(vals[5] / 10.0, 1),
        "water_temp_valid": vals[6],
        "solar_roof_temp_c": round(vals[7] / 10.0, 1),
        "heater_temp_c": round(vals[8] / 10.0, 1),
    }


def _parse_controller_time(data: bytes) -> dict[str, Any]:
    """Parse controller time (cmd 0x0002)."""
    if len(data) < 4:
        return {"type": "controller_time", "raw": data.hex(), "error": "too short"}

    return {
        "type": "controller_time",
        "controller_second": data[0],
        "controller_minute": data[1],
        "controller_hour": data[2],
        "controller_weekday": data[3],
    }


def _parse_controller_date(data: bytes) -> dict[str, Any]:
    """Parse controller date (cmd 0x0003)."""
    if len(data) < 3:
        return {"type": "controller_date", "raw": data.hex(), "error": "too short"}

    return {
        "type": "controller_date",
        "controller_day": data[0],
        "controller_month": data[1],
        "controller_year": 2000 + data[2],
    }


def _parse_heater_state(data: bytes) -> dict[str, Any]:
    """Parse heater state characteristic (cmd 0x044e / BLE 1102)."""
    if len(data) < 12:
        return {"type": "heater_state", "raw": data.hex(), "error": "too short"}

    vals = struct.unpack_from("<BBBBBBBBBHB", data)
    pump_modes = {0: "Off", 1: "Auto", 2: "On"}
    heater_modes = {0: "Off", 1: "On"}
    heatpump_modes = {0: "Cooling", 1: "Heating", 2: "Auto"}

    status = vals[0]
    # TODO: Blade/Jets GPO readback likely lives in 0x044e or a
    # sibling equipment characteristic, but the decompile does not identify
    # vals[6]/vals[7] confidently. Capture Blade/Jets Off/Auto/On transitions
    # before mapping those bytes.
    return {
        "type": "heater_state",
        "heater_on": bool(status & 1),
        "heater_pressure": bool(status & 2),
        "heater_gas_valve": bool(status & 4),
        "heater_flame": bool(status & 8),
        "heater_lockout": bool(status & 16),
        "heater_pump_mode": pump_modes.get(vals[1], f"Unknown({vals[1]})"),
        "heater_mode": heater_modes.get(vals[2], f"Unknown({vals[2]})"),
        "heater_setpoint_c": vals[3],
        "heat_pump_mode": heatpump_modes.get(vals[4], f"Unknown({vals[4]})"),
        "heater_forced": vals[5],
        "heater_water_temp_valid": vals[8],
        "heater_water_temp_c": round(vals[9] / 10.0, 1),
        "heater_error": vals[10],
    }


def _parse_heat_demand_settings(data: bytes) -> dict[str, Any]:
    """Parse heater-demand settings characteristic (cmd 0x0451 / BLE 1105).

    Decompiled from the vendor app `HeaterDemandSettingsCharacteristic`
    (StructLayout Pack=1, 7 bytes):
      [0] HeatDemandEnabled            (0/1)
      [1] EnableHeatDemandWindow       (0/1)
      [2] HeatDemandWindowStopHour
      [3] HeatDemandWindowStopMinute
      [4] HeatDemandWindowStartHour
      [5] HeatDemandWindowStartMinute
      [6] HeatDemandActivated          (0/1)

    Unlike equipment timers (0x0193, 8 slots per season), heater demand is a
    single window + an enable + an activation flag. There is no season axis.
    """
    if len(data) < 7:
        return {"type": "heat_demand_settings", "raw": data.hex(), "error": "too short"}

    return {
        "type": "heat_demand_settings",
        "heat_demand_enabled": bool(data[0]),
        "heat_demand_window_enabled": bool(data[1]),
        "heat_demand_window_stop_hour": data[2],
        "heat_demand_window_stop_minute": data[3],
        "heat_demand_window_start_hour": data[4],
        "heat_demand_window_start_minute": data[5],
        "heat_demand_activated": bool(data[6]),
    }


def _parse_gpo_setup(data: bytes) -> dict[str, Any]:
    """Parse GPO setup/name enum readback (cmd 0x0514)."""
    if len(data) < 7:
        return {"type": "gpo_setup", "raw": data.hex(), "error": "too short"}

    device_type = data[0]
    index = data[1]
    gpo_slot_by_selector = {
        (7, 0): 1,
        (7, 1): 2,
        (8, 0): 3,
        (8, 1): 4,
    }
    gpo_slot = gpo_slot_by_selector.get((device_type, index))
    if gpo_slot is None:
        return {
            "type": "gpo_setup",
            "raw": data.hex(),
            "error": f"unknown gpo selector ({device_type}, {index})",
        }

    name_enum = data[4]
    return {
        "type": "gpo_setup",
        "gpo_slot": gpo_slot,
        "enabled": bool(data[2]),
        "name_enum": name_enum,
        "name_label": GPO_NAME_LABELS.get(name_enum, f"Unknown({name_enum})"),
        "use_timers": bool(data[6]),
        "is_custom_name": name_enum == 1,
    }


def _parse_valve_setup(data: bytes) -> dict[str, Any]:
    """Parse valve setup/name enum readback (cmd 0x0516)."""
    if len(data) < 4:
        return {"type": "valve_setup", "raw": data.hex(), "error": "too short"}

    index = data[0]
    if index > 3:
        return {
            "type": "valve_setup",
            "raw": data.hex(),
            "error": f"unknown valve index {index}",
        }

    name_enum = data[2]
    return {
        "type": "valve_setup",
        "valve_slot": index + 1,
        "enabled": bool(data[1]),
        "name_enum": name_enum,
        "name_label": VALVE_NAME_LABELS.get(name_enum, f"Unknown({name_enum})"),
        "use_timers": bool(data[3]),
        "is_custom_name": name_enum == 1,
    }


def _parse_valve_custom_name_chunk(data: bytes) -> dict[str, Any]:
    """Parse one chunk of a valve custom-name response (cmd 0x051b)."""
    if len(data) < 4:
        return {"type": "valve_custom_name_chunk", "raw": data.hex(), "error": "too short"}

    return {
        "type": "valve_custom_name_chunk",
        "valve_index": data[0],
        "message_number": data[1],
        "custom_name_length": data[2],
        "fragment_bytes": bytes(data[3:16]) if len(data) >= 16 else bytes(data[3:]),
    }


def parse_data_payload(raw: bytes) -> dict[str, Any]:
    """Parse a Halo binary payload transported over WebSocket or DTLS."""
    if len(raw) < 3:
        return {"error": "payload too short", "raw": raw.hex()}

    prefix = raw[0]
    cmd_id = struct.unpack_from("<H", raw, 1)[0]
    data = raw[3:]

    result: dict[str, Any] = {
        "cmd_id": cmd_id,
        "cmd_hex": f"0x{cmd_id:04x}",
        "prefix": prefix,
        "data_len": len(data),
        "data_hex": data.hex(),
    }

    if cmd_id == 0x0068:
        result.update(_parse_state(data))
    elif cmd_id == 0x006A:
        result.update(_parse_dosing_state(data))
    elif cmd_id == 0x012C:
        result.update(_parse_light_state(data))
    elif cmd_id == LIGHT_CAPABILITIES_CMD_ID:
        result.update(_parse_light_capabilities(data))
    elif cmd_id == 0x0069:
        result.update(_parse_capabilities(data))
    elif cmd_id == 0x0066:
        result.update(_parse_setpoint(data))
    elif cmd_id == 0x0258:
        result.update(_parse_probe_statistics(data))
    elif cmd_id == 0x0259:
        result.update(_parse_measurements(data))
    elif cmd_id == 0x025A:
        result.update(_parse_statistics_b(data))
    elif cmd_id == 0x0009:
        result.update(_parse_temperature(data))
    elif cmd_id == 0x0324:
        # 0x0324 is a multi-record CONFIG family. NOT live runtime pump speed.
        # Sub-records rotate through data[0] in {0, 1, 2, 3, 7, ...}; each sub
        # carries a different field. Historically this parser conflated sub=0
        # and sub=3 into a single `pump_speed`, which made the state-change
        # detector flap Medium ↔ High every time the controller emitted a new
        # sub-record on the 0x0324 carousel.
        #
        # Corrected mapping:
        #   sub=0 data[4]  -> `manual_speed_action_code` / `manual_speed_action`
        #                     (4/5/6 = Low/Medium/High. echo of the last
        #                     manual write via 0x01F4).
        #   sub=3 data[2]  -> `configured_speed_code` / `configured_speed`
        #                     (0/1/2/3 = Low/Medium/High/AI. the default or
        #                     configured pump speed slot).
        #
        # Backwards-compat: legacy `pump_speed` / `pump_speed_code` keys are
        # STILL populated alongside the new namespaced fields. Downstream code
        # that is already `sub_command`-aware (websocket_client.py) handles
        # the assignment correctly; the bug was at the level of consumers
        # (e.g. the halo-capture-app state-change detector) that ignored
        # `sub_command` and treated every `pump_speed` value as a live
        # transition. New consumers SHOULD prefer the namespaced fields and
        # derive live runtime speed from 0x0192 (TIMER_STATE.profile_index)
        # × 0x0193[slot].speed_code instead.
        sub = data[0] if data else 0
        result["type"] = "config"
        result["sub_command"] = sub
        if sub == 0x03 and len(data) >= 3:
            code = data[2]
            speed = SPEED_LEVELS.get(code, f"Unknown({code})")
            result["configured_speed_code"] = code
            result["configured_speed"] = speed
            # Legacy aliases for backward compatibility.
            result["pump_speed_code"] = code
            result["pump_speed"] = speed
        elif sub == 0x00 and len(data) >= 5:
            action_code = data[4]
            action = MANUAL_SPEED_ACTIONS.get(action_code, f"Unknown({action_code})")
            result["manual_speed_action_code"] = action_code
            result["manual_speed_action"] = action
            # Legacy aliases: only populate for the known action codes
            # (4/5/6) to preserve the pre-fix semantics where unknown action
            # codes left `pump_speed` unset.
            if action_code in MANUAL_SPEED_ACTIONS:
                result["pump_speed_code"] = action_code
                result["pump_speed"] = action
    elif cmd_id == 0x00CA:
        # Confirmed by 2026-05-12 Halo capture scans: byte 0 is the live
        # timer pump speed code for the currently active timer/profile
        # (0=Low, 1=Medium, 2=High). It retains last value while off/standby,
        # so consumers should only treat it as operating speed when a timer
        # profile or priming state is active.
        result["type"] = "timer_pump_speed"
        if data:
            code = data[0]
            result["timer_pump_speed_code"] = code
            result["timer_pump_speed"] = SPEED_LEVELS.get(code, f"Unknown({code})")
            # Legacy aliases retained for capture tooling/tests that still
            # read the old transition-index hypothesis names.
            result["transition_index"] = code
            result["index"] = code
        result["raw_data_hex"] = data.hex()
    elif cmd_id == 0x0190:
        result.update(parse_timer_capabilities(data))
    elif cmd_id == 0x0191:
        result.update(parse_timer_setup(data))
    elif cmd_id == 0x0192:
        result.update(parse_timer_state(data))
    elif cmd_id == 0x0193:
        result.update(parse_timer_config(data))
    elif cmd_id == 0x0064:
        result.update(_parse_settings(data))
    elif cmd_id == 0x0065:
        result.update(_parse_water_volume(data))
    elif cmd_id == 0x0002:
        result.update(_parse_controller_time(data))
    elif cmd_id == 0x0003:
        result.update(_parse_controller_date(data))
    elif cmd_id == 0x044E:
        result.update(_parse_heater_state(data))
    elif cmd_id == 0x0451:
        result.update(_parse_heat_demand_settings(data))
    elif cmd_id == 0x0514:
        result.update(_parse_gpo_setup(data))
    elif cmd_id == 0x0516:
        result.update(_parse_valve_setup(data))
    elif cmd_id == VALVE_CUSTOM_NAME_CMD_ID:
        result.update(_parse_valve_custom_name_chunk(data))
    elif cmd_id == 0x0019:
        result["type"] = "unknown_0x0019"
    else:
        result["type"] = f"unknown_0x{cmd_id:04x}"

    return result
