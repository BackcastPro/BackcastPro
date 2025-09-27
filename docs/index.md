# <img src="img/logo.drawio.svg" alt="BackcastPro Logo" width="40" height="24"> BackcastPro ドキュメント

BackcastProは、トレーディング戦略のためのPythonバックテストライブラリです。

## ドキュメント一覧

### ユーザー向けドキュメント

- **[チュートリアル](tutorial.md)** - 基本的な使い方を学ぶ
- **[APIリファレンス](api-reference.md)** - クラスとメソッドの詳細
- **[高度な使い方](advanced-usage.md)** - 高度な機能とテクニック
- **[トラブルシューティング](troubleshooting.md)** - よくある問題と解決方法

### 開発者向けドキュメント

- **[開発者ガイド](developer-guide.md)** - 開発に参加するための情報
- **[PyPIへのデプロイ方法](how-to-deploy-to-PyPI.md)** - パッケージの配布方法

### サンプルコード

- **[サンプル集](examples/)** - 実用的な戦略の例
  - [クイックスタートガイド](examples/QuickStartUserGuide.py)
  - [SMAクロス戦略](examples/SmaCross.py)
  - [Streamlitアプリ](examples/Streamlit.py)

## クイックスタート

```python
from BackcastPro import Strategy, Backtest
from BackcastPro.data import DataReader

# シンプルな買い持ち戦略
class BuyAndHold(Strategy):
    def init(self):
        pass
    
    def next(self):
        if len(self.data) == 1:
            self.buy()

# データを取得してバックテストを実行
data = DataReader('7203')  # トヨタ
bt = Backtest(data, BuyAndHold, cash=10000)
results = bt.run()
print(results)
```

## 主な機能

- **シンプルな戦略実装**: `Strategy` を継承して `init` と `next` を実装
- **日本株データ取得**: `DataReader` と `JapanStocks` を提供
- **統計の自動計算**: 代表的なパフォーマンス指標を同梱
- **リスク管理**: `sl` と `tp` に標準対応
- **可視化**: Streamlit 連携の例を提供

```mermaid
flowchart TD
    A[データ取得 DataReader] --> B[Backtest 初期化]
    B --> C[Strategy.init 前処理]
    C --> D[Strategy.next ループ]
    D --> E[_Broker 注文/約定]
    E --> F[_stats 統計計算]
    F --> G[結果 pd.Series]
```

## サポート

- **GitHub Issues**: バグ報告や機能要求
- **Discord**: コミュニティでの質問
- **ドキュメント**: 詳細な使用方法の確認

## ライセンス

MIT License - 詳細は[LICENSE](../LICENSE)を参照してください。
