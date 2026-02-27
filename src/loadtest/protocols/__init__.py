"""Protocol abstraction layer for load testing.

This module provides the foundation for supporting multiple protocols
in a unified way. All protocol handlers must implement the Protocol
interface.

Example:
    >>> from loadtest.protocols import Protocol, ProtocolConfig
    >>> class MyProtocol(Protocol):
    ...     async def connect(self, endpoint: str) -> Connection:
    ...         # Implementation
    ...         pass
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Protocol as TypingProtocol

if TYPE_CHECKING:
    from loadtest.metrics.collector import MetricsCollector


class ProtocolType(Enum):
    """Enumeration of supported protocol types."""
    
    HTTP_1 = auto()
    HTTP_2 = auto()
    HTTP_3 = auto()
    WEBSOCKET = auto()
    GRPC = auto()
    GRAPHQL = auto()
    TCP = auto()
    UDP = auto()
    SSE = auto()
    
    def __str__(self) -> str:
        """Return human-readable protocol name."""
        names = {
            ProtocolType.HTTP_1: "HTTP/1.1",
            ProtocolType.HTTP_2: "HTTP/2",
            ProtocolType.HTTP_3: "HTTP/3",
            ProtocolType.WEBSOCKET: "WebSocket",
            ProtocolType.GRPC: "gRPC",
            ProtocolType.GRAPHQL: "GraphQL",
            ProtocolType.TCP: "TCP",
            ProtocolType.UDP: "UDP",
            ProtocolType.SSE: "SSE",
        }
        return names.get(self, self.name)


@dataclass(frozen=True)
class ProtocolConfig:
    """Configuration for protocol connections.
    
    Attributes:
        protocol: The protocol type to use.
        endpoint: Target endpoint (URL, host:port, etc.).
        timeout: Connection timeout in seconds.
        keepalive: Whether to use connection keepalive.
        max_connections: Maximum number of concurrent connections.
        tls_verify: Whether to verify TLS certificates.
        tls_cert: Path to client certificate.
        tls_key: Path to client private key.
        custom_headers: Protocol-specific headers/options.
    """
    
    protocol: ProtocolType
    endpoint: str
    timeout: float = 30.0
    keepalive: bool = True
    max_connections: int = 100
    tls_verify: bool = True
    tls_cert: str | None = None
    tls_key: str | None = None
    custom_headers: dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "protocol": str(self.protocol),
            "endpoint": self.endpoint,
            "timeout": self.timeout,
            "keepalive": self.keepalive,
            "max_connections": self.max_connections,
            "tls_verify": self.tls_verify,
            "tls_cert": self.tls_cert,
            "tls_key": self.tls_key,
            "custom_headers": self.custom_headers,
        }


@dataclass
class ProtocolMetrics:
    """Metrics specific to protocol operations.
    
    Attributes:
        bytes_sent: Total bytes sent.
        bytes_received: Total bytes received.
        connections_opened: Number of connections opened.
        connections_closed: Number of connections closed.
        streams_opened: Number of streams opened (HTTP/2, etc.).
        streams_closed: Number of streams closed.
        frames_sent: Number of protocol frames sent.
        frames_received: Number of protocol frames received.
    """
    
    bytes_sent: int = 0
    bytes_received: int = 0
    connections_opened: int = 0
    connections_closed: int = 0
    streams_opened: int = 0
    streams_closed: int = 0
    frames_sent: int = 0
    frames_received: int = 0
    
    def merge(self, other: ProtocolMetrics) -> ProtocolMetrics:
        """Merge another metrics instance into this one."""
        return ProtocolMetrics(
            bytes_sent=self.bytes_sent + other.bytes_sent,
            bytes_received=self.bytes_received + other.bytes_received,
            connections_opened=self.connections_opened + other.connections_opened,
            connections_closed=self.connections_closed + other.connections_closed,
            streams_opened=self.streams_opened + other.streams_opened,
            streams_closed=self.streams_closed + other.streams_closed,
            frames_sent=self.frames_sent + other.frames_sent,
            frames_received=self.frames_received + other.frames_received,
        )


@dataclass
class ConnectionStats:
    """Statistics for a single connection.
    
    Attributes:
        connection_id: Unique identifier for the connection.
        protocol: Protocol type.
        connected_at: Timestamp when connection was established.
        requests_count: Number of requests made on this connection.
        errors_count: Number of errors on this connection.
        bytes_sent: Total bytes sent on this connection.
        bytes_received: Total bytes received.
    """
    
    connection_id: str
    protocol: ProtocolType
    connected_at: float = 0.0
    requests_count: int = 0
    errors_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    @property
    def duration(self) -> float:
        """Calculate connection duration."""
        import time
        return time.time() - self.connected_at


class Connection(ABC):
    """Abstract base class for protocol connections.
    
    A Connection represents a single active connection to an endpoint
    using a specific protocol. It handles the low-level protocol details
    while presenting a unified interface to the scenario layer.
    
    Attributes:
        config: Protocol configuration.
        stats: Connection statistics.
        _closed: Whether the connection is closed.
    """
    
    def __init__(self, config: ProtocolConfig, connection_id: str) -> None:
        """Initialize the connection.
        
        Args:
            config: Protocol configuration.
            connection_id: Unique identifier for this connection.
        """
        self.config = config
        self.stats = ConnectionStats(
            connection_id=connection_id,
            protocol=config.protocol,
        )
        self._closed = False
        self._protocol_metrics = ProtocolMetrics()
    
    @abstractmethod
    async def open(self) -> None:
        """Open the connection to the endpoint.
        
        Raises:
            ConnectionError: If connection fails.
            TimeoutError: If connection times out.
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the connection gracefully."""
        pass
    
    @abstractmethod
    async def send(self, data: bytes) -> int:
        """Send data over the connection.
        
        Args:
            data: Raw bytes to send.
        
        Returns:
            Number of bytes sent.
        """
        pass
    
    @abstractmethod
    async def receive(self, max_bytes: int = 8192) -> bytes:
        """Receive data from the connection.
        
        Args:
            max_bytes: Maximum bytes to receive.
        
        Returns:
            Received bytes.
        """
        pass
    
    @property
    def closed(self) -> bool:
        """Check if connection is closed."""
        return self._closed
    
    @property
    def protocol_metrics(self) -> ProtocolMetrics:
        """Get protocol-specific metrics for this connection."""
        return self._protocol_metrics
    
    async def __aenter__(self) -> Connection:
        """Async context manager entry."""
        await self.open()
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()


class Protocol(ABC):
    """Abstract base class for protocol implementations.
    
    A Protocol implementation handles the details of a specific
    protocol (HTTP/2, WebSocket, gRPC, etc.) and manages connections
    to endpoints.
    
    Attributes:
        config: Protocol configuration.
        _connections: Pool of active connections.
    """
    
    protocol_type: ProtocolType
    
    def __init__(self, config: ProtocolConfig) -> None:
        """Initialize the protocol handler.
        
        Args:
            config: Protocol configuration.
        """
        self.config = config
        self._connections: dict[str, Connection] = {}
        self._connection_counter = 0
        self._metrics = ProtocolMetrics()
    
    @abstractmethod
    async def create_connection(self) -> Connection:
        """Create a new connection to the endpoint.
        
        Returns:
            New Connection instance.
        """
        pass
    
    @abstractmethod
    async def execute_request(
        self,
        connection: Connection,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a request over the given connection.
        
        Args:
            connection: Active connection to use.
            request_data: Protocol-specific request data.
        
        Returns:
            Response data dictionary.
        """
        pass
    
    async def get_connection(self) -> Connection:
        """Get a connection from the pool or create new.
        
        Returns:
            Active connection.
        """
        # Simple round-robin for now - could be smarter
        for conn in self._connections.values():
            if not conn.closed:
                return conn
        
        # Create new connection
        conn = await self.create_connection()
        self._connections[conn.stats.connection_id] = conn
        return conn
    
    async def close_all(self) -> None:
        """Close all connections in the pool."""
        for conn in list(self._connections.values()):
            await conn.close()
        self._connections.clear()
    
    def _generate_connection_id(self) -> str:
        """Generate a unique connection ID."""
        self._connection_counter += 1
        return f"{self.protocol_type.name}_{self._connection_counter}"
    
    @property
    def metrics(self) -> ProtocolMetrics:
        """Get aggregated metrics for this protocol."""
        total = self._metrics
        for conn in self._connections.values():
            total = total.merge(conn.protocol_metrics)
        return total


