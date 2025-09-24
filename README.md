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

**開発モードインストール（pip install -e .）を行う**
- 先ほど実行したpip install -e .により、プロジェクトが開発モードでインストールされています
- これにより、srcディレクトリが自動的にPythonパスに追加されました

## Usage

```python
from BackcastPro import Strategy, Backtest
from BackcastPro.lib import resample_apply

# Your trading strategy implementation here
```

## Documents

- [How to deploy to PyPI](./docs/How%20to%20deploy%20to%20PyPI.md)
- [Examples](./docs/examples/)