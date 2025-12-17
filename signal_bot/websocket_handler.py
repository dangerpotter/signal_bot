"""
WebSocket handler for Signal CLI JSON-RPC mode message receiving.

Provides persistent WebSocket connections for low-latency message delivery.
In json-rpc mode, signal-cli runs as a daemon and delivers messages via WebSocket
instead of requiring HTTP polling.
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connection."""
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0
    ping_interval: float = 20.0
    ping_timeout: float = 10.0


class SignalWebSocketHandler:
    """
    Manages a WebSocket connection to a Signal CLI REST API container.

    Handles:
    - Connection establishment
    - Auto-reconnection with exponential backoff
    - Message parsing and delivery to callback
    - Graceful shutdown
    """

    def __init__(
        self,
        phone_number: str,
        port: int,
        message_callback: Callable[[dict], Awaitable[None]],
        config: Optional[WebSocketConfig] = None
    ):
        """
        Args:
            phone_number: Bot's phone number for the WebSocket URL
            port: Signal API port (e.g., 8080, 8081, 8082)
            message_callback: Async function called for each received message
            config: WebSocket configuration options
        """
        self.phone_number = phone_number
        self.port = port
        self.message_callback = message_callback
        self.config = config or WebSocketConfig()

        self._websocket = None
        self._running = False
        self._reconnect_delay = self.config.reconnect_delay
        self._connection_task: Optional[asyncio.Task] = None
        self._connected = False

    @property
    def ws_url(self) -> str:
        """Construct WebSocket URL for receiving messages."""
        return f"ws://localhost:{self.port}/v1/receive/{self.phone_number}"

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        return self._connected and self._websocket is not None

    async def start(self):
        """Start the WebSocket connection loop."""
        if self._running:
            logger.warning(f"WebSocket handler already running for {self.phone_number}")
            return

        self._running = True
        self._connection_task = asyncio.create_task(
            self._connection_loop(),
            name=f"ws-{self.phone_number}"
        )
        logger.info(f"WebSocket handler started for {self.phone_number} on port {self.port}")

    async def stop(self):
        """Stop the WebSocket connection and cleanup."""
        self._running = False
        self._connected = False

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")

        if self._connection_task:
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass

        logger.info(f"WebSocket handler stopped for {self.phone_number}")

    async def _connection_loop(self):
        """Main connection loop with auto-reconnect."""
        while self._running:
            try:
                logger.info(f"Connecting to WebSocket: {self.ws_url}")

                async with websockets.connect(
                    self.ws_url,
                    ping_interval=self.config.ping_interval,
                    ping_timeout=self.config.ping_timeout,
                ) as websocket:
                    self._websocket = websocket
                    self._connected = True
                    self._reconnect_delay = self.config.reconnect_delay  # Reset on success

                    logger.info(f"WebSocket connected for {self.phone_number}")

                    await self._receive_loop(websocket)

            except asyncio.CancelledError:
                logger.debug(f"WebSocket connection cancelled for {self.phone_number}")
                break
            except ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed for {self.phone_number}: {e.code} {e.reason}")
            except WebSocketException as e:
                logger.warning(f"WebSocket error for {self.phone_number}: {e}")
            except Exception as e:
                logger.error(f"Unexpected WebSocket error for {self.phone_number}: {e}")
            finally:
                self._websocket = None
                self._connected = False

            if self._running:
                logger.info(f"WebSocket reconnecting in {self._reconnect_delay:.1f}s for {self.phone_number}...")
                await asyncio.sleep(self._reconnect_delay)

                # Exponential backoff
                self._reconnect_delay = min(
                    self._reconnect_delay * 2,
                    self.config.max_reconnect_delay
                )

    async def _receive_loop(self, websocket):
        """Process incoming WebSocket messages."""
        async for message in websocket:
            if not self._running:
                break

            try:
                # Parse the JSON message
                data = json.loads(message)

                # The WebSocket delivers messages in the same envelope format as REST API
                # Call the message callback to process it
                await self.message_callback(data)

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse WebSocket message: {e}")
                logger.debug(f"Raw message: {message[:200]}...")
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")


async def probe_websocket(port: int, phone: str, timeout: float = 5.0) -> bool:
    """
    Probe if WebSocket endpoint is available on a Signal API container.

    Args:
        port: Signal API port
        phone: Phone number to test with
        timeout: Connection timeout in seconds

    Returns:
        True if WebSocket endpoint is available, False otherwise
    """
    ws_url = f"ws://localhost:{port}/v1/receive/{phone}"

    try:
        async with asyncio.timeout(timeout):
            async with websockets.connect(ws_url) as ws:
                # Connection successful - close immediately
                await ws.close()
                logger.info(f"WebSocket probe succeeded on port {port}")
                return True
    except asyncio.TimeoutError:
        logger.debug(f"WebSocket probe timed out on port {port}")
        return False
    except Exception as e:
        logger.debug(f"WebSocket probe failed on port {port}: {e}")
        return False
