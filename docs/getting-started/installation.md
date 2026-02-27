# Installation

## Requirements

- Python 3.9 or higher
- pip 20.0 or higher

## Install from PyPI

```bash
pip install loadtest
```

## Install with Optional Dependencies

### Web Automation Support

```bash
pip install "loadtest[web]"
playwright install chromium
```

### Development Tools

```bash
pip install "loadtest[dev]"
```

## Verify Installation

```python
from loadtest import LoadTest

test = LoadTest(name="Test")
print(test.config.name)
```

## Upgrade

```bash
pip install --upgrade loadtest
```

## Uninstall

```bash
pip uninstall loadtest
```