class ProtocolRegistry:
    """Registry for protocol implementations.
    
    This registry allows dynamic discovery and instantiation
    of protocol handlers at runtime.
    
    Example:
        >>> registry = ProtocolRegistry()
        >>> registry.register(HTTP2Protocol)
        >>> protocol = registry.create(ProtocolType.HTTP_2, config)
    """
    
    def __init__(self) -> None:
        """Initialize empty protocol registry."""
        self._protocols: dict[ProtocolType, type[Protocol]] = {}
    
    def register(self, protocol_class: type[Protocol]) -> None:
        """Register a protocol implementation.
        
        Args:
            protocol_class: Protocol class to register.
        
        Raises:
            ValueError: If protocol type already registered.
        """
        protocol_type = protocol_class.protocol_type
        if protocol_type in self._protocols:
            raise ValueError(f"Protocol {protocol_type} already registered")
        self._protocols[protocol_type] = protocol_class
    
    def unregister(self, protocol_type: ProtocolType) -> None:
        """Unregister a protocol implementation.
        
        Args:
            protocol_type: Protocol type to unregister.
        """
        self._protocols.pop(protocol_type, None)
    
    def create(self, protocol_type: ProtocolType, config: ProtocolConfig) -> Protocol:
        """Create a protocol handler instance.
        
        Args:
            protocol_type: Type of protocol to create.
            config: Protocol configuration.
        
        Returns:
            Protocol handler instance.
        
        Raises:
            KeyError: If protocol type not registered.
        """
        if protocol_type not in self._protocols:
            raise KeyError(f"Protocol {protocol_type} not registered")
        return self._protocols[protocol_type](config)
    
    def list_protocols(self) -> list[ProtocolType]:
        """List all registered protocol types.
        
        Returns:
            List of registered protocol types.
        """
        return list(self._protocols.keys())
    
    def is_registered(self, protocol_type: ProtocolType) -> bool:
        """Check if a protocol type is registered.
        
        Args:
            protocol_type: Protocol type to check.
        
        Returns:
            True if registered, False otherwise.
        """
        return protocol_type in self._protocols


# Global protocol registry instance
default_registry = ProtocolRegistry()


def register_protocol(protocol_class: type[Protocol]) -> type[Protocol]:
    """Decorator to register a protocol class.
    
    Example:
        >>> @register_protocol
        ... class MyProtocol(Protocol):
        ...     protocol_type = ProtocolType.CUSTOM
        ...     pass
    """
    default_registry.register(protocol_class)
    return protocol_class
