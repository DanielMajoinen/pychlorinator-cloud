"""Decoded SubText4 error-info table from the Halo vendor app resources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ErrorInfo:
    """Structured details for a controller error-info code."""

    code: int
    label: str
    reason: str | None
    action: str | None
    severity: str
    category: str


def _info(
    code: int,
    label: str,
    reason: str | None,
    action: str | None,
    severity: str,
    category: str,
) -> ErrorInfo:
    return ErrorInfo(
        code=code,
        label=label,
        reason=reason,
        action=action,
        severity=severity,
        category=category,
    )


_RESTART_SERVICE = "Restart the chlorinator; contact service if the fault persists."
_SENSOR_WIRING = "Check for damaged wiring or poor connection; replace the sensor or contact service if needed."
_PUMP_SERVICE = "Review the pump fault detail; contact service if the fault persists."
_HEATER_SERVICE = "Review heater diagnostics; contact service if the fault persists."
_EQUIPMENT_SERVICE = "Check the communication cable; restart the chlorinator; contact service if the fault persists."
_SOLAR_SENSOR = "Check for damaged wiring or poor connection; replace sensor with a known good part."


ERROR_CODE_TABLE: Final[dict[int, ErrorInfo]] = {
    1: _info(
        1,
        "Hardware Fault (IO expander)",
        "Hardware Fault (IO expander)",
        _RESTART_SERVICE,
        "Fault",
        "Hardware",
    ),
    2: _info(
        2,
        "Hardware Fault (EEPROM)",
        "Hardware Fault (EEPROM)",
        _RESTART_SERVICE,
        "Fault",
        "Hardware",
    ),
    3: _info(
        3,
        "Hardware Fault (RTC)",
        "Hardware Fault (RTC)",
        _RESTART_SERVICE,
        "Fault",
        "Hardware",
    ),
    4: _info(
        4,
        "Hardware Fault (User Panel Comms)",
        "Hardware Fault (User Panel Comms)",
        _RESTART_SERVICE,
        "Fault",
        "Hardware",
    ),
    5: _info(
        5,
        "Hardware Fault (User Panel Comms)",
        "Hardware Fault (User Panel Comms)",
        _RESTART_SERVICE,
        "Fault",
        "Hardware",
    ),
    9: _info(
        9,
        "Over Temperature",
        "Over Temperature",
        "Turn off the chlorinator and allow it to cool down; check vents and fan.",
        "Warning",
        "Hardware",
    ),
    10: _info(
        10,
        "Temperature Sensor Error",
        "Chlorinator temperature sensor short circuit",
        _SENSOR_WIRING,
        "Fault",
        "Sensor",
    ),
    11: _info(
        11,
        "Temperature Sensor Error",
        "Chlorinator temperature sensor open circuit",
        _SENSOR_WIRING,
        "Fault",
        "Sensor",
    ),
    12: _info(
        12,
        "Factory Reset",
        "EEPROM restored to defaults",
        None,
        "Information",
        "Maintenance",
    ),
    50: _info(
        50,
        "Update Successful",
        "Software update is successful",
        None,
        "Information",
        "Firmware",
    ),
    51: _info(
        51,
        "Update Failed",
        "Software update has failed",
        "Check the internet connection before attempting another update.",
        "Warning",
        "Firmware",
    ),
    52: _info(
        52,
        "Update Available",
        "Software update is available",
        "Use settings to install or check for updates.",
        "Information",
        "Firmware",
    ),
    53: _info(
        53,
        "Hardware Fault (User Panel Comms)",
        "Hardware Fault (User Panel Comms)",
        _RESTART_SERVICE,
        "Fault",
        "Hardware",
    ),
    54: _info(
        54,
        "Hardware Fault (Ethernet)",
        "Hardware Fault (Ethernet)",
        _RESTART_SERVICE,
        "Fault",
        "Network",
    ),
    100: _info(
        100,
        "Pump Fault",
        "Astral/Viron pump communications have been lost",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    101: _info(
        101,
        "Pump Fault",
        "Astral/Viron pump under voltage",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    102: _info(
        102,
        "Pump Fault",
        "Astral/Viron pump over temperature",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    103: _info(
        103,
        "Pump Fault",
        "Astral/Viron pump over current",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    104: _info(
        104,
        "Pump Fault",
        "Astral/Viron pump blocked suction",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    150: _info(
        150, "Pump Fault", "Zodiac pump general fault", _PUMP_SERVICE, "Fault", "Pump"
    ),
    151: _info(
        151, "Pump Fault", "Zodiac pump limit fault", _PUMP_SERVICE, "Fault", "Pump"
    ),
    152: _info(
        152, "Pump Fault", "Zodiac pump voltage fault", _PUMP_SERVICE, "Fault", "Pump"
    ),
    153: _info(
        153,
        "Pump Fault",
        "Zodiac pump commutation fault",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    154: _info(
        154,
        "Pump Fault",
        "Zodiac pump temperature fault",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    155: _info(
        155, "Pump Fault", "Zodiac pump software fault", _PUMP_SERVICE, "Fault", "Pump"
    ),
    156: _info(
        156,
        "Pump Fault",
        "Zodiac pump motor starting fault",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    157: _info(
        157,
        "Pump Fault",
        "Zodiac pump commutation error",
        _PUMP_SERVICE,
        "Fault",
        "Pump",
    ),
    158: _info(
        158, "Pump Fault", "Zodiac pump blocked", _PUMP_SERVICE, "Fault", "Pump"
    ),
    200: _info(
        200,
        "pH Sensor Fault",
        "pH probe has lost communications",
        "Check the sensor signal strength.",
        "Warning",
        "Chemistry",
    ),
    201: _info(
        201,
        "ORP Sensor Fault",
        "ORP probe has lost communications",
        "Check the sensor signal strength.",
        "Warning",
        "Chemistry",
    ),
    202: _info(
        202,
        "pH Sensor Fault",
        "pH value is too high",
        "Manually test the pool pH level.",
        "Warning",
        "Chemistry",
    ),
    203: _info(
        203,
        "ORP Sensor Fault",
        "ORP value is too high",
        "Manually test the pool ORP level.",
        "Warning",
        "Chemistry",
    ),
    204: _info(
        204,
        "pH Sensor Fault",
        "pH value is too low",
        "Manually test the pool pH level.",
        "Warning",
        "Chemistry",
    ),
    205: _info(
        205,
        "ORP Sensor Fault",
        "ORP value is too low",
        "Manually test the pool ORP level.",
        "Warning",
        "Chemistry",
    ),
    206: _info(
        206,
        "pH Sensor Fault",
        "pH access code error",
        "Re-pair the sensor.",
        "Warning",
        "Chemistry",
    ),
    207: _info(
        207,
        "ORP Sensor Fault",
        "ORP access code error",
        "Re-pair the sensor.",
        "Warning",
        "Chemistry",
    ),
    300: _info(
        300,
        "Heater Fault",
        "No communications to the heater",
        _HEATER_SERVICE,
        "Fault",
        "Heater",
    ),
    301: _info(
        301,
        "Heater Fault",
        "Heater Fault 0 - Thermistor freeze condition/open circuit",
        _SENSOR_WIRING,
        "Fault",
        "Heater",
    ),
    302: _info(
        302,
        "Heater Fault",
        "Heater Fault 1 - Thermistor overheat",
        "Allow water to cool below 40C.",
        "Fault",
        "Heater",
    ),
    303: _info(
        303,
        "Heater Fault",
        "Heater Fault 2 - Mechanical overheat",
        "Allow water to cool below 30C.",
        "Fault",
        "Heater",
    ),
    304: _info(
        304,
        "Heater Fault",
        "Heater Fault 3 - Thermistor short circuit",
        _SENSOR_WIRING,
        "Fault",
        "Heater",
    ),
    305: _info(
        305,
        "Heater Fault",
        "Heater Fault 4 - Flame roll-out",
        "Check heat exchanger for blockages; contact service.",
        "Fault",
        "Heater",
    ),
    306: _info(
        306,
        "Heater Fault",
        "Heater Fault 6 - Flue overheat",
        "Phone for service.",
        "Fault",
        "Heater",
    ),
    307: _info(
        307,
        "Heater Fault",
        "Heater Fault 7 - Condensate overflow",
        "Phone for service.",
        "Fault",
        "Heater",
    ),
    308: _info(
        308,
        "Heater Fault",
        "Heater Fault 8 - HX thermistor open circuit",
        _HEATER_SERVICE,
        "Fault",
        "Heater",
    ),
    309: _info(
        309,
        "Heater Fault",
        "Heater Fault 9 - HX thermistor short circuit",
        _HEATER_SERVICE,
        "Fault",
        "Heater",
    ),
    320: _info(
        320,
        "Heater Fault",
        "Heater is in local mode",
        "Return heater to remote mode.",
        "Fault",
        "Heater",
    ),
    321: _info(
        321,
        "Heater Fault",
        "Heat pump fault",
        "Check heatpump for further information.",
        "Fault",
        "Heater",
    ),
    322: _info(
        322,
        "Heater Fault",
        "Heat pump fault",
        "Check heatpump for further information.",
        "Fault",
        "Heater",
    ),
    400: _info(
        400,
        "Equipment Fault",
        "GPO1 has lost communications",
        _EQUIPMENT_SERVICE,
        "Fault",
        "Hardware",
    ),
    401: _info(
        401,
        "Equipment Fault",
        "GPO2 has lost communications",
        _EQUIPMENT_SERVICE,
        "Fault",
        "Hardware",
    ),
    450: _info(
        450,
        "Equipment Fault",
        "Viron Connect 10 communications have been lost",
        _EQUIPMENT_SERVICE,
        "Fault",
        "Hardware",
    ),
    500: _info(
        500,
        "Light Fault",
        "Lighting controller 1 has lost communications",
        "Review lighting controller communications.",
        "Fault",
        "Lighting",
    ),
    501: _info(
        501,
        "Light Fault",
        "Lighting controller 2 has lost communications",
        "Review lighting controller communications.",
        "Fault",
        "Lighting",
    ),
    600: _info(
        600,
        "Solar Fault",
        "Solar roof temperature is short circuit",
        _SOLAR_SENSOR,
        "Fault",
        "Solar",
    ),
    601: _info(
        601,
        "Solar Fault",
        "Solar roof temperature is open circuit",
        _SOLAR_SENSOR,
        "Fault",
        "Solar",
    ),
    602: _info(
        602,
        "Solar Fault",
        "Solar water temperature is short circuit",
        _SOLAR_SENSOR,
        "Fault",
        "Solar",
    ),
    603: _info(
        603,
        "Solar Fault",
        "Solar water temperature is open circuit",
        _SOLAR_SENSOR,
        "Fault",
        "Solar",
    ),
    700: _info(
        700,
        "No Flow",
        "No conductivity",
        "Check the skimmer basket, cell cable, and pump; contact service if needed.",
        "Information",
        "Flow",
    ),
    701: _info(
        701,
        "High Salt",
        "Short circuit software detection",
        "Confirm the salt level is within specification; check cell calcification.",
        "Information",
        "Cell",
    ),
    702: _info(
        702,
        "Low Salt",
        "Driving the PWM close to max and cannot achieve the desired level",
        "Confirm the salt level is within specification; check the cell cable.",
        "Information",
        "Cell",
    ),
    703: _info(
        703,
        "Down Rating (rate 2)",
        "Down rate 2",
        "Chlorine output has been reduced.",
        "Information",
        "Cell",
    ),
    704: _info(
        704,
        "Down Rating (rate 1)",
        "Down rate 1",
        "Chlorine output has been reduced.",
        "Information",
        "Cell",
    ),
    705: _info(
        705,
        "Pump Protect",
        "Pump protection",
        "Check the skimmer basket, cell cable, and pump; contact service if needed.",
        "Information",
        "Pump",
    ),
    706: _info(
        706,
        "Water Sampling",
        "Running at low speed with AI mode enabled, but not in an AI mode timer",
        "No chlorine output while sampling.",
        "Information",
        "Chemistry",
    ),
    707: _info(
        707,
        "Dosing Disabled",
        "Disabled by the user, or disabled by the user for time.",
        "Please enable acid dosing",
        "Information",
        "Acid",
    ),
    708: _info(
        708,
        "Water Too Cold",
        "Water is below a threshold",
        "The chlorinator operates less efficiently at low temperatures.",
        "Information",
        "Cell",
    ),
    709: _info(
        709,
        "Daily Acid Dose Limit",
        "Maximum daily acid dosed",
        "Press OK to reset the limit.",
        "Information",
        "Acid",
    ),
    710: _info(
        710,
        "Cell Disconnected",
        "Cell leads are disconnected",
        None,
        "Information",
        "Cell",
    ),
    711: _info(
        711,
        "Low Flow",
        "Low water flow has been detected",
        "Check the skimmer basket, cell cable, and pump; contact service if needed.",
        "Information",
        "Flow",
    ),
    712: _info(
        712,
        "Mineral Guard",
        "Mineral Guard is close to or past renew time",
        "Replace and reset the timer in the maintenance menu.",
        "Information",
        "Maintenance",
    ),
    850: _info(
        850,
        "pH Sensor Low Battery",
        "Battery is low PH",
        "Replace the pH sensor battery.",
        "Warning",
        "Sensor",
    ),
    900: _info(
        900,
        "pH Sensor Warning",
        "Battery is low PH",
        "Replace the pH sensor battery.",
        "Warning",
        "Sensor",
    ),
    901: _info(
        901,
        "ORP Sensor Warning",
        "Battery is low ORP",
        "Replace the ORP sensor battery.",
        "Warning",
        "Sensor",
    ),
    902: _info(
        902,
        "Sensor Warning",
        "ORP probe is added without a pH probe",
        "Install or pair a pH sensor when using an ORP probe.",
        "Warning",
        "Sensor",
    ),
    1400: _info(
        1400,
        "Unknown Error Code (1400)",
        "Internet connection issue helper",
        "If the fault persists, contact service.",
        "Warning",
        "Network",
    ),
    65535: _info(
        65535,
        "Unknown Error",
        "The user panel or app does not know about the error",
        _RESTART_SERVICE,
        "Warning",
        "Unknown",
    ),
}


ERROR_MESSAGE_OPTIONS: Final[tuple[str, ...]] = (
    "NoError",
    *dict.fromkeys(info.label for info in ERROR_CODE_TABLE.values()).keys(),
)


def error_info_attributes(data: object) -> dict[str, object]:
    """Return vendor decoded controller notice details."""
    return {
        "severity": getattr(data, "error_severity"),
        "category": getattr(data, "error_category"),
        "reason": getattr(data, "error_reason"),
        "recommended_action": getattr(data, "error_action"),
        "raw_code": getattr(data, "salt_error_raw"),
    }


def controller_notice_active(data: object) -> bool | None:
    """Return whether any controller notice is present."""
    raw_code = getattr(data, "salt_error_raw")
    if raw_code is None:
        return None
    return raw_code != 0


def controller_fault_active(data: object) -> bool:
    """Return whether the current controller notice is a fault."""
    return getattr(data, "error_severity") == "Fault"
