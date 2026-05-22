"""Receive-watchdog and fatal-session handling tests."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from pychlorinator_cloud.websocket_client import HaloWebSocketClient


class ReceiveWatchdogTests(unittest.IsolatedAsyncioTestCase):
    async def test_watchdog_fires_after_timeout(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        client._running = True
        client.data.connected = True
        client._last_message_received_at = 0.0
        client._handle_fatal_session = AsyncMock()
        now = 0.0

        async def fake_sleep(delay: float) -> None:
            nonlocal now
            now += delay

        with (
            patch("pychlorinator_cloud.websocket_client.asyncio.sleep", fake_sleep),
            patch("pychlorinator_cloud.websocket_client.time.monotonic", lambda: now),
        ):
            await client._receive_watchdog()

        client._handle_fatal_session.assert_awaited_once_with(
            "receive_watchdog_timeout"
        )

    async def test_keepalive_resets_watchdog(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        client._running = True
        client.data.connected = True
        client._last_message_received_at = 0.0
        client._handle_fatal_session = AsyncMock()
        now = 0.0

        async def fake_sleep(delay: float) -> None:
            nonlocal now
            now += delay
            client._last_message_received_at = now
            if now >= 16.0:
                client._running = False
                client.data.connected = False

        with (
            patch("pychlorinator_cloud.websocket_client.asyncio.sleep", fake_sleep),
            patch("pychlorinator_cloud.websocket_client.time.monotonic", lambda: now),
        ):
            await client._receive_watchdog()

        client._handle_fatal_session.assert_not_awaited()

    async def test_dataexchangeerror_triggers_fatal(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        client._handle_fatal_session = AsyncMock()

        should_continue = await client._handle_incoming_message(
            {"type": "dataexchangeerror", "payload": {}}
        )

        self.assertFalse(should_continue)
        client._handle_fatal_session.assert_awaited_once_with("dataexchangeerror")

    async def test_server_disconnect_triggers_fatal(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        client._handle_fatal_session = AsyncMock()

        should_continue = await client._handle_incoming_message({"type": "disconnect"})

        self.assertFalse(should_continue)
        self.assertTrue(client._quiet_reconnect)
        client._handle_fatal_session.assert_awaited_once_with("server_disconnect")

    async def test_fatal_handler_is_idempotent(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        websocket = AsyncMock()
        client._ws = websocket
        client._running = True
        client.data.connected = True

        await client._handle_fatal_session("first")
        await client._handle_fatal_session("second")

        websocket.send.assert_awaited_once()
        websocket.close.assert_awaited_once()
        self.assertIsNone(client._ws)
        self.assertFalse(client._running)
        self.assertFalse(client.data.connected)

    async def test_watchdog_cancels_on_normal_disconnect(self) -> None:
        client = HaloWebSocketClient("serial", "user", "pass")
        client._running = True
        client.data.connected = True
        task = asyncio.create_task(asyncio.sleep(60))
        client._watchdog_task = task

        await client.disconnect()

        self.assertTrue(task.cancelled())
        self.assertIsNone(client._watchdog_task)


if __name__ == "__main__":
    unittest.main()
