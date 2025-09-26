# BackcastPro

トレーディング戦略のためのPythonバックテストライブラリ。

## インストール

### PyPIから（エンドユーザー向け）

```bash
pip install BackcastPro
```

### 開発用インストール

開発用に、リポジトリをクローンして開発モードでインストールしてください：

```bash
git clone <repository-url>
cd BackcastPro
pip install -e .
```

**開発モードインストール（pip install -e .）**
- 上記で実行したpip install -e .コマンドは、プロジェクトを開発モードでインストールしました
- これにより、srcディレクトリが自動的にPythonパスに追加されます

## 使用方法

```python
from BackcastPro import Strategy, Backtest
from BackcastPro.lib import resample_apply

# ここにトレーディング戦略の実装を記述
```

## ドキュメント

- [PyPIへのデプロイ方法](./docs/How%20to%20deploy%20to%20PyPI.md)
- [サンプル](./docs/examples/)

## バグ報告

バグを報告したり、[ディスカッションボード](https://discord.gg/fzJTbpzE)に投稿する前に、


