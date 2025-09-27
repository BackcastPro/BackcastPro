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
from BackcastPro.data import DataReader, JapanStocks

# ここにトレーディング戦略の実装を記述
```

## ドキュメント

- [ドキュメント一覧](./docs/index.md)
- [チュートリアル](./docs/tutorial.md) - 基本的な使い方
- [APIリファレンス](./docs/api-reference.md) - クラスとメソッドの詳細
- [高度な使い方](./docs/advanced-usage.md) - 高度な機能とテクニック
- [トラブルシューティング](./docs/troubleshooting.md) - よくある問題と解決方法
- [開発者ガイド](./docs/developer-guide.md) - 開発に参加するための情報
- [PyPIへのデプロイ方法](./docs/how-to-deploy-to-PyPI.md)
- [サンプル](./docs/examples/)

## バグ報告

バグを報告したり、[ディスカッションボード](https://discord.gg/fzJTbpzE)に投稿する前に、


