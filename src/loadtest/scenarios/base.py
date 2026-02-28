"""Base scenario class for load testing.

This module defines the abstract base class that all scenario types
must implement to be used in load tests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from phoney import Phoney


class Scenario(ABC):
    """Abstract base class for load test scenarios.

    A scenario represents a single type of user action or request that
    can be executed during a load test. Subclasses must implement the
    `execute` method to define the actual behavior.

    Attributes:
        name: Human-readable name for this scenario.
        phoney: Phoney instance for generating realistic test data.

    Example:
        >>> class MyScenario(Scenario):
        ...     async def execute(self, context):
        ...         # Implementation here
        ...         pass
    """

    def __init__(self, name: str | None = None) -> None:
        """Initialize the scenario.

        Args:
            name: Optional name for this scenario. Defaults to the class name.
        """
        self.name = name or self.__class__.__name__
        self._phoney: Phoney | None = None

    @property
    def phoney(self) -> Phoney:
        """Get or create a Phoney instance for data generation.

        Returns:
            Phoney instance for generating realistic user data.
        """
        if self._phoney is None:
            # Lazy import to avoid dependency issues
            from phoney import Phoney

            self._phoney = Phoney()
        return self._phoney

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> Any:
        """Execute this scenario.

        This method must be implemented by subclasses to define
        the actual behavior of the scenario.

        Args:
            context: Dictionary containing shared context and resources.
                    May include 'metrics' for recording custom metrics.

        Returns:
            Result of the scenario execution. The exact type depends
            on the scenario implementation.

        Raises:
            Exception: Any exception raised during execution will be
                      caught and recorded as a failure.
        """
        pass

    def __repr__(self) -> str:
        """Return a string representation of the scenario."""
        return f"{self.__class__.__name__}(name='{self.name}')"
