# BackcastPro

A Python backtesting library for trading strategies.

## Installation

### From PyPI (for end users)

```bash
pip install BackcastPro
```

### Development Installation

For development, clone the repository and install in development mode:

```bash
git clone <repository-url>
cd BackcastPro
pip install -e .
```

**Development Mode Installation (pip install -e .)**
- The pip install -e . command executed above has installed the project in development mode
- This automatically adds the src directory to the Python path

## Usage

```python
from BackcastPro import Strategy, Backtest
from BackcastPro.lib import resample_apply

# Your trading strategy implementation here
```

## Documents

- [How to deploy to PyPI](./docs/How%20to%20deploy%20to%20PyPI.md)
- [Examples](./docs/examples/)

## Bugs

Before reporting bugs or posting to the
[discussion board](https://discord.gg/fzJTbpzE),


