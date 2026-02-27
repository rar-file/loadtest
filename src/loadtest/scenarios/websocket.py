"""WebSocket scenario for load testing.

This module provides WebSocketScenario for testing WebSocket
connections with support for text/binary frames and bidirectional
communication patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from loadtest.protocols import ProtocolConfig, ProtocolType
from loadtest.protocols.websocket import (
    WebSocketConnection,
    WebSocketFrameType,
    WebSocketMessage,
    WebSocketProtocol,
    WebSocketResponse,
)
from loadtest.scenarios.base import Scenario

if TYPE_CHECKING:
    pass


@dataclass
class WebSocketScenarioResult:
    """Result from a WebSocket scenario execution.
    
    Attributes:
        success: Whether the scenario succeeded.
        messages_sent: Number of messages sent.
        messages_received: Number of messages received.
        bytes_sent: Total bytes sent.
        bytes_received: Total bytes received.
        connection_duration: Duration of connection.
        response_time: Total execution time.
        errors: List of error messages.
    """
    
    success: bool = True
    messages_sent: int = 0
    messages_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    connection_duration: float = 0.0
    response_time: float = 0.0
    errors: list[str] = field(default_factory=list)


class WebSocketScenario(Scenario):
    """Scenario for testing WebSocket connections.
    
    This scenario supports various WebSocket testing patterns including
    send/receive, request/response, and subscription models.
    
    Attributes:
        url: WebSocket URL.
        messages: List of messages to send.
        message_factory: Callable for dynamic message generation.
        frame_type: Frame type (text or binary).
        expect_response: Whether to wait for responses.
        response_timeout: Timeout for responses.
        connection_duration: How long to maintain connection.
        subprotocols: WebSocket subprotocols to request.
    
    Example:
        >>> scenario = WebSocketScenario(
        ...     name="WebSocket Test",
        ...     url="wss://ws.example.com/socket",
        ...     messages=["Hello", "World"],
        ...     expect_response=True,
        ... )
    """
    
    def __init__(
        self,
        name: str | None = None,
        url: str = "",
        messages: list[str | bytes] | None = None,
        message_factory: Callable[[], str | bytes] | None = None,
        frame_type: str = "text",
        expect_response: bool = True,
        response_timeout: float = 10.0,
        connection_duration: float = 0.0,
        subprotocols: list[str] | None = None,
        max_messages: int = 100,
    ) -> None:
        """Initialize WebSocket scenario.
        
        Args:
            name: Scenario name.
            url: WebSocket URL.
            messages: Static messages to send.
            message_factory: Callable for dynamic messages.
            frame_type: 'text' or 'binary'.
            expect_response: Wait for responses.
            response_timeout: Response timeout.
            connection_duration: Time to keep connection open.
            subprotocols: Subprotocols to negotiate.
            max_messages: Maximum messages to receive.
        """
        super().__init__(name or f"WebSocket {url}")
        self.url = url
        self.messages = messages or []
        self.message_factory = message_factory
        self.frame_type = WebSocketFrameType(frame_type)
        self.expect_response = expect_response
        self.response_timeout = response_timeout
        self.connection_duration = connection_duration
        self.subprotocols = subprotocols or []
        self.max_messages = max_messages
        self._protocol: WebSocketProtocol | None = None
    
    def _get_protocol(self) -> WebSocketProtocol:
        """Get or create WebSocket protocol handler.
        
        Returns:
            WebSocket protocol instance.
        """
        if self._protocol is None:
            config = ProtocolConfig(
                protocol=ProtocolType.WEBSOCKET,
                endpoint=self.url,
                custom_headers={
                    "Sec-WebSocket-Protocol": ", ".join(self.subprotocols),
                } if self.subprotocols else {},
            )
            self._protocol = WebSocketProtocol(config)
        return self._protocol
    
    def _get_messages(self) -> list[str | bytes]:
        """Get messages to send.
        
        Returns:
            List of messages.
        """
        if self.message_factory:
            return [self.message_factory()]
        return self.messages
    
    async def execute(self, context: dict[str, Any]) -> WebSocketScenarioResult:
        """Execute the WebSocket scenario.
        
        Args:
            context: Execution context.
        
        Returns:
            Scenario result.
        """
        import asyncio
        import time
        
        start_time = time.time()
        result = WebSocketScenarioResult()
        protocol = self._get_protocol()
        
        try:
            # Create connection
            connection = await protocol.create_connection()
            
            messages = self._get_messages()
            
            for message in messages:
                # Send message
                request_data = {
                    "action": "send",
                    "data": message,
                    "frame_type": self.frame_type.value,
                    "expect_response": self.expect_response,
                    "response_timeout": self.response_timeout,
                }
                
                response = await protocol.execute_request(connection, request_data)
                
                if response.get("success"):
                    result.messages_sent += 1
                    result.bytes_sent += response.get("bytes_sent", 0)
                    
                    # Count received messages
                    msgs = response.get("messages", [])
                    result.messages_received += len(msgs)
                    result.bytes_received += sum(m.get("size", 0) for m in msgs)
                else:
                    result.success = False
                    if response.get("error"):
                        result.errors.append(response["error"])
            
            # Keep connection open if duration specified
            if self.connection_duration > 0:
                await asyncio.sleep(self.connection_duration)
            
            # Get final connection stats
            result.connection_duration = connection.connected_duration
            
            # Close connection
            await connection.close()
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        result.response_time = time.time() - start_time
        return result
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._protocol:
            await self._protocol.close_all()
            self._protocol = None


class WebSocketPingScenario(Scenario):
    """Scenario for testing WebSocket latency via ping/pong.
    
    Sends WebSocket ping frames and measures round-trip times.
    
    Attributes:
        url: WebSocket URL.
        ping_count: Number of pings to send.
        ping_interval: Time between pings.
        timeout: Ping timeout.
    
    Example:
        >>> scenario = WebSocketPingScenario(
        ...     name="Latency Test",
        ...     url="wss://ws.example.com",
        ...     ping_count=10,
        ...     ping_interval=1.0,
        ... )
    """
    
    def __init__(
        self,
        name: str | None = None,
        url: str = "",
        ping_count: int = 10,
        ping_interval: float = 1.0,
        timeout: float = 10.0,
    ) -> None:
        """Initialize WebSocket ping scenario.
        
        Args:
            name: Scenario name.
            url: WebSocket URL.
            ping_count: Number of pings.
            ping_interval: Seconds between pings.
            timeout: Ping timeout.
        """
        super().__init__(name or f"WebSocket Ping {url}")
        self.url = url
        self.ping_count = ping_count
        self.ping_interval = ping_interval
        self.timeout = timeout
        self._protocol: WebSocketProtocol | None = None
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute ping scenario.
        
        Args:
            context: Execution context.
        
        Returns:
            Ping statistics.
        """
        import asyncio
        import time
        
        config = ProtocolConfig(
            protocol=ProtocolType.WEBSOCKET,
            endpoint=self.url,
        )
        self._protocol = WebSocketProtocol(config)
        
        latencies = []
        errors = 0
        
        try:
            connection = await self._protocol.create_connection()
            
            for _ in range(self.ping_count):
                try:
                    latency = await connection.ping(self.timeout)
                    latencies.append(latency)
                except Exception:
                    errors += 1
                
                if self.ping_interval > 0:
                    await asyncio.sleep(self.ping_interval)
            
            await connection.close()
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
        
        if not latencies:
            return {
                "success": False,
                "ping_count": self.ping_count,
                "successful": 0,
                "errors": errors,
            }
        
        return {
            "success": True,
            "ping_count": self.ping_count,
            "successful": len(latencies),
            "errors": errors,
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "avg_latency": sum(latencies) / len(latencies),
            "latencies": latencies,
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._protocol:
            await self._protocol.close_all()
            self._protocol = None


class WebSocketSubscriptionScenario(Scenario):
    """Scenario for testing WebSocket subscriptions.
    
    Connects to a WebSocket and subscribes to messages for a duration,
    useful for testing real-time data feeds.
    
    Attributes:
        url: WebSocket URL.
        subscribe_message: Initial subscription message.
        duration: Subscription duration.
        message_handler: Optional callback for messages.
    
    Example:
        >>> scenario = WebSocketSubscriptionScenario(
        ...     name="Feed Test",
        ...     url="wss://ws.example.com/feed",
        ...     subscribe_message='{"action": "subscribe"}',
        ...     duration=60.0,
        ... )
    """
    
    def __init__(
        self,
        name: str | None = None,
        url: str = "",
        subscribe_message: str | bytes = "",
        duration: float = 60.0,
        message_handler: Callable[[WebSocketMessage], None] | None = None,
    ) -> None:
        """Initialize WebSocket subscription scenario.
        
        Args:
            name: Scenario name.
            url: WebSocket URL.
            subscribe_message: Initial subscription message.
            duration: Subscription duration in seconds.
            message_handler: Optional message handler callback.
        """
        super().__init__(name or f"WebSocket Subscription {url}")
        self.url = url
        self.subscribe_message = subscribe_message
        self.duration = duration
        self.message_handler = message_handler
        self._protocol: WebSocketProtocol | None = None
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute subscription scenario.
        
        Args:
            context: Execution context.
        
        Returns:
            Subscription statistics.
        """
        import asyncio
        import time
        
        config = ProtocolConfig(
            protocol=ProtocolType.WEBSOCKET,
            endpoint=self.url,
        )
        self._protocol = WebSocketProtocol(config)
        
        messages_received = 0
        bytes_received = 0
        errors = []
        message_types: dict[str, int] = {}
        
        def default_handler(msg: WebSocketMessage) -> None:
            nonlocal messages_received, bytes_received
            messages_received += 1
            bytes_received += msg.size
            
            msg_type = msg.frame_type.value
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        handler = self.message_handler or default_handler
        
        try:
            connection = await self._protocol.create_connection()
            
            # Send subscription message if provided
            if self.subscribe_message:
                if isinstance(self.subscribe_message, str):
                    await connection.send_text(self.subscribe_message)
                else:
                    await connection.send_binary(self.subscribe_message)
            
            # Subscribe to messages for duration
            start = time.time()
            while time.time() - start < self.duration:
                message = await connection.receive_message(timeout=1.0)
                if message:
                    handler(message)
                await asyncio.sleep(0.01)
            
            await connection.close()
            
        except Exception as e:
            errors.append(str(e))
        
        return {
            "success": len(errors) == 0,
            "duration": self.duration,
            "messages_received": messages_received,
            "bytes_received": bytes_received,
            "message_types": message_types,
            "errors": errors,
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._protocol:
            await self._protocol.close_all()
            self._protocol = None
