"""Entry point for running loadtest from the command line."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

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
    
    Looks for `create_test` or `main` functions.
    
    Args:
        module: The loaded configuration module.
    
    Returns:
        The test function.
    
    Raises:
        AttributeError: If no test function is found.
    """
    if hasattr(module, "create_test"):
        return module.create_test
    if hasattr(module, "main"):
        return module.main
    
    raise AttributeError(
        "Configuration module must define 'create_test' or 'main' function"
    )


async def run_test(config_path: str, output: str | None = None) -> int:
    """Run a load test from a configuration file.
    
    Args:
        config_path: Path to the configuration file.
        output: Optional output path for the report.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    try:
        console.print(f"[blue]Loading configuration from {config_path}...[/blue]")
        module = load_config_module(config_path)
        test_func = find_test_function(module)
        
        # Run the test function
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()
        
        # Handle different return types
        from loadtest.core import LoadTest
        
        if isinstance(result, LoadTest):
            test = result
            results = await test.run()
            
            # Print console report
            console.print()
            console.print(test.report(format="console"))
            
            # Generate HTML report if requested
            if output:
                test.report(format="html", output=output)
                console.print(f"\n[green]HTML report saved to: {output}[/green]")
            
            return 0 if results.success_rate >= 95 else 1
        else:
            # Assume the function ran the test itself
            console.print("[green]Test completed successfully[/green]")
            return 0
            
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1
    except ImportError as e:
        console.print(f"[red]Error loading configuration: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Test failed: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return 1


def show_version() -> None:
    """Display version information."""
    from loadtest import __version__
    console.print(f"loadtest version {__version__}")


def show_info() -> None:
    """Display information about available components."""
    table = Table(title="LoadTest Components")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    
    # Scenarios
    table.add_row("Scenario", "HTTPScenario", "HTTP request scenarios")
    table.add_row("Scenario", "WebScenario", "Browser automation with Playwright")
    table.add_row("Scenario", "Scenario", "Base class for custom scenarios")
    
    # Generators
    table.add_row("Generator", "ConstantRateGenerator", "Constant traffic rate")
    table.add_row("Generator", "VariableRateGenerator", "Variable traffic patterns")
    table.add_row("Generator", "RampGenerator", "Ramp up/down traffic")
    table.add_row("Generator", "SpikeGenerator", "Spike traffic patterns")
    table.add_row("Generator", "BurstGenerator", "Single burst traffic")
    
    console.print(table)


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
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a load test")
    run_parser.add_argument(
        "config",
        help="Path to the test configuration file",
    )
    run_parser.add_argument(
        "-o", "--output",
        help="Output file for HTML report",
    )
    run_parser.add_argument(
        "-d", "--duration",
        type=float,
        help="Override test duration in seconds",
    )
    
    # Version command
    subparsers.add_parser("version", help="Show version information")
    
    # Info command
    subparsers.add_parser("info", help="Show available components")
    
    parsed = parser.parse_args(args)
    
    if parsed.command == "run":
        return asyncio.run(run_test(parsed.config, parsed.output))
    elif parsed.command == "version":
        show_version()
        return 0
    elif parsed.command == "info":
        show_info()
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
