"""Better error messages with helpful suggestions.

This module provides enhanced error handling with actionable suggestions
for common mistakes and issues.
"""

from __future__ import annotations

import re
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class LoadTestError(Exception):
    """Base exception with helpful suggestions."""

    def __init__(self, message: str, suggestion: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.suggestion = suggestion

    def show(self) -> None:
        """Display the error with suggestion."""
        text = Text()
        text.append("✗ ", style="bold red")
        text.append(self.message, style="red")

        if self.suggestion:
            text.append("\n\n💡 ", style="bold yellow")
            text.append(self.suggestion, style="yellow")

        console.print(Panel(text, border_style="red", title="Error"))


class ConfigurationError(LoadTestError):
    """Configuration-related errors."""

    pass


class ConnectionError(LoadTestError):
    """Connection-related errors."""

    pass


class ScenarioError(LoadTestError):
    """Scenario-related errors."""

    pass


class PatternError(LoadTestError):
    """Traffic pattern errors."""

    pass


# Error patterns and suggestions
ERROR_SUGGESTIONS = {
    # URL errors
    r"invalid url|malformed url|no scheme": {
        "message": "Invalid URL format",
        "suggestion": "Make sure your URL includes the scheme (http:// or https://).\nExample: https://api.example.com instead of api.example.com",
    },
    # Connection errors
    r"connection refused|errno 111": {
        "message": "Connection refused",
        "suggestion": "The server rejected the connection. Check that:\n• The server is running\n• The port is correct\n• Firewall rules allow the connection",
    },
    r"name or service not known|getaddrinfo failed|nodename nor servname": {
        "message": "Could not resolve hostname",
        "suggestion": "The domain name could not be resolved. Check that:\n• The URL is spelled correctly\n• You have internet connectivity\n• DNS is working (try: nslookup \u003cdomain\u003e)",
    },
    r"timeout|timed out": {
        "message": "Request timed out",
        "suggestion": "The server took too long to respond. Try:\n• Increasing the timeout: test.add(..., timeout=60)\n• Checking if the server is overloaded\n• Verifying the endpoint exists",
    },
    # SSL/TLS errors
    r"ssl|certificate|tls|verify": {
        "message": "SSL/TLS error",
        "suggestion": "There's a certificate issue. Options:\n• For self-signed certs in testing: verify=False (not for production!)\n• Check system time is correct\n• Update CA certificates: pip install --upgrade certifi",
    },
    # HTTP errors
    r"404|not found": {
        "message": "Endpoint not found (404)",
        "suggestion": "The endpoint doesn't exist. Check:\n• The URL path is correct\n• You're using the right HTTP method\n• The API version is correct",
    },
    r"401|unauthorized": {
        "message": "Authentication required (401)",
        "suggestion": "You need to authenticate. Try:\n• test.auth('your-token')\n• test.headers({'Authorization': 'Bearer TOKEN'})\n• test.headers({'X-API-Key': 'your-key'})",
    },
    r"403|forbidden": {
        "message": "Access forbidden (403)",
        "suggestion": "You don't have permission. Check:\n• Your authentication token is valid\n• Your account has the required permissions\n• IP allowlists/firewall rules",
    },
    r"429|too many requests": {
        "message": "Rate limited (429)",
        "suggestion": "The server is rate-limiting you. Try:\n• Reducing RPS: loadtest(..., rps=5)\n• Adding delays between requests\n• Checking API rate limit documentation",
    },
    r"500|internal server error": {
        "message": "Server error (500)",
        "suggestion": "The server encountered an error. This is usually a bug in the server.\nCheck server logs or try:\n• Different request parameters\n• Different endpoint\n• Contacting the API provider",
    },
    r"502|bad gateway": {
        "message": "Bad gateway (502)",
        "suggestion": "The proxy/gateway received an invalid response.\nThe upstream server may be down or overloaded.",
    },
    r"503|service unavailable": {
        "message": "Service unavailable (503)",
        "suggestion": "The server is temporarily unavailable.\nIt may be overloaded or down for maintenance.",
    },
    # Configuration errors
    r"no scenarios|empty scenarios": {
        "message": "No test scenarios configured",
        "suggestion": "Add at least one endpoint:\n• test.add('GET /users')\n• test.add('POST /orders', json={'item': 'widget'})",
    },
    r"no pattern|pattern not set": {
        "message": "No traffic pattern set",
        "suggestion": "Set a pattern when creating the test:\n• loadtest(..., pattern='constant')\n• loadtest(..., pattern='ramp', rps=10, target_rps=100)",
    },
    # Import errors
    r"no module named|cannot import|import error": {
        "message": "Import error",
        "suggestion": "Make sure loadtest is installed:\n• pip install loadtest\n• pip install -e . (if developing)",
    },
}


def analyze_error(error: Exception) -> tuple[str, str | None]:
    """Analyze an error and return enhanced message with suggestion.

    Args:
        error: The exception to analyze

    Returns:
        Tuple of (message, suggestion)
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    full_error = f"{error_type}: {error_str}"

    for pattern, info in ERROR_SUGGESTIONS.items():
        if re.search(pattern, full_error) or re.search(pattern, error_str):
            return info["message"], info["suggestion"]

    # Default message for unknown errors
    return str(error), None


def show_error(error: Exception, context: str | None = None) -> None:
    """Display an error with helpful suggestion.

    Args:
        error: The exception to display
        context: Optional context about what was happening
    """
    message, suggestion = analyze_error(error)

    text = Text()
    text.append("✗ ", style="bold red")

    if context:
        text.append(f"{context}\n", style="dim")

    text.append(message, style="bold red")

    if suggestion:
        text.append("\n\n💡 ", style="bold yellow")
        text.append(suggestion, style="yellow")

    # Add original error for debugging
    original = str(error)
    if original and original.lower() != message.lower():
        text.append(f"\n\n[dim]Original: {original}[/dim]")

    console.print()
    console.print(Panel(text, border_style="red", title="Error"))
    console.print()


def suggest_fix(error: Exception) -> str | None:
    """Get suggestion text for an error.

    Args:
        error: The exception to analyze

    Returns:
        Suggestion string or None
    """
    _, suggestion = analyze_error(error)
    return suggestion


def validate_config(config: dict[str, Any]) -> list[str]:
    """Validate configuration and return list of issues.

    Args:
        config: Configuration dictionary

    Returns:
        List of validation issues
    """
    issues = []

    # Check target
    target = config.get("target", "")
    if not target:
        issues.append("No target URL specified")
    elif not target.startswith(("http://", "https://")):
        issues.append(f"Target URL missing scheme: {target}")

    # Check duration
    duration = config.get("duration", 0)
    if duration <= 0:
        issues.append(f"Invalid duration: {duration}")
    elif duration > 3600:
        issues.append(f"Very long duration ({duration}s > 1 hour) - did you mean minutes?")

    # Check RPS
    rps = config.get("rps", 0)
    if rps <= 0:
        issues.append(f"Invalid RPS: {rps}")
    elif rps > 10000:
        issues.append(f"Very high RPS ({rps}) - make sure this is intentional")

    # Check endpoints
    endpoints = config.get("endpoints", [])
    if not endpoints:
        issues.append("No endpoints configured - will test root path only")

    # Check pattern
    pattern = config.get("pattern", "constant")
    valid_patterns = ["constant", "ramp", "spike", "burst", "wave", "step"]
    if pattern not in valid_patterns:
        issues.append(f"Unknown pattern '{pattern}' - use one of: {', '.join(valid_patterns)}")

    return issues


def show_validation_warnings(issues: list[str]) -> None:
    """Display validation warnings.

    Args:
        issues: List of validation issues
    """
    if not issues:
        return

    text = Text()
    text.append("⚠ Configuration Warnings:\n\n", style="bold yellow")

    for issue in issues:
        text.append(f"  • {issue}\n", style="yellow")

    console.print(Panel(text, border_style="yellow", title="Warning"))
