"""Browser automation scenarios using Playwright.

This module provides WebScenario for simulating real user interactions
in a browser using Playwright. This allows for testing full user flows
including JavaScript-heavy applications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loadtest.scenarios.base import Scenario

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page


class WebScenario(Scenario):
    """Base class for browser automation scenarios.
    
    This scenario type uses Playwright to control a real browser,
    allowing you to test full user flows including:
    - Page navigation
    - Form filling and submission
    - Button clicks
    - JavaScript execution
    - Screenshot capture
    
    Subclasses should override the `execute` method to define
    the specific user flow.
    
    Attributes:
        browser_type: Browser to use ('chromium', 'firefox', 'webkit').
        headless: Whether to run browser in headless mode.
        viewport: Browser viewport size as (width, height).
        timeout: Default timeout for actions in milliseconds.
    
    Example:
        >>> class LoginScenario(WebScenario):
        ...     async def execute(self, context):
        ...         page = context["page"]
        ...         await page.goto("https://example.com/login")
        ...         await page.fill("#username", self.phoney.email())
        ...         await page.fill("#password", "password123")
        ...         await page.click("#login")
    """
    
    def __init__(
        self,
        name: str | None = None,
        browser_type: str = "chromium",
        headless: bool = True,
        viewport: tuple[int, int] | None = None,
        timeout: int = 30000,
    ) -> None:
        """Initialize a web scenario.
        
        Args:
            name: Scenario name.
            browser_type: Browser type ('chromium', 'firefox', 'webkit').
            headless: Run browser in headless mode.
            viewport: Viewport size as (width, height).
            timeout: Default timeout for actions in milliseconds.
        """
        super().__init__(name)
        self.browser_type = browser_type
        self.headless = headless
        self.viewport = viewport or (1280, 720)
        self.timeout = timeout
        
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
    
    async def setup(self) -> dict[str, Any]:
        """Set up the browser and context.
        
        Returns:
            Context dictionary with 'page' and other browser resources.
        """
        from playwright.async_api import async_playwright
        
        self._playwright = await async_playwright().start()
        
        browser_launcher = getattr(self._playwright, self.browser_type)
        self._browser = await browser_launcher.launch(headless=self.headless)
        
        self._context = await self._browser.new_context(
            viewport={"width": self.viewport[0], "height": self.viewport[1]},
        )
        
        page = await self._context.new_page()
        page.set_default_timeout(self.timeout)
        
        return {
            "page": page,
            "context": self._context,
            "browser": self._browser,
            "playwright": self._playwright,
        }
    
    async def teardown(self) -> None:
        """Clean up browser resources."""
        if self._context:
            await self._context.close()
            self._context = None
        
        if self._browser:
            await self._browser.close()
            self._browser = None
        
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
    
    async def execute(self, context: dict[str, Any]) -> Any:
        """Execute the web scenario.
        
        Subclasses must override this method to define the actual
        browser automation flow.
        
        Args:
            context: Execution context containing browser resources.
                    Contains 'page', 'context', 'browser', 'playwright'.
        
        Returns:
            Result of the scenario execution.
            
        Raises:
            NotImplementedError: If not overridden by subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the execute method"
        )
    
    async def run(self) -> Any:
        """Run the scenario with setup and teardown.
        
        This is a convenience method that handles browser lifecycle.
        
        Returns:
            Result of the scenario execution.
        """
        context = {}
        try:
            browser_context = await self.setup()
            context.update(browser_context)
            return await self.execute(context)
        finally:
            await self.teardown()


