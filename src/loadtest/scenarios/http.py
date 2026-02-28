"""HTTP request scenarios for load testing.

This module provides HTTPScenario for making HTTP requests using httpx
with support for Phoney-generated realistic data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from loadtest.scenarios.base import Scenario


@dataclass
class HTTPResponse:
    """Response wrapper for HTTP scenario results.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers.
        text: Response body as text.
        elapsed: Response time in seconds.
        url: Final URL after redirects.
    """

    status_code: int
    headers: dict[str, str]
    text: str
    elapsed: float
    url: str

    @property
    def is_success(self) -> bool:
        """Check if the response indicates success (2xx status)."""
        return 200 <= self.status_code < 300

    def json(self) -> Any:
        """Parse response body as JSON."""
        return json.loads(self.text)


class HTTPScenario(Scenario):
    """Scenario for making HTTP requests.

    This scenario supports GET, POST, PUT, DELETE, and other HTTP methods
    with configurable headers, query parameters, and request bodies.
    Request data can be static or generated dynamically using Phoney
    through the data_factory parameter.

    Attributes:
        method: HTTP method (GET, POST, PUT, DELETE, etc.).
        url: Target URL. Can include placeholders for formatting.
        headers: HTTP headers to include.
        params: URL query parameters.
        data: Static request body data.
        data_factory: Callable that returns dynamic request data.
        timeout: Request timeout in seconds.
        follow_redirects: Whether to follow HTTP redirects.

    Example:
        >>> scenario = HTTPScenario(
        ...     name="Create User",
        ...     method="POST",
        ...     url="https://api.example.com/users",
        ...     data_factory=lambda: {
        ...         "name": "John Doe",
        ...         "email": "john@example.com",
        ...     },
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
        timeout: float = 30.0,
        follow_redirects: bool = True,
    ) -> None:
        """Initialize an HTTP scenario.

        Args:
            name: Scenario name. Defaults to the URL.
            method: HTTP method.
            url: Target URL.
            headers: HTTP headers.
            params: Query parameters.
            data: Static request body.
            data_factory: Callable returning dynamic request data.
            timeout: Request timeout in seconds.
            follow_redirects: Whether to follow redirects.
        """
        super().__init__(name or f"{method} {url}")
        self.method = method.upper()
        self.url = url
        self.headers = headers or {}
        self.params = params or {}
        self.data = data
        self.data_factory = data_factory
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self._client: httpx.AsyncClient | None = None

    async def execute(self, context: dict[str, Any]) -> HTTPResponse:
        """Execute the HTTP request.

        Args:
            context: Execution context. May contain a 'client' key with
                    a shared httpx.AsyncClient instance.

        Returns:
            HTTPResponse containing the response details.

        Raises:
            httpx.HTTPError: If the request fails.
        """
        client = context.get("client") or self._get_client()

        # Prepare request data
        request_data = self._prepare_data()
        url = self._prepare_url()

        # Make the request
        response = await client.request(
            method=self.method,
            url=url,
            headers=self.headers,
            params=self.params,
            content=request_data if isinstance(request_data, str) else None,
            json=request_data if isinstance(request_data, dict) else None,
            timeout=self.timeout,
            follow_redirects=self.follow_redirects,
        )

        # Read response content first (required before accessing elapsed)
        text = response.text
        try:
            elapsed = response.elapsed.total_seconds()
        except RuntimeError:
            # Fallback for mocked responses where elapsed isn't available
            elapsed = 0.0

        return HTTPResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            text=text,
            elapsed=elapsed,
            url=str(response.url),
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create an HTTP client.

        Returns:
            AsyncClient instance for making requests.
        """
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    def _prepare_data(self) -> dict[str, Any] | str | None:
        """Prepare request data.

        Returns:
            Request body data, either from factory or static.
        """
        if self.data_factory:
            return self.data_factory()
        return self.data

    def _prepare_url(self) -> str:
        """Prepare the URL.

        Returns:
            URL with any Phoney-generated segments.
        """
        # Allow URL formatting with phoney data
        if "{" in self.url:
            import random

            return self.url.format(
                random_id=random.randint(1, 10000),
                username=self.phoney.username(),
            )
        return self.url

    async def cleanup(self) -> None:
        """Clean up resources (close HTTP client)."""
        if self._client:
            await self._client.aclose()
            self._client = None


class AuthenticatedHTTPScenario(HTTPScenario):
    """HTTP scenario with authentication support.

    Extends HTTPScenario with authentication handling, supporting
    Bearer tokens, API keys, and custom authentication methods.

    Attributes:
        auth_token: Static authentication token.
        token_factory: Callable returning dynamic tokens.
        auth_header: Header name for authentication.
        auth_prefix: Prefix for the token (e.g., "Bearer ").

    Example:
        >>> scenario = AuthenticatedHTTPScenario(
        ...     name="API Request",
        ...     method="GET",
        ...     url="https://api.example.com/data",
        ...     auth_token="static-token",
        ... )
        >>> # Or with dynamic tokens
        >>> scenario = AuthenticatedHTTPScenario(
        ...     name="API Request",
        ...     method="GET",
        ...     url="https://api.example.com/data",
        ...     token_factory=lambda: get_token_from_pool(),
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
        auth_token: str | None = None,
        token_factory: Callable[[], str] | None = None,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer ",
        timeout: float = 30.0,
        follow_redirects: bool = True,
    ) -> None:
        """Initialize an authenticated HTTP scenario.

        Args:
            name: Scenario name.
            method: HTTP method.
            url: Target URL.
            headers: HTTP headers.
            params: Query parameters.
            data: Static request body.
            data_factory: Callable for dynamic request data.
            auth_token: Static authentication token.
            token_factory: Callable for dynamic tokens.
            auth_header: Header name for authentication.
            auth_prefix: Prefix for the token.
            timeout: Request timeout.
            follow_redirects: Whether to follow redirects.
        """
        super().__init__(
            name=name,
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            data_factory=data_factory,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )
        self.auth_token = auth_token
        self.token_factory = token_factory
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix

    def _prepare_auth_header(self) -> dict[str, str]:
        """Prepare authentication header.

        Returns:
            Headers dictionary with authentication.
        """
        headers = self.headers.copy()

        token = self.auth_token
        if self.token_factory:
            token = self.token_factory()

        if token:
            headers[self.auth_header] = f"{self.auth_prefix}{token}"

        return headers

    async def execute(self, context: dict[str, Any]) -> HTTPResponse:
        """Execute the authenticated HTTP request.

        Args:
            context: Execution context.

        Returns:
            HTTPResponse with response details.
        """
        # Temporarily override headers with auth
        original_headers = self.headers
        self.headers = self._prepare_auth_header()

        try:
            return await super().execute(context)
        finally:
            self.headers = original_headers
