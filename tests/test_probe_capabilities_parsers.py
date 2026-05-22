"""Regression tests for probe statistics and capabilities parsers."""

from __future__ import annotations

from pychlorinator_cloud.payload_parsers import (
    _parse_capabilities,
    _parse_probe_statistics,
)


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
