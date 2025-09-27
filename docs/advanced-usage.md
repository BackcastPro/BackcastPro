# <img src="img/logo.drawio.svg" alt="BackcastPro Logo" width="40" height="24"> 高度な使い方ガイド

BackcastProの高度な機能とテクニックを学びます。

## 目次

- [カスタム戦略の実装](#カスタム戦略の実装)
- [リスク管理](#リスク管理)
- [パフォーマンス最適化](#パフォーマンス最適化)
- [複数銘柄の同時バックテスト](#複数銘柄の同時バックテスト)
- [カスタムブローカー](#カスタムブローカー)
- [カスタム統計指標](#カスタム統計指標)
- [バックテストの最適化](#バックテストの最適化)
- [リアルタイム取引への応用](#リアルタイム取引への応用)

## カスタム戦略の実装

複数インジケーターの組み合わせやルールベースの管理は、`Strategy.init` で前処理を行い、`Strategy.next` で意思決定するだけです。大規模なコード例はサンプルに集約しました。

- 参考: `examples/SmaCross.py`
- 参考: `examples/QuickStartUserGuide.py`

## リスク管理

- `buy()` / `sell()` の `sl` と `tp` を活用（損失限定・利確）
- 口座リスクに基づくサイズ調整（`equity` と `ATR` を用いた距離計測 など）

> 具体例はサンプルコードと API リファレンスの `Order`/`Trade` を参照してください。

### ポートフォリオリスク管理

```python
class PortfolioRiskStrategy(Strategy):
    def init(self):
        self.max_drawdown = 0.15  # 最大ドローダウン15%
        self.max_daily_loss = 0.05  # 1日の最大損失5%
        self.peak_equity = self.equity
        self.daily_start_equity = self.equity
        
    def next(self):
        # ドローダウンチェック
        current_drawdown = (self.peak_equity - self.equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            # 全ポジションをクローズ
            self.position.close()
            return
        
        # 日次損失チェック
        daily_loss = (self.daily_start_equity - self.equity) / self.daily_start_equity
        if daily_loss > self.max_daily_loss:
            # 全ポジションをクローズ
            self.position.close()
            return
        
        # 通常の戦略ロジック
        if self.should_enter():
            self.enter_position()
        
        # ピークエクイティを更新
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
```

## パフォーマンス最適化

- 前処理は `init()` でベクトル化して計算
- ループ内の処理は最小限にする（フラグ列を用意して参照する など）
- 期間や列を絞り、必要なデータのみを保持

### メモリ効率の最適化

```python
class MemoryEfficientStrategy(Strategy):
    def init(self):
        # 必要な列のみを保持
        self.data = self.data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # データ型を最適化
        self.data = self.data.astype({
            'Open': 'float32',
            'High': 'float32',
            'Low': 'float32',
            'Close': 'float32',
            'Volume': 'int32'
        })
        
        # インジケーターを計算
        self.data['SMA'] = self.data.Close.rolling(20).mean()
    
    def next(self):
        # シンプルなロジックでメモリ使用量を削減
        if len(self.data) > 20:
            if self.data['SMA'].iloc[-1] > self.data['Close'].iloc[-1]:
                self.buy()
            else:
                self.sell()
```

## 複数銘柄の同時バックテスト

銘柄横断の集計やポートフォリオ配分はデータの列設計に依存します。必要に応じてサンプルを参考に拡張してください。

## 注文ライフサイクル（参考）

```mermaid
flowchart LR
    A[Strategy.buy/sell] --> B{limit/stop?}
    B -- Yes --> C[条件成立時に約定]
    B -- No  --> D[成行: 次バーの始値
                    (trade_on_close=Trueなら終値)]
    C --> E[Trade作成]
    D --> E
    E --> F{SL/TP設定?}
    F -- Yes --> G[OCO注文を生成]
    F -- No  --> H[保持]
    G --> I[約定で部分/全クローズ]
    H --> I
    I --> J[_statsで集計]
```

## カスタム統計指標

結果の `pd.Series` には `_equity_curve` と `_trades` が含まれます。これらを用いて独自指標を計算できます。

## バックテストの最適化

- クラス変数（例: `n1=10` のような窓）を用いたグリッドサーチが簡便
- 並列化や記録は用途に応じて実装
- 実装例はサンプルをご参照ください

## リアルタイム取引への応用

本ライブラリはオフラインのバックテスト用です。リアルタイム用途では「シグナル生成」と「実発注」を分離し、データ更新ごとに `Strategy` を進める設計にすると流用しやすくなります。

## まとめ

- 詳細実装はサンプルと API リファレンスを参照し、本文は考え方を中心に構成しました
- 図で流れを把握し、必要な箇所だけコードを読み込むと効率的です
