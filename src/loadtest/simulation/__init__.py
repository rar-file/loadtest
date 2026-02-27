"""User behavior simulation engine for realistic session flows.

This module provides the Session and SessionFlow classes for simulating
realistic user behaviors with state management, think times, and multi-step flows.
"""

from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Coroutine


class SessionState(Enum):
    """Session lifecycle states."""
    CREATED = auto()
    ACTIVE = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class SessionMetrics:
    """Per-session metrics."""
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    step_count: int = 0
    error_count: int = 0
    total_think_time: float = 0.0
    total_execution_time: float = 0.0
    
    @property
    def duration(self) -> float:
        """Total session duration."""
        end = self.completed_at or time.time()
        return end - self.created_at
    
    @property
    def active_duration(self) -> float:
        """Time spent actively executing (excluding think time)."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return (end - self.started_at) - self.total_think_time


class ThinkTimeModel:
    """Models realistic think times between user actions.
    
    Supports various statistical distributions to simulate realistic
    user pauses between actions.
    
    Example:
        >>> # Normal distribution with 2s mean, 0.5s std dev
        >>> think_time = ThinkTimeModel.normal(mean=2.0, std_dev=0.5)
        >>> 
        >>> # Exponential distribution with 1.5s mean
        >>> think_time = ThinkTimeModel.exponential(mean=1.5)
        >>> 
        >>> # Fixed think time
        >>> think_time = ThinkTimeModel.fixed(seconds=1.0)
        >>> 
        >>> # Custom distribution
        >>> think_time = ThinkTimeModel.custom(lambda: random.gauss(2, 0.5))
    """
    
    def __init__(self, sampler: Callable[[], float]) -> None:
        """Initialize with a custom sampler function.
        
        Args:
            sampler: Callable that returns a think time in seconds.
        """
        self._sampler = sampler
    
    def sample(self) -> float:
        """Get a sample think time.
        
        Returns:
            Think time in seconds (always non-negative).
        """
        return max(0.0, self._sampler())
    
    async def wait(self) -> float:
        """Wait for a sampled think time.
        
        Returns:
            The actual time waited in seconds.
        """
        duration = self.sample()
        await asyncio.sleep(duration)
        return duration
    
    @classmethod
    def normal(cls, mean: float, std_dev: float) -> ThinkTimeModel:
        """Normal (Gaussian) distribution think times.
        
        Args:
            mean: Mean think time in seconds.
            std_dev: Standard deviation in seconds.
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(lambda: random.gauss(mean, std_dev))
    
    @classmethod
    def lognormal(cls, mean: float, sigma: float) -> ThinkTimeModel:
        """Log-normal distribution think times.
        
        Good for modeling think times that are always positive
        with occasional long pauses.
        
        Args:
            mean: Mean of the underlying normal distribution.
            sigma: Standard deviation of the underlying normal distribution.
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(lambda: random.lognormvariate(mean, sigma))
    
    @classmethod
    def exponential(cls, mean: float) -> ThinkTimeModel:
        """Exponential distribution think times.
        
        Models random arrivals (Poisson process). Good for
        modeling "impatient" users.
        
        Args:
            mean: Mean think time in seconds (1/lambda).
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(lambda: random.expovariate(1.0 / mean))
    
    @classmethod
    def fixed(cls, seconds: float) -> ThinkTimeModel:
        """Fixed (deterministic) think times.
        
        Args:
            seconds: Fixed think time in seconds.
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(lambda: seconds)
    
    @classmethod
    def uniform(cls, min_seconds: float, max_seconds: float) -> ThinkTimeModel:
        """Uniform distribution think times.
        
        Args:
            min_seconds: Minimum think time.
            max_seconds: Maximum think time.
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(lambda: random.uniform(min_seconds, max_seconds))
    
    @classmethod
    def gamma(cls, shape: float, scale: float) -> ThinkTimeModel:
        """Gamma distribution think times.
        
        Flexible distribution that can model various user behaviors.
        
        Args:
            shape: Shape parameter (k).
            scale: Scale parameter (theta).
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(lambda: random.gammavariate(shape, scale))
    
    @classmethod
    def bimodal(
        cls,
        fast_mean: float,
        fast_std: float,
        slow_mean: float,
        slow_std: float,
        fast_prob: float = 0.7
    ) -> ThinkTimeModel:
        """Bimodal distribution modeling fast/slow user types.
        
        Models a mix of "fast" and "slow" users.
        
        Args:
            fast_mean: Mean think time for fast users.
            fast_std: Standard deviation for fast users.
            slow_mean: Mean think time for slow users.
            slow_std: Standard deviation for slow users.
            fast_prob: Probability of being a fast user.
        
        Returns:
            ThinkTimeModel instance.
        """
        def sampler():
            if random.random() < fast_prob:
                return random.gauss(fast_mean, fast_std)
            return random.gauss(slow_mean, slow_std)
        return cls(sampler)
    
    @classmethod
    def custom(cls, sampler: Callable[[], float]) -> ThinkTimeModel:
        """Create a think time model with a custom sampler.
        
        Args:
            sampler: Callable that returns think time in seconds.
        
        Returns:
            ThinkTimeModel instance.
        """
        return cls(sampler)


class Session:
    """Represents a simulated user session.
    
    A session maintains state across multiple steps and can include
    realistic think times between actions.
    
    Attributes:
        session_id: Unique identifier for this session.
        state: Current session state.
        data: Session-scoped data storage.
        metrics: Session performance metrics.
    
    Example:
        >>> session = Session(session_id="user_001")
        >>> session.set("username", "john_doe")
        >>> username = session.get("username")
    """
    
    _counter = 0
    _lock = asyncio.Lock()
    
    def __init__(
        self,
        session_id: str | None = None,
        think_time: ThinkTimeModel | None = None,
    ) -> None:
        """Initialize a new session.
        
        Args:
            session_id: Optional session ID (auto-generated if not provided).
            think_time: Think time model for this session.
        """
        self.session_id = session_id or self._generate_id()
        self.state = SessionState.CREATED
        self.data: dict[str, Any] = {}
        self.metrics = SessionMetrics()
        self.think_time = think_time or ThinkTimeModel.fixed(0)
        self._context: dict[str, Any] = {}
        self._current_step: int = 0
        self._lock = asyncio.Lock()
    
    @classmethod
    def _generate_id(cls) -> str:
        """Generate a unique session ID."""
        cls._counter += 1
        return f"session_{cls._counter}_{int(time.time() * 1000)}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from session storage.
        
        Args:
            key: Data key.
            default: Default value if key not found.
        
        Returns:
            Stored value or default.
        """
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> Session:
        """Set a value in session storage.
        
        Args:
            key: Data key.
            value: Value to store.
        
        Returns:
            Self for method chaining.
        """
        self.data[key] = value
        return self
    
    def update(self, values: dict[str, Any]) -> Session:
        """Update session storage with multiple values.
        
        Args:
            values: Dictionary of values to merge.
        
        Returns:
            Self for method chaining.
        """
        self.data.update(values)
        return self
    
    async def think(self) -> float:
        """Pause execution for a realistic think time.
        
        Returns:
            Actual time waited in seconds.
        """
        waited = await self.think_time.wait()
        self.metrics.total_think_time += waited
        return waited
    
    async def start(self) -> None:
        """Mark session as started."""
        async with self._lock:
            if self.state == SessionState.CREATED:
                self.state = SessionState.ACTIVE
                self.metrics.started_at = time.time()
    
    async def complete(self) -> None:
        """Mark session as completed."""
        async with self._lock:
            self.state = SessionState.COMPLETED
            self.metrics.completed_at = time.time()
    
    async def fail(self, error: Exception | None = None) -> None:
        """Mark session as failed.
        
        Args:
            error: Optional exception that caused the failure.
        """
        async with self._lock:
            self.state = SessionState.FAILED
            self.metrics.completed_at = time.time()
            self.metrics.error_count += 1
            if error:
                self.set("_last_error", str(error))
    
    def to_context(self) -> dict[str, Any]:
        """Convert session to execution context.
        
        Returns:
            Context dictionary for scenario execution.
        """
        return {
            "session": self,
            "session_id": self.session_id,
            **self._context,
        }
    
    def __repr__(self) -> str:
        return f"Session(id={self.session_id}, state={self.state.name})"


