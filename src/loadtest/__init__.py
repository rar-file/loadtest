"""LoadTest - Synthetic traffic generator for load testing web applications.

This package provides tools for generating realistic load against web applications
using async patterns, realistic user data from Phoney, and various traffic patterns.
"""

from loadtest.__version__ import __author__, __email__, __license__, __version__
from loadtest.core import LoadTest
from loadtest.runner import TestRunner

__all__ = [
    "LoadTest",
    "TestRunner",
    "__version__",
    "__author__",
    "__email__",
    "__license__",
]
