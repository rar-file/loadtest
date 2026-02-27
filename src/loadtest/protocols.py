"""Protocol abstraction layer for loadtest.

Supports multiple protocols: HTTP/1.1, HTTP/2, HTTP/3, WebSocket, gRPC, GraphQL
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncIterator
from dataclasses import dataclass
import asyncio


@dataclass
class Request:
    """Generic request object."""
    method: str
    url: str
    headers: Dict[str, str]
    body: Optional[bytes] = None
    metadata: Optional[Dict] = None


@dataclass  
class Response:
    """Generic response object."""
    status_code: int
    headers: Dict[str, str]
    body: bytes
    latency_ms: float
    metadata: Optional[Dict] = None


class ProtocolHandler(ABC):
    """Abstract base for protocol handlers."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._connected = False
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    async def request(self, req: Request) -> Response:
        """Execute a request."""
        pass
    
    @abstractmethod
    async def stream(self, req: Request) -> AsyncIterator[Response]:
        """Stream responses (for WebSocket, SSE, etc)."""
        pass
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()


class HTTPHandler(ProtocolHandler):
    """HTTP/1.1 and HTTP/2 handler using httpx."""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._client = None
        self._http2 = config.get('http2', True) if config else True
    
    async def connect(self) -> None:
        """Create HTTP client."""
        import httpx
        limits = httpx.Limits(
            max_connections=self.config.get('max_connections', 100),
            max_keepalive_connections=self.config.get('max_keepalive', 20)
        )
        timeout = httpx.Timeout(
            connect=self.config.get('connect_timeout', 5.0),
            read=self.config.get('read_timeout', 30.0)
        )
        self._client = httpx.AsyncClient(
            http2=self._http2,
            limits=limits,
            timeout=timeout,
            verify=self.config.get('verify_ssl', True)
        )
        self._connected = True
    
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False
    
    async def request(self, req: Request) -> Response:
        """Execute HTTP request."""
        import time
        start = time.time()
        
        response = await self._client.request(
            method=req.method,
            url=req.url,
            headers=req.headers,
            content=req.body
        )
        
        latency = (time.time() - start) * 1000
        
        return Response(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=response.content,
            latency_ms=latency,
            metadata={'http_version': response.http_version}
        )
    
    async def stream(self, req: Request) -> AsyncIterator[Response]:
        """Stream HTTP response."""
        import time
        start = time.time()
        
        async with self._client.stream(
            method=req.method,
            url=req.url,
            headers=req.headers,
            content=req.body
        ) as response:
            chunks = []
            async for chunk in response.aiter_bytes():
                chunks.append(chunk)
            
            latency = (time.time() - start) * 1000
            
            yield Response(
                status_code=response.status_code,
                headers=dict(response.headers),
                body=b''.join(chunks),
                latency_ms=latency
            )


class WebSocketHandler(ProtocolHandler):
    """WebSocket handler."""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._ws = None
    
    async def connect(self) -> None:
        """WebSocket connections are per-request."""
        self._connected = True
    
    async def disconnect(self) -> None:
        """Cleanup."""
        self._connected = False
    
    async def request(self, req: Request) -> Response:
        """Send WebSocket message and get response."""
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets package required: pip install websockets")
        
        import time
        start = time.time()
        
        async with websockets.connect(req.url, extra_headers=req.headers) as ws:
            if req.body:
                await ws.send(req.body.decode())
            
            response = await asyncio.wait_for(
                ws.recv(),
                timeout=self.config.get('ws_timeout', 30.0)
            )
            
            latency = (time.time() - start) * 1000
            
            return Response(
                status_code=101,  # Switching Protocols
                headers={},
                body=response.encode() if isinstance(response, str) else response,
                latency_ms=latency,
                metadata={'protocol': 'websocket'}
            )
    
    async def stream(self, req: Request) -> AsyncIterator[Response]:
        """Stream WebSocket messages."""
        try:
            import websockets
        except ImportError:
            raise ImportError("websockets package required")
        
        async with websockets.connect(req.url, extra_headers=req.headers) as ws:
            if req.body:
                await ws.send(req.body.decode())
            
            message_count = 0
            max_messages = self.config.get('ws_max_messages', 100)
            
            async for message in ws:
                message_count += 1
                yield Response(
                    status_code=101,
                    headers={},
                    body=message.encode() if isinstance(message, str) else message,
                    latency_ms=0,
                    metadata={'message_number': message_count}
                )
                
                if message_count >= max_messages:
                    break


class GraphQLHandler(HTTPHandler):
    """GraphQL handler (uses HTTP underneath)."""
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._endpoint = config.get('endpoint', '') if config else ''
    
    async def graphql_query(self, query: str, variables: Optional[Dict] = None) -> Response:
        """Execute GraphQL query."""
        import json
        
        body = {'query': query}
        if variables:
            body['variables'] = variables
        
        req = Request(
            method='POST',
            url=self._endpoint,
            headers={'Content-Type': 'application/json'},
            body=json.dumps(body).encode()
        )
        
        return await self.request(req)


def create_handler(protocol: str, config: Optional[Dict] = None) -> ProtocolHandler:
    """Factory function to create protocol handlers."""
    handlers = {
        'http': HTTPHandler,
        'http1': lambda c: HTTPHandler({**(c or {}), 'http2': False}),
        'http2': lambda c: HTTPHandler({**(c or {}), 'http2': True}),
        'websocket': WebSocketHandler,
        'ws': WebSocketHandler,
        'graphql': GraphQLHandler,
    }
    
    if protocol.lower() not in handlers:
        raise ValueError(f"Unknown protocol: {protocol}. Available: {list(handlers.keys())}")
    
    return handlers[protocol.lower()](config)
