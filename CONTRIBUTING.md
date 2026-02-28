# Contributing to LoadTest

Thank you for your interest in contributing to LoadTest! This document provides guidelines and information for contributors.

## Getting Started

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/loadtest.git
   cd loadtest
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/loadtest --cov-report=html

# Run specific test file
pytest tests/test_core.py -v

# Run with debug output
pytest -v --tb=long
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
black src/ tests/

# Lint with ruff
ruff check src/ tests/

# Type checking
mypy src/

# Security check
bandit -c pyproject.toml -r src/

# Run all pre-commit hooks
pre-commit run --all-files
```

## Project Structure

```
loadtest/
├── src/loadtest/          # Main source code
│   ├── __init__.py        # Package exports
│   ├── __main__.py        # CLI entry point
│   ├── __version__.py     # Version info
│   ├── core.py            # Core LoadTest class
│   ├── runner.py          # Test execution engine
│   ├── patterns.py        # Traffic patterns
│   ├── scenarios/         # Test scenarios
│   ├── generators/        # Traffic generators
│   ├── reports/           # Report generators
│   └── metrics/           # Metrics collection
├── tests/                 # Test suite
├── examples/              # Example configurations
├── docs/                  # Documentation
├── .github/workflows/     # CI/CD configuration
├── Dockerfile             # Docker build
├── docker-compose.yml     # Docker Compose config
├── pyproject.toml         # Project configuration
└── README.md              # Project readme
```

## Making Changes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits format:

```
feat: add new traffic pattern
fix: resolve HTTP timeout issue
docs: update README examples
refactor: simplify metrics collection
test: add tests for WebSocket scenarios
```

### Pull Request Process

1. **Create a branch** for your changes
2. **Make your changes** with clear, focused commits
3. **Add tests** for new functionality
4. **Run the test suite** to ensure everything passes
5. **Update documentation** if needed
6. **Submit a pull request** with a clear description

### PR Checklist

- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`black`)
- [ ] No linting errors (`ruff`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation updated (if needed)
- [ ] Changelog updated (if needed)

## Testing Guidelines

### Writing Tests

- Use `pytest` for all tests
- Use `pytest-asyncio` for async tests
- Mock external services (HTTP, WebSocket)
- Aim for >90% code coverage

```python
import pytest

class TestNewFeature:
    """Tests for new feature."""
    
    def test_something(self) -> None:
        """Test that something works."""
        assert True
    
    @pytest.mark.asyncio
    async def test_async_something(self) -> None:
        """Test async functionality."""
        result = await async_function()
        assert result == expected
```

### Mocking HTTP Requests

Use `respx` for mocking HTTPX:

```python
import respx
from httpx import Response

@respx.mock
def test_http_scenario() -> None:
    route = respx.get("https://api.example.com").mock(return_value=Response(200))
    # Test code here
    assert route.called
```

## Documentation

### Docstrings

Follow Google style docstrings:

```python
def function(arg1: str, arg2: int) -> bool:
    """Short description.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: When something is wrong.
    
    Example:
        >>> function("test", 42)
        True
    """
    return True
```

### README Updates

When adding new features:
1. Update the feature list
2. Add an example to the examples section
3. Update the configuration reference if needed

## Release Process

1. Update version in `src/loadtest/__version__.py`
2. Update `CHANGELOG.md`
3. Create a git tag: `git tag v0.x.x`
4. Push tags: `git push --tags`
5. GitHub Actions will handle the release

## Getting Help

- 📖 Read the [documentation](https://github.com/example/loadtest/tree/main/docs)
- 🐛 [Open an issue](https://github.com/example/loadtest/issues)
- 💬 Start a [discussion](https://github.com/example/loadtest/discussions)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to:

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Respect different viewpoints and experiences

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
