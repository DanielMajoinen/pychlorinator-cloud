"""Regression tests for WebSocket disconnect-storm fixes."""

from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from pychlorinator_cloud.websocket_client import (
    HaloWebSocketClient,
)


class _FakeWebSocket:
    def __init__(self, response: str | None = None) -> None:
        self.sent: list[str] = []
        self._response = response
        self.close = AsyncMock()

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        if self._response is None:
            raise AssertionError("recv called without a configured response")
        return self._response


class _FakeConnect:
    def __init__(self, websocket: _FakeWebSocket) -> None:
        self.websocket = websocket

    def __await__(self):
        async def _return_websocket():
            return self.websocket

        return _return_websocket().__await__()

    async def __aenter__(self) -> _FakeWebSocket:
        return self.websocket

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class CompactJsonTests(unittest.IsolatedAsyncioTestCase):
    def assert_compact(self, message: str) -> None:
        encoded = message.encode()
        self.assertNotIn(b": ", encoded)
        self.assertNotIn(b", ", encoded)

    async def test_outbound_websocket_frames_use_compact_json(self) -> None:
        connect_ws = _FakeWebSocket(
            json.dumps(
                {
                    "type": "connectresp",
                    "success": 1,
                    "payload": {
                        "accesslevel": 2,
                        "buildinfo": {"protocol": "2.0", "pbver": "1.0"},
                    },
                }
            )
        )
        client = HaloWebSocketClient("serial", "user", "pass")
        client.preflight_availability = AsyncMock(return_value={"payload": {}})
        client._get_ssl_context = AsyncMock(return_value=None)
        client._receive_loop = AsyncMock()
        client._keepalive_loop = AsyncMock()
        client._receive_watchdog = AsyncMock()
        client._request_all_data = AsyncMock()

        with patch(
            "pychlorinator_cloud.websocket_client.websockets.connect",
            return_value=_FakeConnect(connect_ws),
        ):
            await client.connect()

        self.assertEqual(
            connect_ws.sent[0],
            (
                '{"type":"connect","name":"serial","payload":'
                '{"userName":"user","password":"pass"}}'
            ),
        )
        self.assert_compact(connect_ws.sent[0])
        await client.disconnect()

        query_ws = _FakeWebSocket('{"type":"queryresp","success":1,"payload":{}}')
        query_client = HaloWebSocketClient("serial", "user", "pass")
        query_client._get_ssl_context = AsyncMock(return_value=None)
        with patch(
            "pychlorinator_cloud.websocket_client.websockets.connect",
            return_value=_FakeConnect(query_ws),
        ):
            await query_client.query_availability()

        self.assertEqual(query_ws.sent[0], '{"type":"query","name":"serial"}')
        self.assert_compact(query_ws.sent[0])

        command_ws = _FakeWebSocket()
        command_client = HaloWebSocketClient("serial", "user", "pass")
        command_client._ws = command_ws
        command_client.data.connected = True
        await command_client.send_command(b"\x02\x02\x00" + bytes(17))

        self.assertEqual(
            command_ws.sent[0],
            '{"type":"dataexchange","payload":{"data":"AgIAAAAAAAAAAAAAAAAAAAAAAAA="}}',
        )
        self.assert_compact(command_ws.sent[0])

        disconnect_ws = _FakeWebSocket()
        disconnect_client = HaloWebSocketClient("serial", "user", "pass")
        disconnect_client._ws = disconnect_ws
        await disconnect_client.disconnect()

        self.assertEqual(disconnect_ws.sent[0], '{"type":"disconnect"}')
        self.assert_compact(disconnect_ws.sent[0])

        keepalive_ws = _FakeWebSocket()
        keepalive_client = HaloWebSocketClient("serial", "user", "pass")
        keepalive_client._ws = keepalive_ws
        keepalive_client._running = True

        async def request_data(_cmd_id: int, *, source: str = "request_data") -> None:
            keepalive_client._running = False

        keepalive_client.request_data = request_data

        async def fake_sleep(_delay: float) -> None:
            return None

        with patch("pychlorinator_cloud.websocket_client.asyncio.sleep", fake_sleep):
            await keepalive_client._keepalive_loop()

        self.assertEqual(keepalive_ws.sent[0], '{"type":"keepalive"}')
        self.assertIn(b'{"type":"keepalive"}', keepalive_ws.sent[0].encode())
        self.assert_compact(keepalive_ws.sent[0])


class FailClosedKeepaliveTests(unittest.IsolatedAsyncioTestCase):
    async def test_keepalive_send_failure_schedules_fatal_session(self) -> None:
        original_create_task = asyncio.create_task
        client = HaloWebSocketClient("serial", "user", "pass")
        websocket = AsyncMock()
        websocket.send.side_effect = [ConnectionResetError("boom"), None]
        client._ws = websocket
        client._running = True
        client.data.connected = True

        async def fake_sleep(_delay: float) -> None:
            return None

        created_task = None

        def fake_create_task(coro):
            nonlocal created_task
            created_task = original_create_task(coro)
            return created_task

        with (
            patch("pychlorinator_cloud.websocket_client.asyncio.sleep", fake_sleep),
            patch(
                "pychlorinator_cloud.websocket_client.asyncio.create_task",
                fake_create_task,
            ),
        ):
            await client._keepalive_loop()

        assert created_task is not None
        await created_task

        self.assertFalse(client.data.connected)
        self.assertFalse(client._running)
        self.assertIsNone(client._ws)
        self.assertEqual(websocket.send.await_args_list[0].args[0], '{"type":"keepalive"}')
        self.assertEqual(websocket.send.await_args_list[1].args[0], '{"type":"disconnect"}')

    async def test_keepalive_failure_uses_expected_fatal_reason(self) -> None:
        original_create_task = asyncio.create_task
        client = HaloWebSocketClient("serial", "user", "pass")
        websocket = AsyncMock()
        websocket.send.side_effect = ConnectionResetError("boom")
        client._ws = websocket
        client._running = True
        client.data.connected = True
        client._handle_fatal_session = AsyncMock()

        async def fake_sleep(_delay: float) -> None:
            return None

        created_task = None

        def fake_create_task(coro):
            nonlocal created_task
            created_task = original_create_task(coro)
            return created_task

        with (
            patch("pychlorinator_cloud.websocket_client.asyncio.sleep", fake_sleep),
            patch(
                "pychlorinator_cloud.websocket_client.asyncio.create_task",
                fake_create_task,
            ),
        ):
            await client._keepalive_loop()

        assert created_task is not None
        await created_task
        client._handle_fatal_session.assert_awaited_once_with("keepalive_send_failed")


# NOTE(2026-05-21): VomitHandshakeTests removed alongside the production revert
# of the vomit-handshake change. The experimental 0x006B + 0x0005 pre-reads
# caused a connectresp-timeout regression during a 30-minute live soak test.
# Will be reintroduced once a TCS-style synchronous wait on the 0x0005 response
# is implemented and tested against the vendor capture.


if __name__ == "__main__":
    unittest.main()
