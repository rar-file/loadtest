"""WebSocket protocol handler with binary and text frame support.

This module provides a full WebSocket implementation using websockets
library with support for text/binary frames, connection management,
and proper lifecycle handling.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

import websockets
from websockets.extensions.permessage_deflate import ClientPerMessageDeflateFactory

from loadtest.protocols import (
    Connection,
    Protocol,
    ProtocolConfig,
    ProtocolType,
    register_protocol,
)

if TYPE_CHECKING:
    pass


class WebSocketFrameType(Enum):
    """WebSocket frame types."""

    TEXT = "text"
    BINARY = "binary"
    CLOSE = "close"
    PING = "ping"
    PONG = "pong"


@dataclass
class WebSocketMessage:
    """WebSocket message wrapper.

    Attributes:
        frame_type: Type of WebSocket frame.
        data: Message data (str for text, bytes for binary).
        timestamp: When the message was received/sent.
        latency: Round-trip time if this is a response (seconds).
    """

    frame_type: WebSocketFrameType
    data: str | bytes
    timestamp: float = field(default_factory=time.time)
    latency: float = 0.0

    @property
    def is_text(self) -> bool:
        """Check if message is text."""
        return self.frame_type == WebSocketFrameType.TEXT and isinstance(self.data, str)

    @property
    def is_binary(self) -> bool:
        """Check if message is binary."""
        return self.frame_type == WebSocketFrameType.BINARY and isinstance(self.data, bytes)

    @property
    def size(self) -> int:
        """Get message size in bytes."""
        if isinstance(self.data, str):
            return len(self.data.encode("utf-8"))
        return len(self.data)


@dataclass
class WebSocketRequest:
    """WebSocket request/action configuration.

    Attributes:
        action: Action type (send, receive, ping, close).
        data: Data to send (for send action).
        frame_type: Frame type for send (text or binary).
        timeout: Timeout for the action.
        expect_response: Whether to wait for a response.
        response_timeout: Timeout for expected response.
    """

    action: str = "send"  # send, receive, ping, close
    data: str | bytes | None = None
    frame_type: WebSocketFrameType = WebSocketFrameType.TEXT
    timeout: float = 30.0
    expect_response: bool = False
    response_timeout: float = 10.0


@dataclass
class WebSocketResponse:
    """WebSocket response wrapper.

    Attributes:
        success: Whether the operation succeeded.
        messages: List of received messages.
        elapsed: Total elapsed time.
        connection_duration: Duration of WebSocket connection.
        frames_sent: Number of frames sent.
        frames_received: Number of frames received.
        bytes_sent: Total bytes sent.
        bytes_received: Total bytes received.
        close_code: Close code if connection closed.
        close_reason: Close reason if connection closed.
    """

    success: bool = True
    messages: list[WebSocketMessage] = field(default_factory=list)
    elapsed: float = 0.0
    connection_duration: float = 0.0
    frames_sent: int = 0
    frames_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    close_code: int | None = None
    close_reason: str | None = None
    error: str | None = None


class WebSocketConnection(Connection):
    """WebSocket connection implementation.

    Wraps a websockets connection with metrics tracking and
    proper lifecycle management.

    Attributes:
        config: Protocol configuration.
        stats: Connection statistics.
        _websocket: Underlying websockets connection.
        _message_queue: Queue for incoming messages.
        _receiver_task: Background receiver task.
        _connected_at: Connection timestamp.
    """

    def __init__(self, config: ProtocolConfig, connection_id: str) -> None:
        """Initialize WebSocket connection.

        Args:
            config: Protocol configuration.
            connection_id: Unique connection identifier.
        """
        super().__init__(config, connection_id)
        self._websocket: websockets.WebSocketClientProtocol | None = None
        self._message_queue: asyncio.Queue[WebSocketMessage] | None = None
        self._receiver_task: asyncio.Task | None = None
        self._connected_at: float = 0.0
        self._frames_sent = 0
        self._frames_received = 0
        self._close_code: int | None = None
        self._close_reason: str | None = None
        self._lock = None

    def _build_uri(self) -> str:
        """Build WebSocket URI from endpoint.

        Returns:
            WebSocket URI (ws:// or wss://).
        """
        endpoint = self.config.endpoint

        if endpoint.startswith(("ws://", "wss://")):
            return endpoint

        if endpoint.startswith(("http://", "https://")):
            return endpoint.replace("http://", "ws://").replace("https://", "wss://")

        # Default to secure WebSocket
        return f"wss://{endpoint}"

    async def open(self) -> None:
        """Open the WebSocket connection.

        Establishes the WebSocket connection and starts the
        background message receiver.

        Raises:
            ConnectionError: If connection fails.
        """
        import asyncio

        self._lock = asyncio.Lock()
        self._message_queue = asyncio.Queue()

        uri = self._build_uri()

        # Build connection options
        options: dict[str, Any] = {
            "ping_interval": 20 if self.config.keepalive else None,
            "ping_timeout": 10 if self.config.keepalive else None,
            "close_timeout": self.config.timeout,
        }

        # Add custom headers
        if self.config.custom_headers:
            options["extra_headers"] = self.config.custom_headers

        # Add compression support
        options["extensions"] = [ClientPerMessageDeflateFactory()]

        # TLS options
        if uri.startswith("wss://"):
            import ssl

            ssl_context = ssl.create_default_context()
            if not self.config.tls_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            options["ssl"] = ssl_context

        try:
            self._websocket = await websockets.connect(uri, **options)
            self._connected_at = time.time()
            self.stats.connected_at = self._connected_at
            self._protocol_metrics.connections_opened += 1

            # Start background receiver
            self._receiver_task = asyncio.create_task(self._receive_loop())

        except Exception as e:
            raise ConnectionError(f"Failed to open WebSocket connection: {e}") from e

    async def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self._closed:
            return

        # Cancel receiver task
        if self._receiver_task and not self._receiver_task.done():
            self._receiver_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receiver_task

        # Close websocket
        if self._websocket:
            try:
                await self._websocket.close()
                self._close_code = self._websocket.close_code
                self._close_reason = self._websocket.close_reason
            except Exception:
                pass
            finally:
                self._closed = True
                self._protocol_metrics.connections_closed += 1

    async def send(self, data: bytes) -> int:
        """Send raw binary data.

        Args:
            data: Raw bytes to send.

        Returns:
            Number of bytes sent.
        """
        if not self._websocket or self._closed:
            raise RuntimeError("Connection not open")

        await self._websocket.send(data)
        self._frames_sent += 1
        self._protocol_metrics.frames_sent += 1
        self._protocol_metrics.bytes_sent += len(data)
        return len(data)

    async def receive(self, max_bytes: int = 8192) -> bytes:
        """Receive raw data.

        Args:
            max_bytes: Maximum bytes to receive (ignored for WebSocket).

        Returns:
            Received bytes.
        """
        if not self._websocket or self._closed:
            raise RuntimeError("Connection not open")

        # Wait for a binary message
        while True:
            message = await self._websocket.recv()
            if isinstance(message, bytes):
                self._frames_received += 1
                self._protocol_metrics.frames_received += 1
                self._protocol_metrics.bytes_received += len(message)
                return message

    async def send_text(self, text: str) -> None:
        """Send text message.

        Args:
            text: Text to send.
        """
        if not self._websocket or self._closed:
            raise RuntimeError("Connection not open")

        await self._websocket.send(text)
        self._frames_sent += 1
        self._protocol_metrics.frames_sent += 1
        self._protocol_metrics.bytes_sent += len(text.encode("utf-8"))

    async def send_binary(self, data: bytes) -> None:
        """Send binary message.

        Args:
            data: Binary data to send.
        """
        if not self._websocket or self._closed:
            raise RuntimeError("Connection not open")

        await self._websocket.send(data)
        self._frames_sent += 1
        self._protocol_metrics.frames_sent += 1
        self._protocol_metrics.bytes_sent += len(data)

    async def receive_message(self, timeout: float | None = None) -> WebSocketMessage | None:
        """Receive a message from the queue.

        Args:
            timeout: Timeout in seconds.

        Returns:
            WebSocket message or None if timeout.
        """
        if not self._message_queue:
            return None

        try:
            return await asyncio.wait_for(
                self._message_queue.get(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return None

    async def ping(self, timeout: float = 10.0) -> float:
        """Send a ping and measure round-trip time.

        Args:
            timeout: Ping timeout.

        Returns:
            Round-trip time in seconds.
        """
        if not self._websocket or self._closed:
            raise RuntimeError("Connection not open")

        start = time.time()
        await asyncio.wait_for(self._websocket.ping(), timeout=timeout)
        return time.time() - start

    async def _receive_loop(self) -> None:
        """Background loop to receive messages."""
        if not self._websocket or not self._message_queue:
            return

        try:
            async for message in self._websocket:
                frame_type = (
                    WebSocketFrameType.TEXT
                    if isinstance(message, str)
                    else WebSocketFrameType.BINARY
                )

                ws_message = WebSocketMessage(
                    frame_type=frame_type,
                    data=message,
                )

                self._frames_received += 1
                self._protocol_metrics.frames_received += 1

                if isinstance(message, str):
                    self._protocol_metrics.bytes_received += len(message.encode("utf-8"))
                else:
                    self._protocol_metrics.bytes_received += len(message)

                await self._message_queue.put(ws_message)

        except asyncio.CancelledError:
            raise
        except Exception:
            # Connection likely closed
            pass

    @property
    def connected_duration(self) -> float:
        """Get duration of connection in seconds."""
        if self._connected_at == 0:
            return 0.0
        return time.time() - self._connected_at

    @property
    def close_code(self) -> int | None:
        """Get close code."""
        return self._close_code

    @property
    def close_reason(self) -> str | None:
        """Get close reason."""
        return self._close_reason

    @property
    def is_open(self) -> bool:
        """Check if connection is open."""
        if not self._websocket:
            return False
        return self._websocket.state == websockets.protocol.State.OPEN


@register_protocol
class WebSocketProtocol(Protocol):
    """WebSocket protocol handler.

    Implements the Protocol interface for WebSocket connections
    with support for text/binary frames and bidirectional
    communication.

    Attributes:
        protocol_type: Always ProtocolType.WEBSOCKET.
        config: Protocol configuration.
    """

    protocol_type = ProtocolType.WEBSOCKET

    def __init__(self, config: ProtocolConfig) -> None:
        """Initialize WebSocket protocol handler.

        Args:
            config: Protocol configuration.
        """
        super().__init__(config)

    async def create_connection(self) -> WebSocketConnection:
        """Create a new WebSocket connection.

        Returns:
            New WebSocket connection instance.
        """
        conn_id = self._generate_connection_id()
        conn = WebSocketConnection(self.config, conn_id)
        await conn.open()
        return conn

    async def execute_request(
        self,
        connection: Connection,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a WebSocket request/action.

        Args:
            connection: WebSocket connection to use.
            request_data: Request parameters.

        Returns:
            Response data dictionary.
        """
        if not isinstance(connection, WebSocketConnection):
            raise TypeError("Connection must be WebSocketConnection")

        action = request_data.get("action", "send")
        start_time = time.time()

        response = WebSocketResponse()

        try:
            if action == "send":
                data = request_data.get("data")
                frame_type_str = request_data.get("frame_type", "text")
                frame_type = WebSocketFrameType(frame_type_str)

                if frame_type == WebSocketFrameType.TEXT:
                    await connection.send_text(str(data))
                else:
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    await connection.send_binary(data)

                response.frames_sent = 1
                response.bytes_sent = len(str(data).encode("utf-8"))

                # Wait for response if expected
                if request_data.get("expect_response", False):
                    timeout = request_data.get("response_timeout", 10.0)
                    message = await connection.receive_message(timeout)
                    if message:
                        response.messages.append(message)
                        response.frames_received = 1
                        response.bytes_received = message.size

            elif action == "receive":
                timeout = request_data.get("timeout", 30.0)
                max_messages = request_data.get("max_messages", 1)

                for _ in range(max_messages):
                    message = await connection.receive_message(timeout)
                    if message:
                        response.messages.append(message)
                        response.frames_received += 1
                        response.bytes_received += message.size
                    else:
                        break

            elif action == "ping":
                timeout = request_data.get("timeout", 10.0)
                latency = await connection.ping(timeout)
                response.success = True
                response.messages.append(
                    WebSocketMessage(
                        frame_type=WebSocketFrameType.PONG,
                        data=f"RTT: {latency:.3f}s",
                    )
                )

            elif action == "close":
                await connection.close()
                response.close_code = connection.close_code
                response.close_reason = connection.close_reason

            response.elapsed = time.time() - start_time
            response.connection_duration = connection.connected_duration
            response.success = True

        except Exception as e:
            response.success = False
            response.error = str(e)

        return {
            "success": response.success,
            "messages": [
                {
                    "type": m.frame_type.value,
                    "data": m.data,
                    "size": m.size,
                    "latency": m.latency,
                }
                for m in response.messages
            ],
            "elapsed": response.elapsed,
            "connection_duration": response.connection_duration,
            "frames_sent": response.frames_sent,
            "frames_received": response.frames_received,
            "bytes_sent": response.bytes_sent,
            "bytes_received": response.bytes_received,
            "close_code": response.close_code,
            "close_reason": response.close_reason,
            "error": response.error,
        }

    async def send_and_receive(
        self,
        connection: WebSocketConnection,
        data: str | bytes,
        timeout: float = 10.0,
    ) -> WebSocketMessage | None:
        """Send data and wait for a response.

        Convenience method for request/response patterns over
        WebSocket.

        Args:
            connection: WebSocket connection.
            data: Data to send.
            timeout: Response timeout.

        Returns:
            Response message or None.
        """
        if isinstance(data, str):
            await connection.send_text(data)
        else:
            await connection.send_binary(data)

        return await connection.receive_message(timeout)

    async def subscribe(
        self,
        connection: WebSocketConnection,
        handler: Callable[[WebSocketMessage], None],
        duration: float = 60.0,
    ) -> None:
        """Subscribe to messages for a duration.

        Args:
            connection: WebSocket connection.
            handler: Callback for each message.
            duration: Subscription duration in seconds.
        """
        start = time.time()
        while time.time() - start < duration:
            message = await connection.receive_message(timeout=1.0)
            if message:
                handler(message)
            await asyncio.sleep(0.01)
