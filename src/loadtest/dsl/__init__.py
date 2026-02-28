"""Scenario scripting DSL for load testing.

Provides a fluent, Python-based domain-specific language for defining
load test scenarios with a natural, readable syntax.

Example:
    >>> from loadtest.dsl import *
    >>>
    >>> scenario = (
    ...     scenario("User Login Flow")
    ...     .with_session()
    ...     .step("Open Login Page", http_get("https://example.com/login"))
    ...     .think_time(normal(mean=2, std=0.5))
    ...     .step("Enter Credentials", http_post(
    ...         "https://example.com/login",
    ...         json_data=lambda: {"email": fake.email(), "password": "test123"}
    ...     ))
    ...     .validate(status_2xx())
    ... )
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

# ============================================================================
# Think Time DSL
# ============================================================================


def fixed(seconds: float) -> Callable[[], float]:
    """Fixed think time.

    Example:
        >>> think_time = fixed(1.5)  # Always 1.5 seconds
    """
    return lambda: seconds


def normal(mean: float, std: float) -> Callable[[], float]:
    """Normal distribution think time.

    Example:
        >>> think_time = normal(mean=2.0, std=0.5)
    """
    return lambda: random.gauss(mean, std)


def exponential(mean: float) -> Callable[[], float]:
    """Exponential distribution think time.

    Example:
        >>> think_time = exponential(mean=1.5)
    """
    return lambda: random.expovariate(1.0 / mean)


def uniform(min_val: float, max_val: float) -> Callable[[], float]:
    """Uniform distribution think time.

    Example:
        >>> think_time = uniform(min_val=1, max_val=3)
    """
    return lambda: random.uniform(min_val, max_val)


def lognormal(mean: float, sigma: float) -> Callable[[], float]:
    """Log-normal distribution think time.

    Example:
        >>> think_time = lognormal(mean=0.5, sigma=0.5)
    """
    return lambda: random.lognormvariate(mean, sigma)


# ============================================================================
# Data Generation DSL
# ============================================================================


class FakeData:
    """Fake data generator using Phoney."""

    _phoney = None

    @classmethod
    def _get_phoney(cls):
        if cls._phoney is None:
            from phoney import Phoney

            cls._phoney = Phoney()
        return cls._phoney

    @classmethod
    def email(cls) -> str:
        """Generate random email."""
        return cls._get_phoney().email()

    @classmethod
    def username(cls) -> str:
        """Generate random username."""
        return cls._get_phoney().username()

    @classmethod
    def full_name(cls) -> str:
        """Generate random full name."""
        return cls._get_phoney().full_name()

    @classmethod
    def phone(cls) -> str:
        """Generate random phone number."""
        return cls._get_phoney().phone()

    @classmethod
    def address(cls) -> str:
        """Generate random address."""
        return cls._get_phoney().address()

    @classmethod
    def company(cls) -> str:
        """Generate random company name."""
        return cls._get_phoney().company()

    @classmethod
    def text(cls, min_words: int = 5, max_words: int = 20) -> str:
        """Generate random text."""
        return cls._get_phoney().text(min_words, max_words)

    @classmethod
    def uuid(cls) -> str:
        """Generate random UUID."""
        import uuid

        return str(uuid.uuid4())

    @classmethod
    def random_int(cls, min_val: int = 0, max_val: int = 100) -> int:
        """Generate random integer."""
        return random.randint(min_val, max_val)

    @classmethod
    def random_choice(cls, choices: list[Any]) -> Any:
        """Pick random item from list."""
        return random.choice(choices)

    @classmethod
    def password(cls, length: int = 12) -> str:
        """Generate random password."""
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        return "".join(random.choices(chars, k=length))


# Short alias
fake = FakeData


# ============================================================================
# HTTP Action DSL
# ============================================================================


@dataclass
class HTTPConfig:
    """Configuration for HTTP requests."""

    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    json_data: Any = None
    form_data: dict[str, Any] = field(default_factory=dict)
    text_data: str = ""
    timeout: float = 30.0
    follow_redirects: bool = True


class HTTPAction:
    """HTTP action that can be executed."""

    def __init__(self, config: HTTPConfig) -> None:
        """Initialize HTTP action.

        Args:
            config: HTTP configuration.
        """
        self.config = config
        self._extractors: list[Callable] = []
        self._validators: list[Callable] = []

    def extract_json(self, path: str, var_name: str) -> HTTPAction:
        """Extract value from JSON response.

        Args:
            path: JSON path (e.g., "data.token" or "items[0].id").
            var_name: Variable name to store in session.

        Returns:
            Self for chaining.
        """

        def extractor(response: httpx.Response, session: dict) -> None:
            try:
                data = response.json()
                # Simple path traversal
                keys = path.replace("[", ".").replace("]", "").split(".")
                value = data
                for key in keys:
                    value = value[int(key)] if key.isdigit() else value[key]
                session[var_name] = value
            except Exception:
                pass

        self._extractors.append(extractor)
        return self

    def extract_header(self, header: str, var_name: str) -> HTTPAction:
        """Extract value from response header.

        Args:
            header: Header name.
            var_name: Variable name to store in session.

        Returns:
            Self for chaining.
        """

        def extractor(response: httpx.Response, session: dict) -> None:
            value = response.headers.get(header)
            if value:
                session[var_name] = value

        self._extractors.append(extractor)
        return self

    def validate(self, validator: Callable[[httpx.Response], bool]) -> HTTPAction:
        """Add a response validator.

        Args:
            validator: Function that takes response and returns True if valid.

        Returns:
            Self for chaining.
        """
        self._validators.append(validator)
        return self

    async def execute(self, client: httpx.AsyncClient, session: dict) -> httpx.Response:
        """Execute the HTTP action.

        Args:
            client: HTTP client.
            session: Session storage for extracted values.

        Returns:
            HTTP response.

        Raises:
            AssertionError: If validation fails.
        """
        # Resolve dynamic data
        json_data = self._resolve_data(self.config.json_data, session)
        form_data = self._resolve_data(self.config.form_data, session)
        text_data = self._resolve_data(self.config.text_data, session)

        # Make request
        response = await client.request(
            method=self.config.method,
            url=self.config.url,
            headers=self.config.headers,
            params=self.config.params,
            json=json_data,
            data=form_data if form_data else text_data,
            timeout=self.config.timeout,
            follow_redirects=self.config.follow_redirects,
        )

        # Run extractors
        for extractor in self._extractors:
            extractor(response, session)

        # Run validators
        for validator in self._validators:
            if not validator(response):
                raise AssertionError(f"Validation failed: {validator.__name__}")

        return response

    def _resolve_data(self, data: Any, session: dict) -> Any:
        """Resolve dynamic data (callables, templates)."""
        if callable(data):
            return data()

        if isinstance(data, dict):
            resolved = {}
            for key, value in data.items():
                if callable(value):
                    resolved[key] = value()
                elif isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    var_name = value[2:-1]
                    resolved[key] = session.get(var_name)
                else:
                    resolved[key] = value
            return resolved

        if isinstance(data, str):
            if data.startswith("${") and data.endswith("}"):
                return session.get(data[2:-1])
            return data.format(**session)

        return data


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> HTTPAction:
    """Create GET action.

    Example:
        >>> http_get("https://api.example.com/users")
        ...     .extract_json("data[0].id", "user_id")
    """
    config = HTTPConfig(
        method="GET",
        url=url,
        headers=headers or {},
        params=params or {},
    )
    return HTTPAction(config)


def http_post(
    url: str,
    json_data: Any = None,
    form_data: dict[str, Any] | None = None,
    text_data: str = "",
    headers: dict[str, str] | None = None,
) -> HTTPAction:
    """Create POST action.

    Example:
        >>> http_post(
        ...     "https://api.example.com/login",
        ...     json_data={"email": lambda: fake.email(), "password": "test"}
        ... )
    """
    config = HTTPConfig(
        method="POST",
        url=url,
        headers=(
            {**(headers or {}), "Content-Type": "application/json"}
            if json_data
            else (headers or {})
        ),
        json_data=json_data,
        form_data=form_data or {},
        text_data=text_data,
    )
    return HTTPAction(config)


def http_put(
    url: str,
    json_data: Any = None,
    headers: dict[str, str] | None = None,
) -> HTTPAction:
    """Create PUT action."""
    config = HTTPConfig(
        method="PUT",
        url=url,
        headers={**(headers or {}), "Content-Type": "application/json"},
        json_data=json_data,
    )
    return HTTPAction(config)


def http_patch(
    url: str,
    json_data: Any = None,
    headers: dict[str, str] | None = None,
) -> HTTPAction:
    """Create PATCH action."""
    config = HTTPConfig(
        method="PATCH",
        url=url,
        headers={**(headers or {}), "Content-Type": "application/json"},
        json_data=json_data,
    )
    return HTTPAction(config)


def http_delete(url: str, headers: dict[str, str] | None = None) -> HTTPAction:
    """Create DELETE action."""
    config = HTTPConfig(method="DELETE", url=url, headers=headers or {})
    return HTTPAction(config)


# ============================================================================
# Validators DSL
# ============================================================================


def status_2xx() -> Callable[[httpx.Response], bool]:
    """Validate 2xx status code."""

    def validator(response: httpx.Response) -> bool:
        return 200 <= response.status_code < 300

    validator.__name__ = "status_2xx"
    return validator


def status_code(code: int) -> Callable[[httpx.Response], bool]:
    """Validate specific status code.

    Example:
        >>> validate(status_code(201))  # Created
    """

    def validator(response: httpx.Response) -> bool:
        return response.status_code == code

    validator.__name__ = f"status_code_{code}"
    return validator


def status_in(codes: list[int]) -> Callable[[httpx.Response], bool]:
    """Validate status code is in list.

    Example:
        >>> validate(status_in([200, 201, 204]))
    """

    def validator(response: httpx.Response) -> bool:
        return response.status_code in codes

    validator.__name__ = f"status_in_{codes}"
    return validator


def json_path_equals(path: str, expected: Any) -> Callable[[httpx.Response], bool]:
    """Validate JSON path equals expected value.

    Example:
        >>> validate(json_path_equals("status", "success"))
    """

    def validator(response: httpx.Response) -> bool:
        try:
            data = response.json()
            keys = path.replace("[", ".").replace("]", "").split(".")
            value = data
            for key in keys:
                value = value[int(key)] if key.isdigit() else value[key]
            return value == expected
        except Exception:
            return False

    validator.__name__ = f"json_path_equals_{path}"
    return validator


def response_time_under(max_seconds: float) -> Callable[[httpx.Response], bool]:
    """Validate response time is under threshold."""

    def validator(response: httpx.Response) -> bool:
        return response.elapsed.total_seconds() < max_seconds

    validator.__name__ = f"response_time_under_{max_seconds}"
    return validator


def header_exists(header: str) -> Callable[[httpx.Response], bool]:
    """Validate header exists."""

    def validator(response: httpx.Response) -> bool:
        return header in response.headers

    validator.__name__ = f"header_exists_{header}"
    return validator


def content_type(content_type: str) -> Callable[[httpx.Response], bool]:
    """Validate Content-Type header."""

    def validator(response: httpx.Response) -> bool:
        ct = response.headers.get("content-type", "")
        return content_type in ct

    validator.__name__ = f"content_type_{content_type}"
    return validator


# ============================================================================
# Scenario DSL
# ============================================================================


@dataclass
class Step:
    """A scenario step."""

    name: str
    action: HTTPAction | Callable
    think_time: Callable[[], float] | None = None
    condition: Callable[[dict], bool] | None = None
    retries: int = 0


class ScenarioBuilder:
    """Builder for creating scenarios with the DSL.

    Example:
        >>> scenario = (
        ...     scenario("API Test")
        ...     .with_session()
        ...     .step("Create User", http_post("/users", json_data={"name": fake.full_name}))
        ...     .think_time(normal(1, 0.3))
        ...     .step("Get User", http_get("/users/${user_id}"))
        ...     .build()
        ... )
    """

    def __init__(self, name: str) -> None:
        """Initialize scenario builder.

        Args:
            name: Name of the scenario.
        """
        self.name = name
        self.steps: list[Step] = []
        self.default_think_time: Callable[[], float] | None = None
        self.use_session: bool = False
        self.session_vars: dict[str, Any] = {}
        self._setup: Callable | None = None
        self._teardown: Callable | None = None

    def with_session(self, persist: bool = True) -> ScenarioBuilder:
        """Enable session persistence across steps.

        Args:
            persist: Whether to persist session data between requests.

        Returns:
            Self for chaining.
        """
        self.use_session = persist
        return self

    def step(
        self,
        name: str,
        action: HTTPAction | Callable,
        think_time: Callable[[], float] | None = None,
        condition: Callable[[dict], bool] | None = None,
        retries: int = 0,
    ) -> ScenarioBuilder:
        """Add a step to the scenario.

        Args:
            name: Step name.
            action: HTTP action or callable to execute.
            think_time: Optional think time after this step.
            condition: Optional condition to execute this step.
            retries: Number of retries on failure.

        Returns:
            Self for chaining.
        """
        self.steps.append(Step(name, action, think_time, condition, retries))
        return self

    def think_time(self, think_fn: Callable[[], float]) -> ScenarioBuilder:
        """Set default think time for subsequent steps.

        Args:
            think_fn: Function returning think time in seconds.

        Returns:
            Self for chaining.
        """
        self.default_think_time = think_fn
        return self

    def setup(self, fn: Callable) -> ScenarioBuilder:
        """Set setup function.

        Args:
            fn: Function to run before scenario.

        Returns:
            Self for chaining.
        """
        self._setup = fn
        return self

    def teardown(self, fn: Callable) -> ScenarioBuilder:
        """Set teardown function.

        Args:
            fn: Function to run after scenario.

        Returns:
            Self for chaining.
        """
        self._teardown = fn
        return self

    def validate(self, validator: Callable[[httpx.Response], bool]) -> ScenarioBuilder:
        """Add a validator to the last step.

        Args:
            validator: Response validator function.

        Returns:
            Self for chaining.
        """
        if self.steps:
            last_step = self.steps[-1]
            if isinstance(last_step.action, HTTPAction):
                last_step.action.validate(validator)
        return self

    def build(self) -> DSLScenario:
        """Build the scenario.

        Returns:
            DSLScenario ready for execution.
        """
        return DSLScenario(
            name=self.name,
            steps=self.steps,
            default_think_time=self.default_think_time,
            use_session=self.use_session,
            setup=self._setup,
            teardown=self._teardown,
        )


class DSLScenario:
    """Executable scenario built with the DSL."""

    def __init__(
        self,
        name: str,
        steps: list[Step],
        default_think_time: Callable[[], float] | None = None,
        use_session: bool = False,
        setup: Callable | None = None,
        teardown: Callable | None = None,
    ) -> None:
        """Initialize DSL scenario.

        Args:
            name: Scenario name.
            steps: List of steps in the scenario.
            default_think_time: Default think time function.
            use_session: Whether to use session state.
            setup: Optional setup function.
            teardown: Optional teardown function.
        """
        self.name = name
        self.steps = steps
        self.default_think_time = default_think_time
        self.use_session = use_session
        self.setup = setup
        self.teardown = teardown
        self._client: httpx.AsyncClient | None = None

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the scenario.

        Args:
            context: Execution context.

        Returns:
            Results dictionary.
        """
        from loadtest.simulation import Session

        # Get or create session
        session = context.get("session")
        if session is None:
            session_data: dict[str, Any] = {}
        else:
            session_data = session.data if isinstance(session, Session) else {}

        # Create HTTP client if needed
        if self._client is None:
            self._client = httpx.AsyncClient()

        # Run setup
        if self.setup:
            await self._run_async(self.setup, session_data)

        results = []
        success = True

        try:
            for step in self.steps:
                # Check condition
                if step.condition and not step.condition(session_data):
                    continue

                step_result = {
                    "step": step.name,
                    "success": True,
                    "duration": 0.0,
                }

                start_time = asyncio.get_event_loop().time()

                try:
                    # Execute action
                    if isinstance(step.action, HTTPAction):
                        response = await step.action.execute(self._client, session_data)
                        step_result["status_code"] = response.status_code
                    else:
                        await self._run_async(step.action, session_data)

                    step_result["duration"] = asyncio.get_event_loop().time() - start_time

                    # Apply think time
                    think_fn = step.think_time or self.default_think_time
                    if think_fn:
                        await asyncio.sleep(max(0, think_fn()))

                except Exception as e:
                    step_result["success"] = False
                    step_result["error"] = str(e)
                    success = False

                    # Retry logic
                    if step.retries > 0:
                        for attempt in range(step.retries):
                            try:
                                if isinstance(step.action, HTTPAction):
                                    response = await step.action.execute(self._client, session_data)
                                    step_result["status_code"] = response.status_code
                                else:
                                    await self._run_async(step.action, session_data)
                                step_result["success"] = True
                                step_result["retries"] = attempt + 1
                                success = True
                                break
                            except Exception:
                                await asyncio.sleep(0.5 * (2**attempt))

                    if not step_result["success"]:
                        break

                results.append(step_result)

        finally:
            # Run teardown
            if self.teardown:
                await self._run_async(self.teardown, session_data)

        return {
            "scenario": self.name,
            "success": success,
            "steps": results,
            "session_data": session_data if self.use_session else {},
        }

    async def _run_async(self, fn: Callable, session_data: dict) -> Any:
        """Run a function that may be async."""
        import inspect

        if inspect.iscoroutinefunction(fn):
            return await fn(session_data)
        return fn(session_data)

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None


