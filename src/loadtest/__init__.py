"""LoadTest - Simple, powerful load testing in 3 lines.

Quick Start:
    >>> from loadtest import loadtest
    >>> test = loadtest("https://api.example.com")
    >>> test.run()

Advanced Usage:
    >>> test = loadtest("https://api.example.com", 
    ...                 pattern="ramp", rps=100, duration=60)
    >>> test.add("GET /users")
    >>> test.add("POST /orders", weight=0.3)
    >>> test.run()
"""

from loadtest.__version__ import __author__, __email__, __license__, __version__
from loadtest.core import LoadTest
from loadtest.runner import TestRunner
from loadtest.simple_api import loadtest

__all__ = [
    "LoadTest",
    "TestRunner",
    "loadtest",  # Simple API
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]
