"""Tests for dosing/maintenance state payload parsing."""

from __future__ import annotations

import struct
import unittest

from pychlorinator_cloud.payload_parsers import parse_data_payload


BASELINE_PAYLOAD = bytes.fromhex("020803020007b600000000000112809000")
POST_RESTART_PAYLOAD = bytes.fromhex("00e1020200404f01000000000112809000")
POST_RESET_PAYLOAD = bytes.fromhex("00990502001ca700000000000112809000")


def _make_raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


class TestParseDosingState(unittest.TestCase):
    def test_known_capture_values(self):
        cases = [
            (BASELINE_PAYLOAD, 776, 46599),
            (POST_RESTART_PAYLOAD, 737, 85824),
            (POST_RESET_PAYLOAD, 1433, 42780),
        ]

        for payload, acid_minutes, filter_seconds in cases:
            with self.subTest(payload=payload.hex()):
                result = parse_data_payload(_make_raw(0x006A, payload))

                self.assertEqual(result["type"], "dosing_state")
                self.assertEqual(
                    result["acid_hold_remaining_minutes"],
                    acid_minutes,
                )
                self.assertEqual(result["filter_remaining_seconds"], filter_seconds)
                self.assertEqual(result["acid_dosing_state"], "OffForPeriod")

    def test_zero_acid_payload_resumes_now(self):
        payload = bytearray(BASELINE_PAYLOAD)
        payload[1:3] = b"\x00\x00"

        result = parse_data_payload(_make_raw(0x006A, bytes(payload)))

        self.assertEqual(result["acid_hold_remaining_minutes"], 0)
        self.assertEqual(result["acid_dosing_state"], "ResumeNow")
