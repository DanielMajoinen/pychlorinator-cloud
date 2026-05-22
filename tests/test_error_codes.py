"""Tests for decoded controller error-info codes."""

from __future__ import annotations

import struct

from pychlorinator_cloud.error_codes import ERROR_CODE_TABLE, ERROR_MESSAGE_OPTIONS
from pychlorinator_cloud.payload_parsers import parse_data_payload
from pychlorinator_cloud.websocket_client import HaloWebSocketClient


EXPECTED_CODES = {
    1,
    2,
    3,
    4,
    5,
    9,
    10,
    11,
    12,
    50,
    51,
    52,
    53,
    54,
    *range(100, 105),
    *range(150, 159),
    *range(200, 208),
    *range(300, 310),
    *range(320, 323),
    400,
    401,
    450,
    500,
    501,
    *range(600, 604),
    *range(700, 713),
    850,
    900,
    901,
    902,
    1400,
    65535,
}


def _state_raw(error_info: int) -> bytes:
    payload = bytearray(15)
    payload[4] = 5  # Standby
    struct.pack_into("<H", payload, 13, error_info)
    return bytes([0x03]) + struct.pack("<H", 0x0068) + bytes(payload)


def _parse_error_info(error_info: int):
    client = HaloWebSocketClient("serial", "user", "pass")
    if error_info > 0xFFFF:
        client._update_data(
            {
                "type": "state",
                "cmd_id": 0x0068,
                "error": None,
                "error_info": error_info,
                "info_message_code": 5,
            },
            b"",
        )
        return client.data
    raw = _state_raw(error_info)
    client._update_data(parse_data_payload(raw), raw)
    return client.data


def test_error_code_table_contains_expected_codes() -> None:
    assert set(ERROR_CODE_TABLE) == EXPECTED_CODES


def test_error_707_is_dosing_disabled_information_acid() -> None:
    info = ERROR_CODE_TABLE[707]

    assert info.label == "Dosing Disabled"
    assert info.severity == "Information"
    assert info.category == "Acid"
    assert info.action is not None
    assert "enable acid dosing" in info.action.lower()


def test_700_series_corrected_labels() -> None:
    assert ERROR_CODE_TABLE[703].label == "Down Rating (rate 2)"
    assert ERROR_CODE_TABLE[705].label == "Pump Protect"
    assert ERROR_CODE_TABLE[706].label == "Water Sampling"
    assert ERROR_CODE_TABLE[708].label == "Water Too Cold"


def test_error_code_severity_classification() -> None:
    for code in range(1, 6):
        assert ERROR_CODE_TABLE[code].severity == "Fault"
    assert ERROR_CODE_TABLE[9].severity == "Warning"
    assert ERROR_CODE_TABLE[50].severity == "Information"
    for code in range(100, 105):
        assert ERROR_CODE_TABLE[code].severity == "Fault"
    for code in range(200, 208):
        assert ERROR_CODE_TABLE[code].severity == "Warning"
    for code in (*range(300, 310), *range(320, 323)):
        assert ERROR_CODE_TABLE[code].severity == "Fault"
    for code in (400, 401, 450):
        assert ERROR_CODE_TABLE[code].severity == "Fault"
    for code in (500, 501):
        assert ERROR_CODE_TABLE[code].severity == "Fault"
    for code in range(600, 604):
        assert ERROR_CODE_TABLE[code].severity == "Fault"
    for code in range(700, 713):
        assert ERROR_CODE_TABLE[code].severity == "Information"
    for code in (850, 900, 901, 902):
        assert ERROR_CODE_TABLE[code].severity == "Warning"
    assert ERROR_CODE_TABLE[1400].severity == "Warning"
    assert ERROR_CODE_TABLE[1400].category == "Network"
    assert ERROR_CODE_TABLE[65535].severity == "Warning"
    assert ERROR_CODE_TABLE[65535].category == "Unknown"


def test_error_message_options_include_corrected_labels_not_legacy_names() -> None:
    assert "Dosing Disabled" in ERROR_MESSAGE_OPTIONS
    assert "Water Sampling" in ERROR_MESSAGE_OPTIONS
    assert "SamplingOnly" not in ERROR_MESSAGE_OPTIONS
    assert "DosingDisabled" not in ERROR_MESSAGE_OPTIONS


def test_unknown_error_code_parses_as_unknown_label() -> None:
    assert ERROR_CODE_TABLE.get(99999) is None

    data = _parse_error_info(99999)

    assert data.error_message == "Unknown (99999)"
    assert data.error_severity == "Unknown"
    assert data.error_category == "Unknown"
    assert data.error_reason is None
    assert data.error_action is None


def test_error_info_zero_parses_as_no_error_and_clears_details() -> None:
    data = _parse_error_info(0)

    assert data.error_message == "NoError"
    assert data.error_severity is None
    assert data.error_category is None
    assert data.error_reason is None
    assert data.error_action is None
