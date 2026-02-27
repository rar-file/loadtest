"""Tests for protocol abstraction layer."""

from __future__ import annotations

import pytest

from loadtest.protocols import (
    ConnectionStats,
    ProtocolConfig,
    ProtocolMetrics,
    ProtocolRegistry,
    ProtocolType,
    default_registry,
    register_protocol,
)
from loadtest.protocols.http2 import HTTP2Protocol, HTTP2Request, HTTP2Connection
from loadtest.protocols.websocket import (
    WebSocketProtocol,
    WebSocketRequest,
    WebSocketConnection,
    WebSocketFrameType,
)


class TestProtocolType:
    """Test protocol type enumeration."""
    
    def test_protocol_type_str(self) -> None:
        """Test protocol type string representation."""
        assert str(ProtocolType.HTTP_1) == "HTTP/1.1"
        assert str(ProtocolType.HTTP_2) == "HTTP/2"
        assert str(ProtocolType.HTTP_3) == "HTTP/3"
        assert str(ProtocolType.WEBSOCKET) == "WebSocket"
        assert str(ProtocolType.GRPC) == "gRPC"
        assert str(ProtocolType.GRAPHQL) == "GraphQL"
        assert str(ProtocolType.TCP) == "TCP"
        assert str(ProtocolType.UDP) == "UDP"
        assert str(ProtocolType.SSE) == "SSE"


class TestProtocolConfig:
    """Test protocol configuration."""
    
    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = ProtocolConfig(
            protocol=ProtocolType.HTTP_2,
            endpoint="https://example.com",
        )
        
        assert config.protocol == ProtocolType.HTTP_2
        assert config.endpoint == "https://example.com"
        assert config.timeout == 30.0
        assert config.keepalive is True
        assert config.max_connections == 100
        assert config.tls_verify is True
        assert config.tls_cert is None
        assert config.tls_key is None
        assert config.custom_headers == {}
    
    def test_config_to_dict(self) -> None:
        """Test config serialization."""
        config = ProtocolConfig(
            protocol=ProtocolType.WEBSOCKET,
            endpoint="wss://example.com",
            timeout=60.0,
            custom_headers={"X-Custom": "value"},
        )
        
        data = config.to_dict()
        assert data["protocol"] == "WebSocket"
        assert data["endpoint"] == "wss://example.com"
        assert data["timeout"] == 60.0
        assert data["custom_headers"] == {"X-Custom": "value"}


class TestProtocolMetrics:
    """Test protocol metrics."""
    
    def test_default_metrics(self) -> None:
        """Test default metric values."""
        metrics = ProtocolMetrics()
        
        assert metrics.bytes_sent == 0
        assert metrics.bytes_received == 0
        assert metrics.connections_opened == 0
        assert metrics.connections_closed == 0
        assert metrics.streams_opened == 0
        assert metrics.streams_closed == 0
        assert metrics.frames_sent == 0
        assert metrics.frames_received == 0
    
    def test_merge_metrics(self) -> None:
        """Test metrics merging."""
        m1 = ProtocolMetrics(
            bytes_sent=100,
            bytes_received=200,
            connections_opened=1,
        )
        m2 = ProtocolMetrics(
            bytes_sent=50,
            bytes_received=100,
            connections_opened=1,
            connections_closed=1,
        )
        
        merged = m1.merge(m2)
        
        assert merged.bytes_sent == 150
        assert merged.bytes_received == 300
        assert merged.connections_opened == 2
        assert merged.connections_closed == 1


class TestConnectionStats:
    """Test connection statistics."""
    
    def test_stats_creation(self) -> None:
        """Test stats creation."""
        stats = ConnectionStats(
            connection_id="conn_1",
            protocol=ProtocolType.HTTP_2,
        )
        
        assert stats.connection_id == "conn_1"
        assert stats.protocol == ProtocolType.HTTP_2
        assert stats.requests_count == 0
        assert stats.errors_count == 0


class TestProtocolRegistry:
    """Test protocol registry."""
    
    def test_register_protocol(self) -> None:
        """Test protocol registration."""
        registry = ProtocolRegistry()
        
        registry.register(HTTP2Protocol)
        
        assert registry.is_registered(ProtocolType.HTTP_2)
        assert ProtocolType.HTTP_2 in registry.list_protocols()
    
    def test_register_duplicate_raises(self) -> None:
        """Test registering duplicate protocol raises error."""
        registry = ProtocolRegistry()
        
        registry.register(HTTP2Protocol)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(HTTP2Protocol)
    
    def test_unregister_protocol(self) -> None:
        """Test protocol unregistration."""
        registry = ProtocolRegistry()
        
        registry.register(HTTP2Protocol)
        assert registry.is_registered(ProtocolType.HTTP_2)
        
        registry.unregister(ProtocolType.HTTP_2)
        assert not registry.is_registered(ProtocolType.HTTP_2)
    
    def test_create_protocol(self) -> None:
        """Test protocol creation."""
        registry = ProtocolRegistry()
        registry.register(HTTP2Protocol)
        
        config = ProtocolConfig(
            protocol=ProtocolType.HTTP_2,
            endpoint="https://example.com",
        )
        
        protocol = registry.create(ProtocolType.HTTP_2, config)
        
        assert isinstance(protocol, HTTP2Protocol)
        assert protocol.config == config
    
    def test_create_unregistered_raises(self) -> None:
        """Test creating unregistered protocol raises error."""
        registry = ProtocolRegistry()
        
        config = ProtocolConfig(
            protocol=ProtocolType.HTTP_2,
            endpoint="https://example.com",
        )
        
        with pytest.raises(KeyError, match="not registered"):
            registry.create(ProtocolType.HTTP_2, config)


