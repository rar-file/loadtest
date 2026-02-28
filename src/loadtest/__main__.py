"""Entry point for running loadtest from the command line."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from loadtest import __version__

console = Console()


def load_config_module(config_path: str) -> Any:
    """Load a configuration module from a file path.
    
    Args:
        config_path: Path to the Python configuration file.
    
    Returns:
        The loaded module.
    
    Raises:
        FileNotFoundError: If the file doesn't exist.
        ImportError: If the module can't be loaded.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    spec = importlib.util.spec_from_file_location("config", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load configuration from: {config_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules["config"] = module
    spec.loader.exec_module(module)
    
    return module


def find_test_function(module: Any) -> Any:
    """Find the test creation function in a module.
    
    Looks for `create_test`, `main`, or `test` objects.
    
    Args:
        module: The loaded configuration module.
    
    Returns:
        The test function or object.
    
    Raises:
        AttributeError: If no test function is found.
    """
    if hasattr(module, "create_test"):
        return module.create_test
    if hasattr(module, "main"):
        return module.main
    if hasattr(module, "test"):
        return module.test
    
    raise AttributeError(
        "Configuration module must define 'create_test', 'main', or 'test'"
    )


def print_error(message: str, details: str = "") -> None:
    """Print a formatted error message.
    
    Args:
        message: Short error message.
        details: Additional error details.
    """
    console.print(Panel(
        f"[bold red]Error:[/bold red] {message}\n{details}",
        title="❌ LoadTest Error",
        border_style="red"
    ))


def print_success(message: str) -> None:
    """Print a formatted success message.
    
    Args:
        message: Success message to display.
    """
    console.print(f"[bold green]✓[/bold green] {message}")


def print_info(message: str) -> None:
    """Print an info message.
    
    Args:
        message: Info message to display.
    """
    console.print(f"[blue]ℹ[/blue] {message}")


async def run_test(config_path: str, output: str | None = None, duration: float | None = None) -> int:
    """Run a load test from a configuration file.
    
    Args:
        config_path: Path to the configuration file.
        output: Optional output path for the report.
        duration: Optional duration override.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        print_info(f"Loading configuration from {config_path}...")
        module = load_config_module(config_path)
        test_obj = find_test_function(module)
        
        # Handle different types of test objects
        if callable(test_obj) and not hasattr(test_obj, 'run'):
            # It's a function, call it to get the test
            if asyncio.iscoroutinefunction(test_obj):
                test = await test_obj()
            else:
                test = test_obj()
        else:
            test = test_obj
        
        # Apply duration override if specified
        if duration is not None and hasattr(test, 'config'):
            test.config.duration = duration
        
        # Run the test
        print_info(f"Starting test: {getattr(test, 'config', {}).get('name', 'Load Test') if hasattr(test, 'config') else 'Load Test'}")
        
        from loadtest.core import LoadTest
        
        if isinstance(test, LoadTest):
            results = await test.run()
            
            # Print console report
            console.print()
            console.print(test.report(format="console"))
            
            # Generate HTML report if requested
            if output:
                test.report(format="html", output=output)
                print_success(f"HTML report saved to: {output}")
            
            return 0 if results.success_rate >= 95 else 1
        else:
            # Assume the test object has a run method
            if hasattr(test, 'run'):
                if asyncio.iscoroutinefunction(test.run):
                    await test.run()
                else:
                    test.run()
            print_success("Test completed successfully")
            return 0
            
    except FileNotFoundError as e:
        print_error(str(e), "Please check that the file path is correct.")
        return 1
    except ImportError as e:
        print_error(f"Failed to import configuration: {e}", 
                   "Make sure all required dependencies are installed.")
        return 1
    except AttributeError as e:
        print_error(str(e),
                   "Your configuration file should define a 'create_test()' or 'main()' function\n"
                   "that returns a LoadTest object, or define a 'test' variable.")
        return 1
    except Exception as e:
        print_error(f"Test execution failed: {e}")
        import traceback
        console.print(traceback.format_exc())
        return 1


def show_version() -> None:
    """Display version information."""
    console.print(Panel(
        f"[bold]LoadTest[/bold] version [cyan]{__version__}[/cyan]\n"
        "Synthetic traffic generator for load testing",
        title="📊 LoadTest",
        border_style="cyan"
    ))


def show_info() -> None:
    """Display information about available components."""
    table = Table(title="Available LoadTest Components")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", no_wrap=True)
    table.add_column("Description", style="white")
    
    # Scenarios
    table.add_row("Scenario", "HTTPScenario", "HTTP/HTTPS request scenarios with async support")
    table.add_row("Scenario", "AuthenticatedHTTPScenario", "HTTP with Bearer/API key authentication")
    table.add_row("Scenario", "WebScenario", "Browser automation with Playwright (requires [web] extra)")
    table.add_row("Scenario", "Scenario", "Base class for custom scenarios")
    
    # Generators
    table.add_row("Generator", "ConstantRateGenerator", "Steady, unchanging request rate")
    table.add_row("Generator", "VariableRateGenerator", "Variable traffic with wave patterns")
    table.add_row("Generator", "RampGenerator", "Gradually increase or decrease load")
    table.add_row("Generator", "SpikeGenerator", "Sudden traffic spikes")
    table.add_row("Generator", "BurstGenerator", "Single isolated burst patterns")
    
    # Patterns (new API)
    table.add_row("Pattern", "TrafficPattern", "Abstract base for custom patterns")
    table.add_row("Pattern", "SteadyStateGenerator", "Steady rate with optional jitter")
    table.add_row("Pattern", "StepLadderGenerator", "Step-wise load increase/decrease")
    table.add_row("Pattern", "ChaosGenerator", "Random/unpredictable traffic")
    table.add_row("Pattern", "CompositePattern", "Combine multiple patterns")
    
    console.print(table)
    console.print("\n[dim]For more information, visit: https://github.com/example/loadtest[/dim]")


def show_quickstart() -> None:
    """Display quick start guide."""
    guide = """
