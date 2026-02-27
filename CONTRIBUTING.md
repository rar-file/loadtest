# Contributing to LoadTest

Thank you for your interest in contributing to LoadTest! We welcome contributions from the community and are excited to have you join us.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- A GitHub account

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/loadtest.git
   cd loadtest
   ```

3. **Set up the upstream remote**:
   ```bash
   git remote add upstream https://github.com/original/loadtest.git
   ```

4. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install development dependencies**:
   ```bash
   pip install -e ".[dev,web]"
   ```

6. **Install Playwright browsers** (for web testing):
   ```bash
   playwright install chromium
   ```

7. **Verify your setup**:
   ```bash
   pytest
   ```

## Development Workflow

### Branching Strategy

We follow a simplified GitFlow workflow:

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Urgent production fixes

### Making Changes

1. **Create a new branch** from `develop`:
   ```bash
   git checkout develop
   git pull upstream develop
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Run tests and linting**:
   ```bash
   # Run tests
   pytest

   # Run linting
   black src tests
   ruff check src tests
   mypy src
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

## Project Structure

```
loadtest/
├── src/loadtest/           # Main source code
│   ├── __init__.py
│   ├── core.py            # Main LoadTest class
│   ├── runner.py          # Test runner
│   ├── scenarios/         # Scenario implementations
│   │   ├── base.py
│   │   ├── http.py
│   │   └── web.py
│   ├── generators/        # Traffic generators
│   │   ├── constant.py
│   │   ├── ramp.py
│   │   └── spike.py
│   ├── metrics/           # Metrics collection
│   └── reports/           # Report generators
├── tests/                 # Test suite
├── examples/              # Usage examples
├── docs/                  # Documentation
├── benchmarks/            # Performance benchmarks
├── .github/workflows/     # CI/CD configuration
├── pyproject.toml         # Project configuration
└── README.md
```

## Coding Standards

### Python Style

We use:
- **Black** for code formatting (line length: 100)
- **Ruff** for linting
- **MyPy** for type checking

### Code Style Guidelines

1. **Follow PEP 8** with Black formatting
2. **Use type hints** for all function signatures
3. **Write docstrings** for all public APIs using Google style
4. **Use async/await** properly for async code
5. **Use descriptive variable names**

### Example Async Function

```python
from typing import Dict, Any
import asyncio

async def execute_scenario(
    scenario: Scenario,
    context: Dict[str, Any],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Execute a load test scenario with timeout.
    
    Args:
        scenario: The scenario to execute.
        context: Execution context with shared resources.
        timeout: Maximum execution time in seconds.
    
    Returns:
        Dictionary with execution results.
    
    Raises:
        asyncio.TimeoutError: If execution exceeds timeout.
        ScenarioError: If scenario execution fails.
    
    Example:
        >>> result = await execute_scenario(scenario, context)
        >>> print(result['status'])
        'success'
    """
    try:
        return await asyncio.wait_for(
            scenario.execute(context),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"Scenario timed out after {timeout}s")
```

## Testing Guidelines

### Test Structure

- Tests are in the `tests/` directory
- Mirror the source structure
- Use `pytest` as the test runner
- Use `pytest-asyncio` for async tests

### Writing Tests

```python
import pytest
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario

class TestLoadTest:
    """Test cases for the LoadTest class."""
    
    @pytest.mark.asyncio
    async def test_add_scenario(self):
        """Test adding scenarios to load test."""
        test = LoadTest(name="Test")
        scenario = HTTPScenario(name="Test", method="GET", url="http://test.com")
        
        test.add_scenario(scenario, weight=1)
        
        assert len(test.scenarios) == 1
        assert test.scenarios[0][0].name == "Test"
    
    @pytest.mark.asyncio
    async def test_run_requires_scenarios(self):
        """Test that run requires at least one scenario."""
        test = LoadTest(name="Test")
        
        with pytest.raises(RuntimeError, match="No scenarios"):
            await test.run()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=loadtest

# Run specific test file
pytest tests/test_core.py

# Run with verbose output
pytest -v

# Run only web tests (requires playwright)
pytest -m web

# Run excluding slow tests
pytest -m "not slow"

# Run async tests specifically
pytest -m asyncio
```

## Documentation

### Code Documentation

- All public functions, classes, and modules must have docstrings
- Use Google-style docstrings
- Include type hints
- Provide usage examples where helpful

### Documentation Files

- Update `README.md` if adding major features
- Add examples to `examples/` directory
- Update API docs in `docs/api/`

### Building Documentation

```bash
# Install docs dependencies
pip install mkdocs mkdocs-material mkdocstrings[python]

# Serve docs locally
mkdocs serve

# Build docs
mkdocs build
```

## Submitting Changes

### Pull Request Process

1. **Update the README.md** with details of changes if applicable
2. **Update documentation** for any API changes
3. **Add tests** for new functionality
4. **Ensure all tests pass**
5. **Update the CHANGELOG.md** with your changes
6. **Link any related issues** in the PR description

### PR Checklist

- [ ] Code follows the style guidelines
- [ ] Self-review of code completed
- [ ] Code is commented, particularly in hard-to-understand areas
- [ ] Corresponding documentation changes made
- [ ] Tests added that prove the fix is effective or feature works
- [ ] New and existing unit tests pass locally
- [ ] Dependent changes have been merged and published

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body (optional)

footer (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test-related changes
- `chore`: Build/tooling changes

Examples:
```
feat(generator): add burst traffic pattern

fix(http): handle connection pool exhaustion

docs: update API reference for scenarios
```

## Performance Considerations

When contributing, please consider:

1. **Async Efficiency**: Use proper async patterns, avoid blocking calls
2. **Memory Usage**: Large load tests can consume significant memory
3. **CPU Usage**: Profile CPU-intensive operations
4. **Network Efficiency**: Reuse connections where possible

### Benchmarking

Run benchmarks before and after changes:

```bash
# Run benchmarks
python -m pytest benchmarks/ --benchmark-only

# Compare with previous run
python -m pytest benchmarks/ --benchmark-compare
```

## Release Process

1. **Update version** in `src/loadtest/__version__.py`
2. **Update CHANGELOG.md** with release notes
3. **Create a tag**: `git tag -a v1.0.0 -m "Release version 1.0.0"`
4. **Push the tag**: `git push origin v1.0.0`
5. **GitHub Actions** will automatically build and publish

## Getting Help

- **GitHub Discussions**: For questions and ideas
- **GitHub Issues**: For bug reports and feature requests
- **Discord**: [Join our community](https://discord.gg/example)

## Recognition

Contributors will be recognized in our README.md and release notes.

Thank you for contributing to LoadTest!