class SessionStep(ABC):
    """Abstract base class for session flow steps.
    
    Each step represents a single action in a user session flow.
    
    Example:
        >>> class LoginStep(SessionStep):
        ...     async def execute(self, session: Session) -> bool:
        ...         # Perform login
        ...         return True
    """
    
    def __init__(
        self,
        name: str,
        think_time: ThinkTimeModel | None = None,
        max_retries: int = 0,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize a session step.
        
        Args:
            name: Step name.
            think_time: Optional think time after this step.
            max_retries: Maximum retry attempts on failure.
            retry_delay: Delay between retries in seconds.
        """
        self.name = name
        self.think_time = think_time
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    @abstractmethod
    async def execute(self, session: Session) -> Any:
        """Execute this step.
        
        Args:
            session: The current session.
        
        Returns:
            Step result (interpreted by the flow).
        
        Raises:
            Exception: Step failures are caught and can trigger retries.
        """
        pass
    
    async def run(self, session: Session) -> Any:
        """Execute step with retry logic and think time.
        
        Args:
            session: The current session.
        
        Returns:
            Step result.
        
        Raises:
            Exception: If all retries are exhausted.
        """
        last_error: Exception | None = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await self.execute(session)
                session.metrics.step_count += 1
                
                # Apply think time after successful execution
                if self.think_time:
                    await session.think()
                
                return result
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise
        
        raise last_error or RuntimeError("Step failed with no error captured")


@dataclass
class StepResult:
    """Result of a session step execution."""
    step_name: str
    success: bool
    result: Any = None
    error: Exception | None = None
    duration: float = 0.0
    think_time: float = 0.0


class SessionFlow:
    """Defines and executes a multi-step user session flow.
    
    A flow consists of multiple steps that execute sequentially,
    with support for conditional branching and loops.
    
    Example:
        >>> flow = SessionFlow("User Checkout")
        >>> flow.add_step(BrowseProducts())
        >>> flow.add_step(AddToCart())
        >>> flow.add_step(Checkout(), condition=lambda s: s.get("cart_items", 0) > 0)
        >>> 
        >>> session = Session()
        >>> results = await flow.execute(session)
    """
    
    def __init__(self, name: str, default_think_time: ThinkTimeModel | None = None) -> None:
        """Initialize a session flow.
        
        Args:
            name: Flow name.
            default_think_time: Default think time for steps.
        """
        self.name = name
        self.steps: list[tuple[SessionStep, Callable[[Session], bool] | None]] = []
        self.default_think_time = default_think_time or ThinkTimeModel.fixed(0)
        self.on_step_complete: list[Callable[[StepResult], None]] = []
    
    def add_step(
        self,
        step: SessionStep,
        condition: Callable[[Session], bool] | None = None
    ) -> SessionFlow:
        """Add a step to the flow.
        
        Args:
            step: The step to add.
            condition: Optional condition function. Step only executes if True.
        
        Returns:
            Self for method chaining.
        """
        self.steps.append((step, condition))
        return self
    
    def add_callback(self, callback: Callable[[StepResult], None]) -> SessionFlow:
        """Add a callback to be called after each step.
        
        Args:
            callback: Function called with StepResult after each step.
        
        Returns:
            Self for method chaining.
        """
        self.on_step_complete.append(callback)
        return self
    
    async def execute(self, session: Session) -> list[StepResult]:
        """Execute the flow for a session.
        
        Args:
            session: The session to execute with.
        
        Returns:
            List of step results.
        """
        results: list[StepResult] = []
        
        await session.start()
        start_time = time.time()
        
        try:
            for step, condition in self.steps:
                # Check condition
                if condition and not condition(session):
                    continue
                
                step_start = time.time()
                think_before = session.metrics.total_think_time
                
                try:
                    result = await step.run(session)
                    step_duration = time.time() - step_start
                    think_time = session.metrics.total_think_time - think_before
                    
                    step_result = StepResult(
                        step_name=step.name,
                        success=True,
                        result=result,
                        duration=step_duration,
                        think_time=think_time,
                    )
                    
                except Exception as e:
                    step_duration = time.time() - step_start
                    step_result = StepResult(
                        step_name=step.name,
                        success=False,
                        error=e,
                        duration=step_duration,
                    )
                    session.metrics.error_count += 1
                
                results.append(step_result)
                
                # Notify callbacks
                for callback in self.on_step_complete:
                    try:
                        callback(step_result)
                    except Exception:
                        pass
                
                # Stop on failure if configured
                if not step_result.success:
                    break
            
            await session.complete()
            
        except Exception as e:
            await session.fail(e)
            raise
        
        finally:
            session.metrics.total_execution_time = time.time() - start_time
        
        return results


class SimulationEngine:
    """Engine for running multiple user session simulations.
    
    Manages concurrent sessions, tracks overall metrics, and coordinates
    session lifecycle across multiple flows.
    
    Example:
        >>> engine = SimulationEngine(max_concurrent=100)
        >>> engine.register_flow("checkout", checkout_flow)
        >>> 
        >>> # Run 1000 sessions with think times
        >>> await engine.run_sessions(
        ...     flow_name="checkout",
        ...     count=1000,
        ...     arrival_rate=10,  # 10 new sessions per second
        ... )
    """
    
    def __init__(
        self,
        max_concurrent: int = 100,
        global_think_time: ThinkTimeModel | None = None,
    ) -> None:
        """Initialize the simulation engine.
        
        Args:
            max_concurrent: Maximum concurrent sessions.
            global_think_time: Default think time model.
        """
        self.max_concurrent = max_concurrent
        self.global_think_time = global_think_time or ThinkTimeModel.fixed(0)
        self.flows: dict[str, SessionFlow] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._sessions: list[Session] = []
        self._results: dict[str, list[list[StepResult]]] = {}
        self._on_session_complete: list[Callable[[Session, list[StepResult]], None]] = []
    
    def register_flow(self, name: str, flow: SessionFlow) -> SimulationEngine:
        """Register a session flow.
        
        Args:
            name: Flow identifier.
            flow: The session flow.
        
        Returns:
            Self for method chaining.
        """
        self.flows[name] = flow
        return self
    
    def on_session_complete(
        self,
        callback: Callable[[Session, list[StepResult]], None]
    ) -> SimulationEngine:
        """Register a callback for session completion.
        
        Args:
            callback: Function called when a session completes.
        
        Returns:
            Self for method chaining.
        """
        self._on_session_complete.append(callback)
        return self
    
    async def run_session(self, flow_name: str, session: Session | None = None) -> tuple[Session, list[StepResult]]:
        """Run a single session.
        
        Args:
            flow_name: Name of the registered flow to execute.
            session: Optional existing session (creates new if not provided).
        
        Returns:
            Tuple of (session, step_results).
        """
        flow = self.flows.get(flow_name)
        if not flow:
            raise ValueError(f"Flow not found: {flow_name}")
        
        if session is None:
            session = Session(think_time=self.global_think_time)
        
        async with self._semaphore:
            self._sessions.append(session)
            results = await flow.execute(session)
            
            # Store results
            if flow_name not in self._results:
                self._results[flow_name] = []
            self._results[flow_name].append(results)
            
            # Notify callbacks
            for callback in self._on_session_complete:
                try:
                    callback(session, results)
                except Exception:
                    pass
            
            return session, results
    
    async def run_sessions(
        self,
        flow_name: str,
        count: int,
        arrival_rate: float | None = None,
        think_time: ThinkTimeModel | None = None,
    ) -> list[tuple[Session, list[StepResult]]]:
        """Run multiple sessions.
        
        Args:
            flow_name: Name of the registered flow.
            count: Number of sessions to run.
            arrival_rate: Sessions per second (None = unlimited).
            think_time: Think time model for new sessions.
        
        Returns:
            List of (session, results) tuples.
        """
        results: list[tuple[Session, list[StepResult]]] = []
        tasks: list[asyncio.Task] = []
        
        interval = 1.0 / arrival_rate if arrival_rate else 0
        
        for i in range(count):
            session = Session(think_time=think_time or self.global_think_time)
            
            task = asyncio.create_task(
                self._run_session_wrapped(flow_name, session, results)
            )
            tasks.append(task)
            
            if interval > 0 and i < count - 1:
                await asyncio.sleep(interval)
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    async def _run_session_wrapped(
        self,
        flow_name: str,
        session: Session,
        results: list
    ) -> None:
        """Wrapper for session execution with exception handling."""
        try:
            _, step_results = await self.run_session(flow_name, session)
            results.append((session, step_results))
        except Exception as e:
            await session.fail(e)
            results.append((session, []))
    
    def get_statistics(self) -> dict[str, Any]:
        """Get simulation statistics.
        
        Returns:
            Dictionary with simulation statistics.
        """
        total_sessions = len(self._sessions)
        completed = sum(1 for s in self._sessions if s.state == SessionState.COMPLETED)
        failed = sum(1 for s in self._sessions if s.state == SessionState.FAILED)
        
        total_steps = sum(s.metrics.step_count for s in self._sessions)
        total_errors = sum(s.metrics.error_count for s in self._sessions)
        total_think_time = sum(s.metrics.total_think_time for s in self._sessions)
        total_duration = sum(s.metrics.duration for s in self._sessions)
        
        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed,
            "failed_sessions": failed,
            "completion_rate": (completed / total_sessions * 100) if total_sessions else 0,
            "total_steps": total_steps,
            "total_errors": total_errors,
            "error_rate": (total_errors / total_steps * 100) if total_steps else 0,
            "avg_steps_per_session": total_steps / total_sessions if total_sessions else 0,
            "total_think_time": total_think_time,
            "total_duration": total_duration,
            "avg_session_duration": total_duration / total_sessions if total_sessions else 0,
        }
    
    def reset(self) -> None:
        """Reset the engine state."""
        self._sessions.clear()
        self._results.clear()
