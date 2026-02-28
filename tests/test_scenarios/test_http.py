"""Tests for HTTP scenarios."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from loadtest.scenarios.http import (
    AuthenticatedHTTPScenario,
    HTTPResponse,
    HTTPScenario,
)


class TestHTTPResponse:
    """Tests for HTTPResponse."""

    def test_is_success_2xx(self) -> None:
        """Test success detection for 2xx codes."""
        response = HTTPResponse(
            status_code=200,
            headers={},
            text='{"ok": true}',
            elapsed=0.1,
            url="http://example.com",
        )
        assert response.is_success is True

    def test_is_success_4xx(self) -> None:
        """Test success detection for 4xx codes."""
        response = HTTPResponse(
            status_code=404,
            headers={},
            text="Not Found",
            elapsed=0.1,
            url="http://example.com",
        )
        assert response.is_success is False

    def test_json_parsing(self) -> None:
        """Test JSON parsing."""
        response = HTTPResponse(
            status_code=200,
            headers={"Content-Type": "application/json"},
            text='{"key": "value", "number": 42}',
            elapsed=0.1,
            url="http://example.com",
        )
        data = response.json()
        assert data["key"] == "value"
        assert data["number"] == 42


class TestHTTPScenario:
    """Tests for HTTPScenario."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        scenario = HTTPScenario()
        assert scenario.method == "GET"
        assert scenario.url == ""
        assert scenario.timeout == 30.0
        assert scenario.follow_redirects is True

    def test_init_custom(self) -> None:
        """Test custom initialization."""
        scenario = HTTPScenario(
            name="Custom",
            method="POST",
            url="http://example.com/api",
            headers={"X-Custom": "value"},
            timeout=60.0,
            follow_redirects=False,
        )
        assert scenario.name == "Custom"
        assert scenario.method == "POST"
        assert scenario.url == "http://example.com/api"
        assert scenario.headers == {"X-Custom": "value"}
        assert scenario.timeout == 60.0
        assert scenario.follow_redirects is False

    def test_name_from_method_url(self) -> None:
        """Test that name defaults to method and URL."""
        scenario = HTTPScenario(method="GET", url="http://example.com")
        assert scenario.name == "GET http://example.com"

    @pytest.mark.asyncio
    async def test_execute_get_request(self) -> None:
        """Test executing a GET request."""
        scenario = HTTPScenario(
            method="GET",
            url="http://example.com",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"status": "ok"}'
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.url = "http://example.com"

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        context = {"client": mock_client}
        result = await scenario.execute(context)

        assert result.status_code == 200
        assert result.is_success is True
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_post_with_data(self) -> None:
        """Test executing a POST request with data."""
        scenario = HTTPScenario(
            method="POST",
            url="http://example.com/api",
            data_factory=lambda: {"key": "value"},
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.text = '{"id": 1}'
        mock_response.elapsed.total_seconds.return_value = 0.2
        mock_response.url = "http://example.com/api"

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        context = {"client": mock_client}
        result = await scenario.execute(context)

        assert result.status_code == 201
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args is not None
        assert call_args.kwargs.get("json") == {"key": "value"}

    @pytest.mark.asyncio
    async def test_execute_with_error(self) -> None:
        """Test executing a request that fails."""
        scenario = HTTPScenario(
            method="GET",
            url="http://example.com",
        )

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

        context = {"client": mock_client}

        with pytest.raises(httpx.ConnectError):
            await scenario.execute(context)

    def test_prepare_data_from_factory(self) -> None:
        """Test data preparation from factory."""
        scenario = HTTPScenario(
            data_factory=lambda: {"dynamic": "data"},
        )

        data = scenario._prepare_data()

        assert data == {"dynamic": "data"}

    def test_prepare_data_static(self) -> None:
        """Test data preparation from static data."""
        scenario = HTTPScenario(data={"static": "data"})

        data = scenario._prepare_data()

        assert data == {"static": "data"}

    def test_prepare_url_with_format(self) -> None:
        """Test URL preparation with placeholders."""
        scenario = HTTPScenario(url="http://example.com/users/{random_id}")

        url = scenario._prepare_url()

        assert "http://example.com/users/" in url
        assert "{random_id}" not in url

    @pytest.mark.asyncio
    async def test_cleanup(self) -> None:
        """Test cleanup closes client."""
        scenario = HTTPScenario()
        mock_client = AsyncMock()
        scenario._client = mock_client

        await scenario.cleanup()

        mock_client.aclose.assert_called_once()
        assert scenario._client is None


class TestAuthenticatedHTTPScenario:
    """Tests for AuthenticatedHTTPScenario."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        scenario = AuthenticatedHTTPScenario(auth_token="test-token")
        assert scenario.auth_token == "test-token"
        assert scenario.auth_header == "Authorization"
        assert scenario.auth_prefix == "Bearer "

    def test_init_custom(self) -> None:
        """Test custom initialization."""
        scenario = AuthenticatedHTTPScenario(
            auth_token="api-key",
            auth_header="X-API-Key",
            auth_prefix="",
        )
        assert scenario.auth_header == "X-API-Key"
        assert scenario.auth_prefix == ""

    def test_prepare_auth_header_static_token(self) -> None:
        """Test auth header preparation with static token."""
        scenario = AuthenticatedHTTPScenario(
            auth_token="static-token",
            headers={"X-Custom": "value"},
        )

        headers = scenario._prepare_auth_header()

        assert headers["Authorization"] == "Bearer static-token"
        assert headers["X-Custom"] == "value"

    def test_prepare_auth_header_factory(self) -> None:
        """Test auth header preparation with token factory."""
        counter = 0

        def token_factory() -> str:
            nonlocal counter
            counter += 1
            return f"dynamic-token-{counter}"

        scenario = AuthenticatedHTTPScenario(token_factory=token_factory)

        headers1 = scenario._prepare_auth_header()
        headers2 = scenario._prepare_auth_header()

        assert headers1["Authorization"] == "Bearer dynamic-token-1"
        assert headers2["Authorization"] == "Bearer dynamic-token-2"

    @pytest.mark.asyncio
    async def test_execute_preserves_original_headers(self) -> None:
        """Test that execute preserves original headers after call."""
        original_headers = {"X-Original": "value"}
        scenario = AuthenticatedHTTPScenario(
            auth_token="test",
            headers=original_headers.copy(),
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.url = "http://example.com"

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)

        context = {"client": mock_client}
        await scenario.execute(context)

        # Original headers should be restored
        assert scenario.headers == original_headers
        assert "Authorization" not in scenario.headers


class TestHTTPScenarioIntegration:
    """Integration-style tests for HTTPScenario."""

    @pytest.mark.asyncio
    async def test_scenario_with_real_httpx(self) -> None:
        """Test scenario with real httpx client (mocked transport)."""
        import time
        from httpx import Request, Response

        def mock_handler(request: Request) -> Response:
            # Create response with explicit elapsed time
            response = Response(200, json={"status": "ok"})
            return response

        transport = httpx.MockTransport(mock_handler)

        async with httpx.AsyncClient(transport=transport) as client:
            scenario = HTTPScenario(
                method="GET",
                url="http://test.example.com/api",
            )

            context = {"client": client}
            result = await scenario.execute(context)

            assert result.status_code == 200
            assert result.is_success is True
