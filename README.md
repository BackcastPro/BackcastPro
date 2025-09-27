# <img src="docs/img/logo.drawio.svg" alt="BackcastPro Logo" width="40" height="24"> BackcastPro

トレーディング戦略のためのPythonバックテストライブラリ。

## インストール（Windows）

### PyPIから（エンドユーザー向け）

```powershell
py -m pip install BackcastPro
```

### 開発用インストール

開発用に、リポジトリをクローンして開発モードでインストールします。

```powershell
git clone <repository-url>
cd BackcastPro
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .
py -m pip install -r requirements.txt
```

**開発モードインストール（py -m pip install -e .）**
- プロジェクトを開発モードでインストールします
- `src` ディレクトリが自動的に Python パスに追加されます

## 使用方法

```python
from BackcastPro import Strategy, Backtest
from BackcastPro.data import DataReader, JapanStocks

# ここにトレーディング戦略の実装を記述
```

## ドキュメント

- [ドキュメント一覧](./docs/index.md)
- [チュートリアル](./docs/tutorial.md)
- [APIリファレンス](./docs/api-reference.md)
- [高度な使い方](./docs/advanced-usage.md)
- [トラブルシューティング](./docs/troubleshooting.md)
- [開発者ガイド](./docs/developer-guide.md)
- [PyPIへのデプロイ方法](./docs/how-to-deploy-to-PyPI.md)
- [サンプル](./docs/examples/)

## バグ報告 / サポート

- バグ報告や要望は GitHub Issues へ
- 質問は Discord コミュニティへ（[招待リンク](https://discord.gg/fzJTbpzE)）
- 使い方はドキュメントをご参照ください

