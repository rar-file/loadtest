"""HTTP/2 scenario for load testing.

This module provides HTTP2Scenario for making HTTP/2 requests with
support for multiplexing, stream prioritization, and modern HTTP features.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from loadtest.protocols import ProtocolConfig, ProtocolType
from loadtest.protocols.http2 import HTTP2Protocol, HTTP2Request, HTTP2Response
from loadtest.scenarios.base import Scenario

if TYPE_CHECKING:
    pass


@dataclass
class HTTP2ScenarioResult:
    """Result from an HTTP/2 scenario execution.
    
    Attributes:
        success: Whether the request succeeded.
        status_code: HTTP status code.
        response_time: Total response time in seconds.
        bytes_sent: Bytes sent.
        bytes_received: Bytes received.
        stream_id: HTTP/2 stream ID.
        error: Error message if failed.
    """
    
    success: bool
    status_code: int = 0
    response_time: float = 0.0
    bytes_sent: int = 0
    bytes_received: int = 0
    stream_id: int = 0
    error: str | None = None


class HTTP2Scenario(Scenario):
    """Scenario for making HTTP/2 requests.
    
    This scenario leverages HTTP/2 features like multiplexing and
    header compression for efficient load testing of HTTP/2 endpoints.
    
    Attributes:
        method: HTTP method.
        url: Target URL.
        headers: HTTP headers.
        params: Query parameters.
        data: Static request body.
        data_factory: Callable for dynamic data.
        priority: HTTP/2 stream priority (0-255).
        timeout: Request timeout.
    
    Example:
        >>> scenario = HTTP2Scenario(
        ...     name="API Test",
        ...     method="POST",
        ...     url="https://api.example.com/users",
        ...     data_factory=lambda: {"name": "test"},
        ...     priority=128,
        ... )
    """
    
    def __init__(
        self,
        name: str | None = None,
        method: str = "GET",
        url: str = "",
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        data: dict[str, Any] | str | None = None,
        data_factory: Callable[[], dict[str, Any] | str] | None = None,
        priority: int = 128,
        timeout: float = 30.0,
        max_connections: int = 10,
        tls_verify: bool = True,
    ) -> None:
        """Initialize HTTP/2 scenario.
        
        Args:
            name: Scenario name.
            method: HTTP method.
            url: Target URL.
            headers: HTTP headers.
            params: Query parameters.
            data: Static request body.
            data_factory: Callable for dynamic data.
            priority: Stream priority (0-255, lower=higher priority).
            timeout: Request timeout.
            max_connections: Maximum concurrent connections.
            tls_verify: Verify TLS certificates.
        """
        super().__init__(name or f"HTTP/2 {method} {url}")
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.params = params or {}
        self.data = data
        self.data_factory = data_factory
        self.priority = priority
        self.timeout = timeout
        self.max_connections = max_connections
        self.tls_verify = tls_verify
        self._protocol: HTTP2Protocol | None = None
    
    def _get_protocol(self, endpoint: str) -> HTTP2Protocol:
        """Get or create HTTP/2 protocol handler.
        
        Args:
            endpoint: Target endpoint.
        
        Returns:
            HTTP/2 protocol instance.
        """
        if self._protocol is None:
            config = ProtocolConfig(
                protocol=ProtocolType.HTTP_2,
                endpoint=endpoint,
                timeout=self.timeout,
                max_connections=self.max_connections,
                tls_verify=self.tls_verify,
                custom_headers=self.headers,
            )
            self._protocol = HTTP2Protocol(config)
        return self._protocol
    
    def _prepare_data(self) -> dict[str, Any] | str | None:
        """Prepare request data.
        
        Returns:
            Request body data.
        """
        if self.data_factory:
            return self.data_factory()
        return self.data
    
    def _prepare_url(self) -> str:
        """Prepare URL with optional formatting.
        
        Returns:
            Final URL.
        """
        if "{" in self.url:
            return self.url.format(
                random_id=self.phoney.random_int(1, 10000),
                username=self.phoney.username(),
            )
        return self.url
    
    async def execute(self, context: dict[str, Any]) -> HTTP2ScenarioResult:
        """Execute the HTTP/2 request.
        
        Args:
            context: Execution context.
        
        Returns:
            Scenario result.
        """
        url = self._prepare_url()
        protocol = self._get_protocol(url)
        
        data = self._prepare_data()
        
        request_data = {
            "method": self.method,
            "url": url,
            "headers": self.headers,
            "params": self.params,
            "timeout": self.timeout,
            "priority": self.priority,
        }
        
        if isinstance(data, dict):
            request_data["json"] = data
        elif isinstance(data, str):
            request_data["content"] = data.encode("utf-8")
        
        try:
            response = await protocol.execute(request_data)
            
            return HTTP2ScenarioResult(
                success=response.get("success", False),
                status_code=response.get("status_code", 0),
                response_time=response.get("elapsed", 0.0),
                stream_id=response.get("stream_id", 0),
            )
            
        except Exception as e:
            return HTTP2ScenarioResult(
                success=False,
                error=str(e),
            )
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._protocol:
            await self._protocol.close_all()
            self._protocol = None


class HTTP2StreamScenario(Scenario):
    """Scenario for testing HTTP/2 multiplexing with multiple streams.
    
    This scenario creates multiple concurrent streams on a single
    HTTP/2 connection to test multiplexing capabilities.
    
    Attributes:
        streams: Number of concurrent streams.
        base_scenario: Base scenario to replicate across streams.
    
    Example:
        >>> base = HTTP2Scenario(name="Single", url="https://api.example.com")
        >>> scenario = HTTP2StreamScenario(
        ...     name="Multiplex Test",
        ...     streams=10,
        ...     base_scenario=base,
        ... )
    """
    
    def __init__(
        self,
        name: str | None = None,
        streams: int = 10,
        base_scenario: HTTP2Scenario | None = None,
        method: str = "GET",
        url: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize HTTP/2 stream scenario.
        
        Args:
            name: Scenario name.
            streams: Number of concurrent streams.
            base_scenario: Base scenario to use.
            method: HTTP method (if not using base_scenario).
            url: Target URL (if not using base_scenario).
            headers: HTTP headers (if not using base_scenario).
        """
        super().__init__(name or f"HTTP/2 {streams} Streams")
        self.streams = streams
        
        if base_scenario:
            self.base_scenario = base_scenario
        else:
            self.base_scenario = HTTP2Scenario(
                method=method,
                url=url,
                headers=headers,
            )
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute concurrent streams.
        
        Args:
            context: Execution context.
        
        Returns:
            Aggregate results.
        """
        import asyncio
        
        async def run_stream(stream_id: int) -> HTTP2ScenarioResult:
            result = await self.base_scenario.execute(context)
            return result
        
        # Launch all streams concurrently
        tasks = [run_stream(i) for i in range(self.streams)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        successful = sum(1 for r in results if isinstance(r, HTTP2ScenarioResult) and r.success)
        total_time = sum(
            r.response_time for r in results
            if isinstance(r, HTTP2ScenarioResult)
        )
        
        return {
            "streams": self.streams,
            "successful": successful,
            "failed": self.streams - successful,
            "total_response_time": total_time,
            "avg_response_time": total_time / self.streams if self.streams > 0 else 0,
        }
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.base_scenario.cleanup()
