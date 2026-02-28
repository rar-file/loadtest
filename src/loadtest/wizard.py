"""Interactive CLI wizard for loadtest.

Usage:
    loadtest wizard    # Start interactive wizard
    loadtest init      # Create config file interactively
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.syntax import Syntax

console = Console()


def print_welcome() -> None:
    """Print welcome message."""
    console.print(Panel.fit(
        "[bold cyan]LoadTest Wizard[/bold cyan]\n"
        "Create your load test in under a minute! 🚀",
        title="Welcome",
        border_style="cyan"
    ))


def wizard() -> dict[str, Any]:
    """Run the interactive wizard.
    
    Returns:
        Configuration dictionary
    """
    print_welcome()
    
    config: dict[str, Any] = {}
    
    # Step 1: Target URL
    console.print("\n[bold]Step 1: Target Configuration[/bold]")
    config["target"] = Prompt.ask(
        "Target URL",
        default="https://httpbin.org",
        show_default=True
    )
    
    # Step 2: Endpoints
    console.print("\n[bold]Step 2: Endpoints to Test[/bold]")
    endpoints = []
    
    while True:
        console.print(f"\n[dim]Endpoint #{len(endpoints) + 1}[/dim]")
        
        method = Prompt.ask(
            "  HTTP Method",
            choices=["GET", "POST", "PUT", "DELETE", "PATCH"],
            default="GET"
        )
        
        path = Prompt.ask("  Path", default="/")
        
        weight = IntPrompt.ask(
            "  Weight (frequency relative to other endpoints)",
            default=1
        )
        
        endpoint = {"method": method, "path": path, "weight": weight}
        
        # Optional: JSON body for POST/PUT
        if method in ("POST", "PUT", "PATCH"):
            has_body = Confirm.ask("  Add JSON body?", default=False)
            if has_body:
                body_str = Prompt.ask("  JSON body (e.g., {\"key\": \"value\"})")
                try:
                    endpoint["json"] = json.loads(body_str)
                except json.JSONDecodeError:
                    console.print("[yellow]  Invalid JSON, skipping body[/yellow]")
        
        endpoints.append(endpoint)
        
        if not Confirm.ask("\nAdd another endpoint?", default=False):
            break
    
    config["endpoints"] = endpoints
    
    # Step 3: Traffic Pattern
    console.print("\n[bold]Step 3: Traffic Pattern[/bold]")
    
    pattern = Prompt.ask(
        "Pattern type",
        choices=["constant", "ramp", "spike", "burst"],
        default="constant"
    )
    config["pattern"] = pattern
    
    # Pattern-specific options
    if pattern == "constant":
        config["rps"] = FloatPrompt.ask(
            "Requests per second",
            default=10.0
        )
    
    elif pattern == "ramp":
        config["rps"] = FloatPrompt.ask(
            "Starting RPS",
            default=10.0
        )
        config["target_rps"] = FloatPrompt.ask(
            "Target RPS (end of ramp)",
            default=100.0
        )
    
    elif pattern == "spike":
        config["rps"] = FloatPrompt.ask(
            "Base RPS",
            default=10.0
        )
        config["peak_rps"] = FloatPrompt.ask(
            "Peak RPS during spike",
            default=500.0
        )
        config["spike_duration"] = FloatPrompt.ask(
            "Spike duration (seconds)",
            default=10.0
        )
    
    elif pattern == "burst":
        config["rps"] = FloatPrompt.ask(
            "Initial RPS",
            default=10.0
        )
        config["burst_rps"] = FloatPrompt.ask(
            "Burst RPS",
            default=1000.0
        )
        config["burst_duration"] = FloatPrompt.ask(
            "Burst duration (seconds)",
            default=30.0
        )
        config["delay"] = FloatPrompt.ask(
            "Delay before burst (seconds)",
            default=30.0
        )
    
    # Step 4: Duration
    console.print("\n[bold]Step 4: Test Duration[/bold]")
    config["duration"] = FloatPrompt.ask(
        "Test duration (seconds)",
        default=60.0
    )
    
    # Step 5: Headers (optional)
    console.print("\n[bold]Step 5: Headers (Optional)[/bold]")
    config["headers"] = {}
    
    if Confirm.ask("Add custom headers?", default=False):
        while True:
            key = Prompt.ask("Header name (or empty to finish)")
            if not key:
                break
            value = Prompt.ask(f"Value for {key}")
            config["headers"][key] = value
    
    # Summary
    print_summary(config)
    
    return config


def print_summary(config: dict[str, Any]) -> None:
    """Print configuration summary."""
    console.print("\n[bold green]Configuration Summary:[/bold green]")
    console.print(f"  Target: [cyan]{config['target']}[/cyan]")
    console.print(f"  Pattern: [cyan]{config['pattern']}[/cyan]")
    console.print(f"  Duration: [cyan]{config['duration']}s[/cyan]")
    
    if config['pattern'] == 'constant':
        console.print(f"  RPS: [cyan]{config['rps']}[/cyan]")
    elif config['pattern'] == 'ramp':
        console.print(f"  RPS: [cyan]{config['rps']} → {config['target_rps']}[/cyan]")
    
    console.print(f"  Endpoints: [cyan]{len(config['endpoints'])}[/cyan]")
    for ep in config['endpoints']:
        console.print(f"    - {ep['method']} {ep['path']} (weight: {ep['weight']})")
    
    if config.get('headers'):
        console.print(f"  Headers: [cyan]{len(config['headers'])} custom[/cyan]")


def generate_python_code(config: dict[str, Any]) -> str:
    """Generate Python code from configuration.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Python code string
    """
    lines = [
        "from loadtest import loadtest",
        "",
        "# Create load test",
        f"test = loadtest(",
        f'    target="{config["target"]}",',
        f'    pattern="{config["pattern"]}",',
    ]
    
    # Add pattern-specific params
    if config["pattern"] == "constant":
        lines.append(f'    rps={config["rps"]},')
    elif config["pattern"] == "ramp":
        lines.append(f'    rps={config["rps"]},')
        lines.append(f'    target_rps={config["target_rps"]},')
    elif config["pattern"] == "spike":
        lines.append(f'    rps={config["rps"]},')
        lines.append(f'    peak_rps={config["peak_rps"]},')
        lines.append(f'    spike_duration={config["spike_duration"]},')
    elif config["pattern"] == "burst":
        lines.append(f'    rps={config["rps"]},')
        lines.append(f'    burst_rps={config["burst_rps"]},')
        lines.append(f'    burst_duration={config["burst_duration"]},')
        lines.append(f'    delay={config["delay"]},')
    
    lines.append(f'    duration={config["duration"]},')
    lines.append(")")
    lines.append("")
    
    # Add endpoints
    for ep in config["endpoints"]:
        args = [f'"{ep["method"]} {ep["path"]}"']
        if ep["weight"] != 1:
            args.append(f'weight={ep["weight"]}')
        if ep.get("json"):
            args.append(f'json={json.dumps(ep["json"])}')
        
        lines.append(f"test.add({', '.join(args)})")
    
    # Add headers if present
    if config.get("headers"):
        lines.append("")
        lines.append("# Set headers")
        for key, value in config["headers"].items():
            lines.append(f'test.headers({{"{key}": "{value}"}})')
    
    lines.append("")
    lines.append("# Run the test")
    lines.append("if __name__ == \"__main__\":")
    lines.append("    test.run()")
    
    return "\n".join(lines)


def generate_config_file(config: dict[str, Any], path: str = "loadtest.json") -> None:
    """Generate a JSON config file.
    
    Args:
        config: Configuration dictionary
        path: Output file path
    """
    with open(path, "w") as f:
        json.dump(config, f, indent=2)
    console.print(f"\n[green]✓ Config saved to {path}[/green]")


def init_command() -> int:
    """Run the init command to create a config file.
    
    Returns:
        Exit code
    """
    config = wizard()
    
    console.print("\n[bold]What would you like to create?[/bold]")
    choices = [
        "Python script (loadtest.py)",
        "JSON config (loadtest.json)",
        "Both"
    ]
    
    for i, choice in enumerate(choices, 1):
        console.print(f"  {i}. {choice}")
    
    choice = IntPrompt.ask("Select", default=1)
    
    if choice in (1, 3):
        py_file = "loadtest.py"
        code = generate_python_code(config)
        with open(py_file, "w") as f:
            f.write(code)
        console.print(f"[green]✓ Python script saved to {py_file}[/green]")
        
        # Show the code
        console.print("\n[dim]Generated code:[/dim]")
        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
        console.print(syntax)
    
    if choice in (2, 3):
        generate_config_file(config, "loadtest.json")
    
    console.print(Panel.fit(
        "[bold green]You're all set![/bold green]\n\n"
        "Run your test with:\n"
        "  [cyan]python loadtest.py[/cyan]\n\n"
        "Or using the CLI:\n"
        "  [cyan]loadtest run loadtest.py[/cyan]",
        title="Next Steps",
        border_style="green"
    ))
    
    return 0


def run_wizard() -> int:
    """Run the wizard and optionally execute the test.
    
    Returns:
        Exit code
    """
    config = wizard()
    
    # Ask if they want to run now or save
    console.print("\n[bold]What next?[/bold]")
    action = Prompt.ask(
        "Choose action",
        choices=["run", "save", "both"],
        default="run"
    )
    
    if action in ("save", "both"):
        filename = Prompt.ask(
            "Filename",
            default="loadtest.py"
        )
        code = generate_python_code(config)
        with open(filename, "w") as f:
            f.write(code)
        console.print(f"[green]✓ Saved to {filename}[/green]")
    
    if action in ("run", "both"):
        console.print("\n[bold]Starting load test...[/bold]")
        
        # Build and run the test
        from loadtest import loadtest
        
        test = loadtest(
            target=config["target"],
            pattern=config["pattern"],
            duration=config["duration"],
            **{k: v for k, v in config.items() if k not in ("target", "pattern", "duration", "endpoints", "headers")}
        )
        
        for ep in config["endpoints"]:
            test.add(
                f"{ep['method']} {ep['path']}",
                weight=ep.get("weight", 1),
                json=ep.get("json")
            )
        
        if config.get("headers"):
            test.headers(config["headers"])
        
        try:
            test.run()
        except KeyboardInterrupt:
            console.print("\n[yellow]Test interrupted[/yellow]")
            return 130
    
    return 0


if __name__ == "__main__":
    run_wizard()
