from __future__ import annotations

import base64
import datetime as dt
import json
import struct
import unittest

from scripts.raw_ws_capture import (
    build_ha_service_request,
    decode_dataexchange,
    is_remote_disconnect_message,
    make_read_command,
    parse_phase_window,
    phase_for,
    redact_message,
)


def _raw(cmd_id: int, data: bytes, prefix: int = 0x03) -> bytes:
    return bytes([prefix]) + struct.pack("<H", cmd_id) + data


class TestRawWsCapture(unittest.TestCase):
    def test_make_read_command_is_prefix_02_with_padded_body(self):
        cmd = make_read_command(0x0068)
        self.assertEqual(cmd[0], 0x02)
        self.assertEqual(struct.unpack_from("<H", cmd, 1)[0], 0x0068)
        self.assertEqual(len(cmd), 20)
        self.assertEqual(cmd[3:], bytes(17))

    def test_decode_dataexchange_preserves_raw_and_parser_values(self):
        # 0x0324 sub 0x00, action code 0x06 => current parser labels High.
        frame = _raw(0x0324, bytes([0x00, 0x00, 0x00, 0x00, 0x06]))
        msg = {
            "type": "dataexchange",
            "payload": {"data": base64.b64encode(frame).decode("ascii")},
        }
        decoded = decode_dataexchange(msg)
        assert decoded is not None
        self.assertEqual(decoded["raw_hex"], frame.hex())
        self.assertEqual(decoded["prefix"], 0x03)
        self.assertEqual(decoded["cmd_id"], 0x0324)
        self.assertEqual(decoded["cmd_hex"], "0x0324")
        self.assertEqual(decoded["parsed"]["sub_command"], 0)
        self.assertEqual(decoded["parsed"]["pump_speed_code"], 6)
        self.assertEqual(decoded["parsed"]["pump_speed"], "High")

    def test_decode_dataexchange_records_bad_base64(self):
        decoded = decode_dataexchange({"type": "dataexchange", "payload": {"data": "not base64!!"}})
        assert decoded is not None
        self.assertIn("decode_error", decoded)

    def test_phase_for_pump_test(self):
        start = dt.datetime(2026, 5, 9, 7, 0, tzinfo=dt.timezone(dt.timedelta(hours=8)))
        self.assertEqual(phase_for(start - dt.timedelta(seconds=1), start), "Baseline/pre-test")
        self.assertEqual(phase_for(start + dt.timedelta(minutes=1), start), "Low")
        self.assertEqual(phase_for(start + dt.timedelta(minutes=11), start), "Medium")
        self.assertEqual(phase_for(start + dt.timedelta(minutes=21), start), "High")
        self.assertEqual(phase_for(start + dt.timedelta(minutes=31), start), "AI/Auto")

    def test_custom_phase_windows_override_template(self):
        reference = dt.datetime(2026, 5, 9, 13, 25, tzinfo=dt.timezone(dt.timedelta(hours=8)))
        windows = (
            parse_phase_window("Baseline=13:25,13:30", reference),
            parse_phase_window("Low=13:30,13:45", reference),
            parse_phase_window("Medium=13:46,14:00", reference),
            parse_phase_window("High=14:01,14:15", reference),
            parse_phase_window("Off=14:15,14:25", reference),
        )
        self.assertEqual(phase_for(reference + dt.timedelta(minutes=1), None, windows), "Baseline")
        self.assertEqual(phase_for(reference + dt.timedelta(minutes=10), None, windows), "Low")
        self.assertEqual(phase_for(reference + dt.timedelta(minutes=22), None, windows), "Medium")
        self.assertEqual(phase_for(reference + dt.timedelta(minutes=37), None, windows), "High")
        self.assertEqual(phase_for(reference + dt.timedelta(minutes=53), None, windows), "Off")

    def test_remote_disconnect_message_detection(self):
        self.assertTrue(is_remote_disconnect_message({"type": "disconnect"}))
        self.assertFalse(is_remote_disconnect_message({"type": "dataexchangeerror"}))

    def test_redact_message_hides_credentials(self):
        redacted = redact_message(
            {
                "type": "connect",
                "name": "1234567",
                "payload": {"userName": "rob@example.test", "password": "secret"},
            }
        )
        self.assertEqual(redacted["payload"]["userName"], "<redacted>")
        self.assertEqual(redacted["payload"]["password"], "<redacted>")
        # Ensure it is JSON-serializable for JSONL logging.
        json.dumps(redacted)

    def test_build_ha_service_request(self):
        req = build_ha_service_request(
            "http://ha.local:8123/",
            "token123",
            "button",
            "press",
            {"entity_id": "button.halo_1234567_pause_cloud_connection"},
        )
        self.assertEqual(req.full_url, "http://ha.local:8123/api/services/button/press")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers["Authorization"], "Bearer token123")
        self.assertEqual(req.headers["Content-type"], "application/json")
        self.assertEqual(
            json.loads(req.data.decode("utf-8")),
            {"entity_id": "button.halo_1234567_pause_cloud_connection"},
        )


if __name__ == "__main__":
    unittest.main()
