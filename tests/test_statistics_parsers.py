"""Regression tests for Halo statistics payload parsers."""

from __future__ import annotations

import struct

from pychlorinator_cloud.payload_parsers import (
    _parse_capabilities,
    _parse_probe_statistics,
    _parse_statistics_b,
    parse_data_payload,
)
from pychlorinator_cloud.websocket_client import HaloWebSocketClient


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


def test_statistics_a_0x0259_baseline_capture() -> None:
    result = parse_data_payload(
        _make_raw(0x0259, bytes.fromhex("4e04a81300002a0200002200005a019000"))
    )

    assert result["type"] == "statistics_a"
    assert result["operating_days"] == 1102
    assert result["unknown_counter_a"] == 5032
    assert result["cell_reversal_count"] == 554
    assert result["previous_days_cell_load_percent"] == 34
    assert result["today_cell_runtime_minutes"] == 346
    assert result["stats_flag_byte"] == 144
    assert "water_temperature_c" not in result
    assert "cell_current_ma" not in result


def test_statistics_b_0x025a_baseline_capture() -> None:
    result = _parse_statistics_b(bytes.fromhex("09100000549e04007b0901000000000000"))

    assert result["type"] == "statistics_b"
    assert result["power_board_runtime_hours"] == 4105
    assert "cell_running_time_minutes" not in result


def test_parse_probe_statistics_0x0258() -> None:
    result = _parse_probe_statistics(
        bytes.fromhex("5900400300000000000000000000000000")
    )

    assert result["type"] == "probe_statistics"
    assert result["highest_ph_measured"] == 8.9
    assert result["lowest_ph_measured"] == 0.0
    assert result["highest_orp_measured"] == 832
    assert result["lowest_orp_measured"] == 0


def test_parse_capabilities_0x0069() -> None:
    result = _parse_capabilities(bytes.fromhex("0202000000000000000000000000000000"))

    assert result["type"] == "capabilities"
    assert result["min_manual_acid_setpoint"] == 2
    assert result["max_manual_acid_setpoint"] == 2
    assert result["min_manual_chlorine_setpoint"] == 0
    assert result["min_ph_setpoint"] == 0.0
    assert result["min_orp_setpoint"] == 0
    assert result["ph_control_type"] == "None"


def test_state_0x0068_chemistry_flags() -> None:
    # StateCharacteristic2 flag bits from vendor decompile, overlaid onto the
    # existing 0x0068 state-payload test shape.
    flags = 0x0083  # PHMeasurementValid | FirstPHResultReceived | SanitisingUntil...
    state_payload = bytes([flags & 0xFF, flags >> 8]) + struct.pack(
        "<HBBHBBBxx",
        1234,
        1,
        3,
        700,
        9,
        74,
        0,
    ) + b"\x00" * 5

    result = parse_data_payload(_make_raw(0x0068, state_payload))

    assert result["chemistry_values_current"] is True
    assert result["chemistry_values_valid"] is True
    assert result["sanitising_until_next_timer_tomorrow"] is True


def test_live_data_sources_temperature_and_cell_current_from_correct_commands() -> None:
    client = HaloWebSocketClient("serial", "user", "pass")

    stats_raw = _make_raw(0x0259, bytes.fromhex("4e04a81300002a0200002200005a019000"))
    client._update_data(parse_data_payload(stats_raw), stats_raw)
    assert client.data.operating_days == 1102
    assert client.data.water_temperature_c is None
    assert client.data.water_temperature_precise is None
    assert client.data.cell_current_ma is None

    temp_payload = struct.pack(
        "<BBHHHHBHHB",
        0,
        0,
        250,
        160,
        160,
        0,
        1,
        0,
        0,
        0,
    )
    temp_raw = _make_raw(0x0009, temp_payload)
    client._update_data(parse_data_payload(temp_raw), temp_raw)
    assert client.data.water_temperature_c == 16.0
    assert client.data.water_temperature_precise == 16.0

    state_payload = bytes([0x02, 0x05]) + struct.pack("<H", 1234) + (b"\x00" * 11)
    state_raw = _make_raw(0x0068, state_payload)
    client._update_data(parse_data_payload(state_raw), state_raw)
    assert client.data.cell_current_ma == 1234
