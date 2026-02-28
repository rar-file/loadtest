"""OpenAPI auto-detection for loadtest.

Automatically discover and configure endpoints from OpenAPI/Swagger specs.
"""

from __future__ import annotations

import json
from typing import Any

import httpx


class OpenAPIDetector:
    """Detect and parse OpenAPI specifications.

    Example:
        >>> detector = OpenAPIDetector("https://api.example.com")
        >>> endpoints = detector.discover()
        >>> print(f"Found {len(endpoints)} endpoints")
    """

    # Common OpenAPI spec locations
    SPEC_PATHS = [
        "/openapi.json",
        "/api/openapi.json",
        "/swagger.json",
        "/api/swagger.json",
        "/v1/openapi.json",
        "/v2/swagger.json",
        "/openapi.yaml",
        "/swagger.yaml",
        "/api-docs",
        "/api/docs",
    ]

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        """Initialize detector.

        Args:
            base_url: Base URL of the API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.spec: dict[str, Any] | None = None
        self.spec_url: str | None = None

    async def detect(self) -> dict[str, Any] | None:
        """Try to find and fetch OpenAPI spec.

        Returns:
            OpenAPI specification dict or None if not found
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for path in self.SPEC_PATHS:
                url = f"{self.base_url}{path}"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "")

                        if "yaml" in content_type or path.endswith(".yaml"):
                            # Parse YAML
                            try:
                                import yaml

                                self.spec = yaml.safe_load(response.text)
                            except ImportError:
                                continue
                        else:
                            # Parse JSON
                            try:
                                self.spec = response.json()
                            except json.JSONDecodeError:
                                continue

                        self.spec_url = url
                        return self.spec

                except Exception:
                    continue

        return None

    def parse_endpoints(self) -> list[dict[str, Any]]:
        """Parse endpoints from discovered spec.

        Returns:
            List of endpoint configurations
        """
        if not self.spec:
            return []

        endpoints = []

        # OpenAPI 3.x and Swagger 2.0 both use 'paths'
        paths = self.spec.get("paths", {})
        base_path = self.spec.get("basePath", "")

        for path, methods in paths.items():
            # Skip parameters and other non-method keys
            for method, details in methods.items():
                if method.startswith("x-") or method == "parameters":
                    continue

                method = method.upper()

                # Extract useful info
                summary = details.get("summary", "")
                description = details.get("description", "")
                operation_id = details.get("operationId", "")
                tags = details.get("tags", [])

                # Build endpoint config
                endpoint = {
                    "method": method,
                    "path": base_path + path,
                    "full_path": path,
                    "summary": summary,
                    "description": description,
                    "operation_id": operation_id,
                    "tags": tags,
                }

                # Try to generate sample request body
                if method in ("POST", "PUT", "PATCH"):
                    body = self._generate_sample_body(details)
                    if body:
                        endpoint["sample_body"] = body

                # Extract parameters
                params = details.get("parameters", [])
                endpoint["parameters"] = [
                    {
                        "name": p.get("name"),
                        "in": p.get("in"),  # query, path, header, body
                        "required": p.get("required", False),
                        "type": p.get("type") or p.get("schema", {}).get("type", "string"),
                    }
                    for p in params
                ]

                endpoints.append(endpoint)

        return endpoints

    def _generate_sample_body(self, operation: dict[str, Any]) -> dict[str, Any] | None:
        """Generate a sample request body from schema.

        Args:
            operation: Operation details from spec

        Returns:
            Sample body dict or None
        """
        request_body = operation.get("requestBody", {})
        content = request_body.get("content", {})

        # Try JSON schema first
        json_content = content.get("application/json", {})
        schema = json_content.get("schema", {})

        if schema:
            return self._generate_sample_from_schema(schema)

        # Swagger 2.0 style
        for param in operation.get("parameters", []):
            if param.get("in") == "body":
                schema = param.get("schema", {})
                return self._generate_sample_from_schema(schema)

        return None

    def _generate_sample_from_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate sample data from JSON schema.

        Args:
            schema: JSON schema dict

        Returns:
            Sample data dict
        """
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            result = {}
            properties = schema.get("properties", {})
            required = schema.get("required", [])

            for prop_name, prop_schema in properties.items():
                if (
                    prop_name in required or len(properties) <= 5
                ):  # Include non-required if few props
                    result[prop_name] = self._get_sample_value(prop_schema, prop_name)

            return result

        elif schema_type == "array":
            items = schema.get("items", {})
            return [self._generate_sample_from_schema(items)]

        return {}

    def _get_sample_value(self, schema: dict[str, Any], name: str = "") -> Any:
        """Get a sample value for a schema property.

        Args:
            schema: Property schema
            name: Property name (for intelligent defaults)

        Returns:
            Sample value
        """
        prop_type = schema.get("type", "string")
        enum = schema.get("enum", [])

        if enum:
            return enum[0]

        if prop_type == "string":
            # Intelligent defaults based on name
            name_lower = name.lower()
            if "email" in name_lower:
                return "user@example.com"
            elif "name" in name_lower:
                if "first" in name_lower:
                    return "John"
                elif "last" in name_lower:
                    return "Doe"
                return "John Doe"
            elif "id" in name_lower or "uuid" in name_lower:
                return "550e8400-e29b-41d4-a716-446655440000"
            elif "date" in name_lower or "time" in name_lower:
                return "2024-01-01T00:00:00Z"
            elif "url" in name_lower or "link" in name_lower:
                return "https://example.com"
            elif "phone" in name_lower:
                return "+1-555-123-4567"
            elif "status" in name_lower or "state" in name_lower:
                return "active"
            elif "type" in name_lower:
                return "standard"
            elif "description" in name_lower or "text" in name_lower or "content" in name_lower:
                return f"Sample {name}"
            else:
                return f"sample_{name}"

        elif prop_type == "integer" or prop_type == "number":
            name_lower = name.lower()
            if "age" in name_lower:
                return 30
            elif "count" in name_lower or "quantity" in name_lower:
                return 1
            elif "price" in name_lower or "amount" in name_lower:
                return 99.99
            elif "id" in name_lower:
                return 12345
            else:
                return 42

        elif prop_type == "boolean":
            return True

        elif prop_type == "array":
            items = schema.get("items", {})
            return [self._get_sample_value(items, name)]

        elif prop_type == "object":
            return self._generate_sample_from_schema(schema)

        return None

    def generate_loadtest_config(self, max_endpoints: int = 10) -> dict[str, Any]:
        """Generate loadtest configuration from spec.

        Args:
            max_endpoints: Maximum number of endpoints to include

        Returns:
            Loadtest configuration dict
        """
        endpoints = self.parse_endpoints()

        # Sort by method (GETs first for safety) and limit
        priority_methods = ["GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"]
        endpoints.sort(
            key=lambda e: (
                priority_methods.index(e["method"]) if e["method"] in priority_methods else 99
            )
        )

        config_endpoints = []
        for ep in endpoints[:max_endpoints]:
            config_ep = {
                "method": ep["method"],
                "path": ep["path"],
                "weight": 1.0,
            }

            if ep.get("sample_body"):
                config_ep["json"] = ep["sample_body"]

            config_endpoints.append(config_ep)

        # Detect API title
        title = "API Load Test"
        if self.spec:
            info = self.spec.get("info", {})
            title = info.get("title", title)

        return {
            "target": self.base_url,
            "name": f"{title} Load Test",
            "pattern": "constant",
            "rps": 10,
            "duration": 60,
            "endpoints": config_endpoints,
        }


async def detect_endpoints(base_url: str, max_endpoints: int = 10) -> dict[str, Any]:
    """Auto-detect endpoints from OpenAPI spec.

    This is a convenience function for the simple API.

    Args:
        base_url: Base URL of the API
        max_endpoints: Maximum number of endpoints to include

    Returns:
        Loadtest configuration dict

    Example:
        >>> from loadtest import loadtest
        >>> from loadtest.openapi import detect_endpoints
        >>> config = await detect_endpoints("https://api.example.com")
        >>> test = loadtest(**config)
        >>> test.run()
    """
    detector = OpenAPIDetector(base_url)
    spec = await detector.detect()

    if spec:
        return detector.generate_loadtest_config(max_endpoints)

    # Return minimal config if no spec found
    return {
        "target": base_url,
        "pattern": "constant",
        "rps": 10,
        "duration": 60,
        "endpoints": [{"method": "GET", "path": "/", "weight": 1}],
    }


def detect_endpoints_sync(base_url: str, max_endpoints: int = 10) -> dict[str, Any]:
    """Synchronous version of detect_endpoints.

    Args:
        base_url: Base URL of the API
        max_endpoints: Maximum number of endpoints to include

    Returns:
        Loadtest configuration dict
    """
    import asyncio

    return asyncio.run(detect_endpoints(base_url, max_endpoints))