class TestHTTP2Request:
    """Test HTTP/2 request building."""
    
    def test_default_request(self) -> None:
        """Test default request values."""
        request = HTTP2Request()
        
        assert request.method == "GET"
        assert request.url == ""
        assert request.headers == {}
        assert request.params == {}
        assert request.json_data is None
        assert request.content is None
        assert request.timeout == 30.0
        assert request.priority == 128
    
    def test_request_to_httpx(self) -> None:
        """Test converting request to httpx parameters."""
        request = HTTP2Request(
            method="POST",
            url="/api/users",
            headers={"Content-Type": "application/json"},
            json_data={"name": "test"},
            timeout=60.0,
        )
        
        params = request.to_httpx_request("https://example.com")
        
        assert params["method"] == "POST"
        assert params["url"] == "https://example.com/api/users"
        assert params["headers"] == {"Content-Type": "application/json"}
        assert params["json"] == {"name": "test"}
        assert params["timeout"] == 60.0


class TestWebSocketFrameType:
    """Test WebSocket frame types."""
    
    def test_frame_type_values(self) -> None:
        """Test frame type enumeration values."""
        assert WebSocketFrameType.TEXT.value == "text"
        assert WebSocketFrameType.BINARY.value == "binary"
        assert WebSocketFrameType.CLOSE.value == "close"
        assert WebSocketFrameType.PING.value == "ping"
        assert WebSocketFrameType.PONG.value == "pong"


class TestWebSocketRequest:
    """Test WebSocket request building."""
    
    def test_default_request(self) -> None:
        """Test default request values."""
        request = WebSocketRequest()
        
        assert request.action == "send"
        assert request.data is None
        assert request.frame_type == WebSocketFrameType.TEXT
        assert request.timeout == 30.0
        assert request.expect_response is False
        assert request.response_timeout == 10.0


@pytest.mark.asyncio
class TestHTTP2Protocol:
    """Test HTTP/2 protocol handler."""
    
    async def test_protocol_type(self) -> None:
        """Test HTTP/2 protocol type."""
        config = ProtocolConfig(
            protocol=ProtocolType.HTTP_2,
            endpoint="https://example.com",
        )
        protocol = HTTP2Protocol(config)
        
        assert protocol.protocol_type == ProtocolType.HTTP_2
    
    async def test_create_connection_id(self) -> None:
        """Test connection ID generation."""
        config = ProtocolConfig(
            protocol=ProtocolType.HTTP_2,
            endpoint="https://example.com",
        )
        protocol = HTTP2Protocol(config)
        
        id1 = protocol._generate_connection_id()
        id2 = protocol._generate_connection_id()
        
        assert id1 != id2
        assert id1.startswith("HTTP_2_")
        assert id2.startswith("HTTP_2_")
    
    async def test_metrics_aggregation(self) -> None:
        """Test metrics aggregation."""
        config = ProtocolConfig(
            protocol=ProtocolType.HTTP_2,
            endpoint="https://example.com",
        )
        protocol = HTTP2Protocol(config)
        
        # Initial metrics
        metrics = protocol.metrics
        assert metrics.connections_opened == 0


@pytest.mark.asyncio
class TestWebSocketProtocol:
    """Test WebSocket protocol handler."""
    
    async def test_protocol_type(self) -> None:
        """Test WebSocket protocol type."""
        config = ProtocolConfig(
            protocol=ProtocolType.WEBSOCKET,
            endpoint="wss://example.com",
        )
        protocol = WebSocketProtocol(config)
        
        assert protocol.protocol_type == ProtocolType.WEBSOCKET
    
    async def test_build_uri_ws(self) -> None:
        """Test building ws:// URI."""
        config = ProtocolConfig(
            protocol=ProtocolType.WEBSOCKET,
            endpoint="ws://example.com/socket",
        )
        protocol = WebSocketProtocol(config)
        conn = WebSocketConnection(config, "test_1")
        
        uri = conn._build_uri()
        assert uri == "ws://example.com/socket"
    
    async def test_build_uri_https(self) -> None:
        """Test converting https:// to wss://."""
        config = ProtocolConfig(
            protocol=ProtocolType.WEBSOCKET,
            endpoint="https://example.com",
        )
        conn = WebSocketConnection(config, "test_1")
        
        uri = conn._build_uri()
        assert uri == "wss://example.com"


class TestRegisterProtocolDecorator:
    """Test protocol registration decorator."""
    
    def test_decorator_registers(self) -> None:
        """Test that decorator registers protocol."""
        # HTTP2Protocol is decorated, should be registered
        assert default_registry.is_registered(ProtocolType.HTTP_2)
        assert default_registry.is_registered(ProtocolType.WEBSOCKET)