def scenario(name: str) -> ScenarioBuilder:
    """Start building a scenario.

    Args:
        name: Scenario name.

    Returns:
        ScenarioBuilder for chaining.

    Example:
        >>> scenario = (
        ...     scenario("User Login")
        ...     .step("Open login", http_get("/login"))
        ...     .step("Submit", http_post("/login", form_data={"user": fake.email}))
        ...     .build()
        ... )
    """
    return ScenarioBuilder(name)


# ============================================================================
# Load Pattern DSL
# ============================================================================


def constant_rate(rps: float) -> dict[str, Any]:
    """Constant rate load pattern.

    Example:
        >>> load_pattern = constant_rate(rps=100)
    """
    return {"type": "constant", "rps": rps}


def ramp_up(start_rps: float, end_rps: float, duration: float) -> dict[str, Any]:
    """Ramp up load pattern.

    Example:
        >>> load_pattern = ramp_up(start_rps=10, end_rps=100, duration=300)
    """
    return {"type": "ramp_up", "start_rps": start_rps, "end_rps": end_rps, "duration": duration}


def ramp_up_down(
    start_rps: float,
    peak_rps: float,
    ramp_up_duration: float,
    sustain_duration: float,
    ramp_down_duration: float,
) -> dict[str, Any]:
    """Ramp up, sustain, then ramp down.

    Example:
        >>> load_pattern = ramp_up_down(
        ...     start_rps=10, peak_rps=100,
        ...     ramp_up_duration=60, sustain_duration=120, ramp_down_duration=60
        ... )
    """
    return {
        "type": "ramp_up_down",
        "start_rps": start_rps,
        "peak_rps": peak_rps,
        "ramp_up_duration": ramp_up_duration,
        "sustain_duration": sustain_duration,
        "ramp_down_duration": ramp_down_duration,
    }


def spike(
    baseline_rps: float, spike_rps: float, spike_duration: float, interval: float
) -> dict[str, Any]:
    """Spike load pattern.

    Example:
        >>> load_pattern = spike(
        ...     baseline_rps=10, spike_rps=500, spike_duration=30, interval=300
        ... )
    """
    return {
        "type": "spike",
        "baseline_rps": baseline_rps,
        "spike_rps": spike_rps,
        "spike_duration": spike_duration,
        "interval": interval,
    }


# ============================================================================
# Test Definition DSL
# ============================================================================


@dataclass
class TestConfig:
    """Test configuration."""

    name: str = "Load Test"
    duration: float = 60.0
    warmup: float = 5.0
    max_concurrent: int = 1000


def test(name: str) -> TestConfig:
    """Create test configuration.

    Example:
        >>> config = test("API Load Test").with_duration(300).with_warmup(10)
    """
    return TestConfig(name=name)


# Add methods to TestConfig
TestConfig.with_duration = lambda self, d: setattr(self, "duration", d) or self
TestConfig.with_warmup = lambda self, w: setattr(self, "warmup", w) or self
TestConfig.with_max_concurrent = lambda self, m: setattr(self, "max_concurrent", m) or self