[bold cyan]Quick Start Guide[/bold cyan]

1. [bold]Create a test file[/bold] (test.py):

   from loadtest import LoadTest
   from loadtest.generators.constant import ConstantRateGenerator
   from loadtest.scenarios.http import HTTPScenario

   async def create_test():
       scenario = HTTPScenario(
           method="GET",
           url="https://api.example.com/users"
       )
       return (
           LoadTest(name="API Test", duration=60)
           .add_scenario(scenario)
           .set_pattern(ConstantRateGenerator(rate=10))
       )

2. [bold]Run the test[/bold]:

   $ loadtest run test.py

3. [bold]Generate HTML report[/bold]:

   $ loadtest run test.py --output report.html

[bold cyan]Configuration Tips[/bold cyan]

• Use [cyan]create_test()[/cyan] or [cyan]main()[/cyan] async function that returns a LoadTest
• Or define a [cyan]test[/cyan] variable with your LoadTest instance
• Set [cyan]console_output=False[/cyan] for CI/CD environments
• Use [cyan]duration[/cyan] in seconds to control test length

[bold cyan]Examples[/bold cyan]

See the [cyan]examples/[/cyan] directory for more sample configurations:
• quickstart.py - Simple HTTP load test
• simple_http_load.py - Complete example with POST data
• api_load_test.py - API testing patterns
    """
    console.print(Panel(guide, title="🚀 Getting Started", border_style="green"))


def main(args: list[str] | None = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:]).
    
    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="loadtest",
        description="Synthetic traffic generator for load testing web applications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  loadtest run test.py                    # Run a test from Python file
  loadtest run test.py -o report.html     # Generate HTML report
  loadtest run test.py -d 120             # Override duration to 120 seconds
  loadtest quickstart                     # Show quick start guide
  loadtest info                           # Show available components
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser(
        "run", 
        help="Run a load test from configuration file",
        description="Execute a load test defined in a Python, JSON, or YAML file."
    )
    run_parser.add_argument(
        "config",
        metavar="FILE",
        help="Path to test configuration file (.py, .json, or .yaml)",
    )
    run_parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help="Output file path for HTML report",
    )
    run_parser.add_argument(
        "-d", "--duration",
        type=float,
        metavar="SECONDS",
        help="Override test duration (in seconds)",
    )
    
    # Version command
    subparsers.add_parser("version", help="Show version information")
    
    # Info command
    subparsers.add_parser("info", help="Show available components")
    
    # Quickstart command
    subparsers.add_parser("quickstart", help="Show quick start guide")
    
    parsed = parser.parse_args(args)
    
    if parsed.command == "run":
        try:
            return asyncio.run(run_test(parsed.config, parsed.output, parsed.duration))
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠ Test interrupted by user[/yellow]")
            return 130
    elif parsed.command == "version":
        show_version()
        return 0
    elif parsed.command == "info":
        show_info()
        return 0
    elif parsed.command == "quickstart":
        show_quickstart()
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
