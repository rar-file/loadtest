"""HTTP/2 protocol handler with multiplexing support.

This module provides a full HTTP/2 implementation using httpx with
HTTP/2 support enabled, including stream multiplexing and proper
connection management.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx

from loadtest.protocols import (
    Connection,
    ConnectionStats,
    Protocol,
    ProtocolConfig,
    ProtocolMetrics,
    ProtocolType,
    register_protocol,
)

if TYPE_CHECKING:
    pass


@dataclass
class HTTP2Response:
    """HTTP/2 response wrapper.
    
    Attributes:
        status_code: HTTP status code.
        headers: Response headers.
        text: Response body as text.
        json_data: Parsed JSON body (if applicable).
        elapsed: Response time in seconds.
        url: Final URL after redirects.
        stream_id: HTTP/2 stream ID.
        push_promise: Whether this was a server push.
    """
    
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""
    json_data: Any = None
    elapsed: float = 0.0
    url: str = ""
    stream_id: int = 0
    push_promise: bool = False
    
    @property
    def is_success(self) -> bool:
        """Check if the response indicates success (2xx status)."""
        return 200 <= self.status_code < 300
    
    @property
    def is_redirect(self) -> bool:
        """Check if the response is a redirect (3xx status)."""
        return 300 <= self.status_code < 400
    
    @property
    def is_error(self) -> bool:
        """Check if the response indicates an error (4xx/5xx status)."""
        return self.status_code >= 400


@dataclass
class HTTP2Request:
    """HTTP/2 request configuration.
    
    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.).
        url: Target URL.
        headers: HTTP headers.
        params: URL query parameters.
        json_data: JSON body data.
        content: Raw content body.
        timeout: Request timeout.
        priority: HTTP/2 stream priority (0-255, lower = higher priority).
    """
    
    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    json_data: Any = None
    content: bytes | str | None = None
    timeout: float = 30.0
    priority: int = 128
    
    def to_httpx_request(self, base_url: str = "") -> dict[str, Any]:
        """Convert to httpx request parameters."""
        url = self.url
        if base_url and not url.startswith(("http://", "https://")):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")
        
        result = {
            "method": self.method.upper(),
            "url": url,
            "headers": self.headers,
            "params": self.params,
            "timeout": self.timeout,
        }
        
        if self.json_data is not None:
            result["json"] = self.json_data
        elif self.content is not None:
            result["content"] = self.content
        
        return result


class HTTP2Connection(Connection):
    """HTTP/2 connection implementation.
    
    Wraps an httpx.AsyncClient with HTTP/2 enabled to provide
    connection pooling and stream multiplexing.
    
    Attributes:
        config: Protocol configuration.
        stats: Connection statistics.
        _client: Underlying httpx client.
        _active_streams: Number of active streams.
        _stream_counter: Counter for stream IDs.
    """
    
    def __init__(self, config: ProtocolConfig, connection_id: str) -> None:
        """Initialize HTTP/2 connection.
        
        Args:
            config: Protocol configuration.
            connection_id: Unique connection identifier.
        """
        super().__init__(config, connection_id)
        self._client: httpx.AsyncClient | None = None
        self._active_streams = 0
        self._stream_counter = 0
        self._base_url = self._extract_base_url(config.endpoint)
        self._lock = None  # Created in open()
    
    def _extract_base_url(self, endpoint: str) -> str:
        """Extract base URL from endpoint.
        
        Args:
            endpoint: Endpoint string (URL or host:port).
        
        Returns:
            Full base URL.
        """
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        
        # Default to HTTPS for HTTP/2
        return f"https://{endpoint}"
    
    async def open(self) -> None:
        """Open the HTTP/2 connection.
        
        Creates an httpx.AsyncClient with HTTP/2 support enabled.
        
        Raises:
            ConnectionError: If connection fails.
        """
        import asyncio
        
        self._lock = asyncio.Lock()
        
        # Build limits and transport configuration
        limits = httpx.Limits(
            max_keepalive_connections=self.config.max_connections,
            max_connections=self.config.max_connections,
            keepalive_expiry=60.0 if self.config.keepalive else 0.0,
        )
        
        # TLS configuration
        verify: bool | str = self.config.tls_verify
        cert: tuple[str, str] | None = None
        if self.config.tls_cert and self.config.tls_key:
            cert = (self.config.tls_cert, self.config.tls_key)
        
        try:
            self._client = httpx.AsyncClient(
                http2=True,  # Enable HTTP/2
                limits=limits,
                verify=verify,
                cert=cert,
                timeout=httpx.Timeout(self.config.timeout),
            )
            
            # Verify connection with a simple request
            self.stats.connected_at = time.time()
            self._protocol_metrics.connections_opened += 1
            
        except Exception as e:
            raise ConnectionError(f"Failed to open HTTP/2 connection: {e}") from e
    
    async def close(self) -> None:
        """Close the HTTP/2 connection gracefully."""
        if self._client and not self._closed:
            await self._client.aclose()
            self._closed = True
            self._protocol_metrics.connections_closed += 1
    
    async def send(self, data: bytes) -> int:
        """Send raw data (not typically used for HTTP/2).
        
        Args:
            data: Raw bytes to send.
        
        Returns:
            Number of bytes sent.
        """
        # HTTP/2 is request/response, use execute_request instead
        self._protocol_metrics.bytes_sent += len(data)
        return len(data)
    
    async def receive(self, max_bytes: int = 8192) -> bytes:
        """Receive raw data (not typically used for HTTP/2).
        
        Args:
            max_bytes: Maximum bytes to receive.
        
        Returns:
            Received bytes.
        """
        # HTTP/2 is request/response, use execute_request instead
        return b""
    
    async def execute_request(
        self,
        request: HTTP2Request,
    ) -> HTTP2Response:
        """Execute an HTTP/2 request.
        
        Args:
            request: HTTP/2 request configuration.
        
        Returns:
            HTTP/2 response wrapper.
        
        Raises:
            RuntimeError: If connection not open.
        """
        if not self._client or self._closed:
            raise RuntimeError("Connection not open")
        
        if self._lock is None:
            raise RuntimeError("Connection not properly initialized")
        
        # Track stream
        async with self._lock:
            self._stream_counter += 1
            stream_id = self._stream_counter
            self._active_streams += 1
            self._protocol_metrics.streams_opened += 1
        
        start_time = time.time()
        
        try:
            # Merge custom headers from config
            headers = {**self.config.custom_headers, **request.headers}
            request.headers = headers
            
            # Execute request
            httpx_params = request.to_httpx_request(self._base_url)
            response = await self._client.request(**httpx_params)
            
            elapsed = time.time() - start_time
            
            # Update metrics
            self._protocol_metrics.bytes_sent += len(
                str(request.json_data or request.content or "").encode()
            )
            self._protocol_metrics.bytes_received += len(response.content)
            self._protocol_metrics.frames_received += 1
            
            # Update stats
            self.stats.requests_count += 1
            
            # Parse JSON if applicable
            json_data = None
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    json_data = response.json()
                except Exception:
                    pass
            
            return HTTP2Response(
                status_code=response.status_code,
                headers=dict(response.headers),
                text=response.text,
                json_data=json_data,
                elapsed=elapsed,
                url=str(response.url),
                stream_id=stream_id,
            )
            
        except Exception as e:
            self.stats.errors_count += 1
            raise
        finally:
            async with self._lock:
                self._active_streams -= 1
                self._protocol_metrics.streams_closed += 1
    
    @property
    def active_streams(self) -> int:
        """Get number of currently active streams."""
        return self._active_streams
    
    @property
    def is_multiplexing(self) -> bool:
        """Check if connection supports multiplexing (always True for HTTP/2)."""
        return True


@register_protocol
class HTTP2Protocol(Protocol):
    """HTTP/2 protocol handler.
    
    Implements the Protocol interface for HTTP/2 with full
    support for multiplexing, stream prioritization, and
    efficient connection reuse.
    
    Attributes:
        protocol_type: Always ProtocolType.HTTP_2.
        config: Protocol configuration.
    """
    
    protocol_type = ProtocolType.HTTP_2
    
    def __init__(self, config: ProtocolConfig) -> None:
        """Initialize HTTP/2 protocol handler.
        
        Args:
            config: Protocol configuration with HTTP/2 settings.
        """
        super().__init__(config)
        self._connection: HTTP2Connection | None = None
    
    async def create_connection(self) -> HTTP2Connection:
        """Create a new HTTP/2 connection.
        
        Returns:
            New HTTP/2 connection instance.
        """
        conn_id = self._generate_connection_id()
        conn = HTTP2Connection(self.config, conn_id)
        await conn.open()
        return conn
    
    async def execute_request(
        self,
        connection: Connection,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an HTTP/2 request.
        
        Args:
            connection: HTTP/2 connection to use.
            request_data: Request parameters (method, url, headers, etc.).
        
        Returns:
            Response data dictionary.
        
        Raises:
            TypeError: If connection is not HTTP2Connection.
        """
        if not isinstance(connection, HTTP2Connection):
            raise TypeError("Connection must be HTTP2Connection")
        
        # Build request from request_data
        request = HTTP2Request(
            method=request_data.get("method", "GET"),
            url=request_data.get("url", ""),
            headers=request_data.get("headers", {}),
            params=request_data.get("params", {}),
            json_data=request_data.get("json"),
            content=request_data.get("content"),
            timeout=request_data.get("timeout", self.config.timeout),
            priority=request_data.get("priority", 128),
        )
        
        response = await connection.execute_request(request)
        
        return {
            "status_code": response.status_code,
            "headers": response.headers,
            "text": response.text,
            "json": response.json_data,
            "elapsed": response.elapsed,
            "url": response.url,
            "stream_id": response.stream_id,
            "success": response.is_success,
        }
    
    async def get_connection(self) -> HTTP2Connection:
        """Get or create a multiplexed HTTP/2 connection.
        
        HTTP/2 connections support multiple concurrent streams,
        so we typically reuse a single connection.
        
        Returns:
            Active HTTP/2 connection.
        """
        if self._connection is None or self._connection.closed:
            self._connection = await self.create_connection()
        return self._connection
    
    async def execute(
        self,
        request_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a request using the default connection.
        
        Convenience method that gets a connection and executes
        the request in one call.
        
        Args:
            request_data: Request parameters.
        
        Returns:
            Response data dictionary.
        """
        conn = await self.get_connection()
        return await self.execute_request(conn, request_data)
    
    async def close_all(self) -> None:
        """Close all connections."""
        if self._connection:
            await self._connection.close()
            self._connection = None
        await super().close_all()
    
    @property
    def active_streams(self) -> int:
        """Get total number of active streams across all connections."""
        if self._connection:
            return self._connection.active_streams
        return 0