class WebSessionScenario(WebScenario):
    """Web scenario that maintains session across executions.
    
    Unlike WebScenario which creates a new browser context for each
    execution, this class maintains the browser context, allowing
    scenarios to share state like cookies and localStorage.
    
    This is useful for testing multi-step user flows where the user
    needs to remain logged in across multiple actions.
    
    Example:
        >>> class ShoppingFlow(WebSessionScenario):
        ...     async def execute(self, context):
        ...         page = context["page"]
        ...         # First call: login
        ...         if not context.get("logged_in"):
        ...             await page.goto("/login")
        ...             # ... login logic
        ...             context["logged_in"] = True
        ...         else:
        ...             # Already logged in, proceed with action
        ...             await page.goto("/cart")
    """
    
    def __init__(
        self,
        name: str | None = None,
        browser_type: str = "chromium",
        headless: bool = True,
        viewport: tuple[int, int] | None = None,
        timeout: int = 30000,
    ) -> None:
        """Initialize a web session scenario.
        
        Args:
            name: Scenario name.
            browser_type: Browser type.
            headless: Run in headless mode.
            viewport: Viewport size.
            timeout: Default timeout.
        """
        super().__init__(name, browser_type, headless, viewport, timeout)
        self._session_context: dict[str, Any] = {}
    
    async def run(self) -> Any:
        """Run the scenario, maintaining session state.
        
        Returns:
            Result of the scenario execution.
        """
        # Initialize browser on first run
        if self._browser is None:
            browser_context = await self.setup()
            self._session_context.update(browser_context)
        
        try:
            return await self.execute(self._session_context)
        except Exception:
            # Reset session on error
            await self.teardown()
            raise
    
    async def reset_session(self) -> None:
        """Reset the browser session."""
        await self.teardown()
        self._session_context.clear()


class PageActionMixin:
    """Mixin providing common page actions for web scenarios.
    
    This mixin provides helper methods for common browser actions
    that use Phoney data for realistic input.
    
    Use this by mixing into your WebScenario subclass.
    
    Example:
        >>> class MyScenario(PageActionMixin, WebScenario):
        ...     async def execute(self, context):
        ...         page = context["page"]
        ...         await self.fill_form(page, {
        ...             "#name": self.phoney.full_name(),
        ...             "#email": self.phoney.email(),
        ...         })
    """
    
    async def fill_form(
        self,
        page: Page,
        fields: dict[str, str],
        submit_selector: str | None = None,
    ) -> None:
        """Fill a form with data.
        
        Args:
            page: Playwright page instance.
            fields: Dictionary mapping selectors to values.
            submit_selector: Optional selector for submit button.
        """
        for selector, value in fields.items():
            await page.fill(selector, value)
        
        if submit_selector:
            await page.click(submit_selector)
    
    async def fill_registration_form(
        self,
        page: Page,
        name_selector: str = "#name",
        email_selector: str = "#email",
        password_selector: str = "#password",
        submit_selector: str | None = "#submit",
    ) -> dict[str, str]:
        """Fill a registration form with Phoney-generated data.
        
        Args:
            page: Playwright page instance.
            name_selector: Selector for name field.
            email_selector: Selector for email field.
            password_selector: Selector for password field.
            submit_selector: Optional submit button selector.
        
        Returns:
            Dictionary with the generated user data.
        """
        # Need access to phoney - this assumes the class also inherits from Scenario
        if not hasattr(self, "phoney"):
            raise RuntimeError("PageActionMixin must be used with a Scenario subclass")
        
        user_data = {
            "name": self.phoney.full_name(),
            "email": self.phoney.email(),
            "password": self.phoney.password(length=12),
        }
        
        await page.fill(name_selector, user_data["name"])
        await page.fill(email_selector, user_data["email"])
        await page.fill(password_selector, user_data["password"])
        
        if submit_selector:
            await page.click(submit_selector)
        
        return user_data
    
    async def safe_click(self, page: Page, selector: str, timeout: int = 5000) -> bool:
        """Attempt to click an element, returning success status.
        
        Args:
            page: Playwright page instance.
            selector: Element selector.
            timeout: Timeout in milliseconds.
        
        Returns:
            True if click succeeded, False otherwise.
        """
        try:
            await page.click(selector, timeout=timeout)
            return True
        except Exception:  # noqa: BLE001
            return False
    
    async def wait_for_navigation(
        self,
        page: Page,
        url_pattern: str | None = None,
        timeout: int = 10000,
    ) -> bool:
        """Wait for page navigation to complete.
        
        Args:
            page: Playwright page instance.
            url_pattern: Optional URL pattern to wait for.
            timeout: Timeout in milliseconds.
        
        Returns:
            True if navigation completed, False on timeout.
        """
        try:
            if url_pattern:
                await page.wait_for_url(url_pattern, timeout=timeout)
            else:
                await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception:  # noqa: BLE001
            return False
