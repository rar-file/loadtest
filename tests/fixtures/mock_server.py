"""Mock server for testing loadtest scenarios.

This module provides a simple HTTP server for testing purposes,
allowing tests to run without external dependencies.
"""

from __future__ import annotations

import asyncio
import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class MockRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock server."""
    
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Suppress log messages."""
        pass
    
    def _send_json_response(self, data: dict[str, Any], status: int = 200) -> None:
        """Send a JSON response.
        
        Args:
            data: Response data.
            status: HTTP status code.
        """
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        if self.path.startswith("/users"):
            # Simulate user list endpoint
            self._send_json_response({
                "users": [
                    {"id": i, "name": f"User {i}"}
                    for i in range(1, 11)
                ],
                "total": 100,
                "page": 1,
            })
        elif self.path.startswith("/delay"):
            # Simulate slow endpoint
            import time
            time.sleep(0.1)
            self._send_json_response({"status": "delayed"})
        elif self.path == "/error":
            # Simulate error endpoint
            self._send_json_response({"error": "Internal Server Error"}, status=500)
        else:
            self._send_json_response({"status": "ok", "path": self.path})
    
    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"raw": body.decode()}
        
        # Echo back the request
        self._send_json_response({
            "status": "created",
            "received": data,
            "path": self.path,
        }, status=201)
    
    def do_PUT(self) -> None:  # noqa: N802
        """Handle PUT requests."""
        self._send_json_response({"status": "updated"})
    
    def do_DELETE(self) -> None:  # noqa: N802
        """Handle DELETE requests."""
        self._send_json_response({"status": "deleted"})


class MockServer:
    """Simple mock HTTP server for testing.
    
    This server provides endpoints for testing various scenarios:
    - GET /users - Returns list of users
    - GET /delay - Returns after a delay
    - GET /error - Returns 500 error
    - POST / - Echoes request body
    
    Example:
        >>> server = MockServer(port=8080)
        >>> server.start()
        >>> # Run tests...
        >>> server.stop()
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        """Initialize the mock server.
        
        Args:
            host: Host address to bind to.
            port: Port to listen on (0 for random port).
        """
        self.host = host
        self.port = port
        self._server: HTTPServer | None = None
        self._thread: asyncio.Task | None = None
    
    def start(self) -> int:
        """Start the mock server.
        
        Returns:
            The port number the server is listening on.
        """
        self._server = HTTPServer((self.host, self.port), MockRequestHandler)
        
        if self.port == 0:
            self.port = self._server.server_address[1]
        
        import threading
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        
        return self.port
    
    def stop(self) -> None:
        """Stop the mock server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
    
    @property
    def url(self) -> str:
        """Get the server URL.
        
        Returns:
            Base URL for the server.
        """
        return f"http://{self.host}:{self.port}"
    
    def __enter__(self) -> "MockServer":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.stop()


class FlakyMockServer(MockServer):
    """Mock server that randomly returns errors.
    
    Useful for testing error handling and retry logic.
    
    Attributes:
        error_rate: Probability of returning an error (0-1).
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        error_rate: float = 0.1,
    ) -> None:
        """Initialize the flaky mock server.
        
        Args:
            host: Host address.
            port: Port number.
            error_rate: Probability of errors (0-1).
        """
        super().__init__(host, port)
        self.error_rate = error_rate
    
    def start(self) -> int:
        """Start the server with a flaky handler."""
        error_rate = self.error_rate
        
        class FlakyHandler(MockRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if random.random() < error_rate:
                    self._send_json_response({"error": "Random failure"}, status=503)
                else:
                    super().do_GET()
            
            def do_POST(self) -> None:  # noqa: N802
                if random.random() < error_rate:
                    self._send_json_response({"error": "Random failure"}, status=503)
                else:
                    super().do_POST()
        
        self._server = HTTPServer((self.host, self.port), FlakyHandler)
        
        if self.port == 0:
            self.port = self._server.server_address[1]
        
        import threading
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        
        return self.port
