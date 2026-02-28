"""Configuration file utilities for loadtest.

Generate, load, and manage loadtest configuration files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

from loadtest.simple_api import SimpleLoadTest


def to_dict(test: SimpleLoadTest) -> dict[str, Any]:
    """Convert a SimpleLoadTest to a dictionary.

    Args:
        test: The test to convert

    Returns:
        Configuration dictionary
    """
    return {
        "target": test.target,
        "pattern": test._pattern_type,
        "rps": test._rps,
        "duration": test._duration,
        "pattern_options": test._pattern_kwargs,
        "global_headers": test._global_headers,
        "endpoints": [
            {
                "method": ep.method,
                "path": ep.path,
                "weight": ep.weight,
                "headers": ep.headers,
                "json": ep.json,
                "data": ep.data,
            }
            for ep in test._endpoints
        ],
    }


def from_dict(config: dict[str, Any]) -> SimpleLoadTest:
    """Create a SimpleLoadTest from a dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        Configured SimpleLoadTest instance
    """
    from loadtest import loadtest

    test = loadtest(
        target=config["target"],
        pattern=config.get("pattern", "constant"),
        rps=config.get("rps", 10),
        duration=config.get("duration", 60),
        **config.get("pattern_options", {}),
    )

    # Set global headers
    if config.get("global_headers"):
        test.headers(config["global_headers"])

    # Add endpoints
    for ep in config.get("endpoints", []):
        test.add(
            endpoint=f"{ep['method']} {ep['path']}",
            weight=ep.get("weight", 1.0),
            headers=ep.get("headers"),
            json=ep.get("json"),
            data=ep.get("data"),
        )

    return test


def save_json(test: SimpleLoadTest, path: str | Path) -> None:
    """Save test configuration to JSON file.

    Args:
        test: Test to save
        path: File path

    Example:
        >>> test = loadtest("https://api.example.com")
        >>> test.add("GET /users")
        >>> save_json(test, "my_test.json")
    """
    path = Path(path)
    config = to_dict(test)

    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def load_json(path: str | Path) -> SimpleLoadTest:
    """Load test configuration from JSON file.

    Args:
        path: File path

    Returns:
        Configured SimpleLoadTest instance

    Example:
        >>> test = load_json("my_test.json")
        >>> test.run()
    """
    path = Path(path)

    with open(path) as f:
        config = json.load(f)

    return from_dict(config)


def save_yaml(test: SimpleLoadTest, path: str | Path) -> None:
    """Save test configuration to YAML file.

    Args:
        test: Test to save
        path: File path

    Example:
        >>> test = loadtest("https://api.example.com")
        >>> save_yaml(test, "my_test.yaml")
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")

    path = Path(path)
    config = to_dict(test)

    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def load_yaml(path: str | Path) -> SimpleLoadTest:
    """Load test configuration from YAML file.

    Args:
        path: File path

    Returns:
        Configured SimpleLoadTest instance

    Example:
        >>> test = load_yaml("my_test.yaml")
        >>> test.run()
    """
    if not HAS_YAML:
        raise ImportError("PyYAML is required for YAML support. Install with: pip install pyyaml")

    path = Path(path)

    with open(path) as f:
        config = yaml.safe_load(f)

    return from_dict(config)


def save(test: SimpleLoadTest, path: str | Path) -> None:
    """Save test configuration (auto-detects format from extension).

    Args:
        test: Test to save
        path: File path (.json or .yaml/.yml)

    Example:
        >>> test = loadtest("https://api.example.com")
        >>> save(test, "my_test.yaml")
    """
    path = Path(path)

    if path.suffix in (".yaml", ".yml"):
        save_yaml(test, path)
    else:
        save_json(test, path)


def load(path: str | Path) -> SimpleLoadTest:
    """Load test configuration (auto-detects format from extension).

    Args:
        path: File path (.json or .yaml/.yml)

    Returns:
        Configured SimpleLoadTest instance

    Example:
        >>> test = load("my_test.yaml")
        >>> test.run()
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    if path.suffix in (".yaml", ".yml"):
        return load_yaml(path)
    else:
        return load_json(path)


def generate_config_file(
    target: str,
    pattern: str = "constant",
    rps: float = 10,
    duration: float = 60,
    endpoints: list[dict[str, Any]] | None = None,
    output: str = "loadtest.json",
) -> Path:
    """Generate a new configuration file.

    This is a convenience function for CLI usage.

    Args:
        target: Target URL
        pattern: Traffic pattern
        rps: Requests per second
        duration: Test duration
        endpoints: List of endpoint configs
        output: Output file path

    Returns:
        Path to generated file

    Example:
        >>> from loadtest.config import generate_config_file
        >>> generate_config_file(
        ...     target="https://api.example.com",
        ...     endpoints=[{"method": "GET", "path": "/users"}]
        ... )
    """
    config = {
        "target": target,
        "pattern": pattern,
        "rps": rps,
        "duration": duration,
        "endpoints": endpoints or [{"method": "GET", "path": "/"}],
    }

    path = Path(output)

    if path.suffix in (".yaml", ".yml"):
        if not HAS_YAML:
            raise ImportError(
                "PyYAML is required for YAML support. Install with: pip install pyyaml"
            )
        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    else:
        with open(path, "w") as f:
            json.dump(config, f, indent=2)

    return path
