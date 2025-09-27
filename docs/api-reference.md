# <img src="img/logo.drawio.svg" alt="BackcastPro Logo" width="40" height="24"> APIリファレンス

BackcastProの主要クラスとメソッドの詳細なリファレンスです。

## 目次

- [Strategy](#strategy)
- [Backtest](#backtest)
- [DataReader](#datareader)
- [Order](#order)
- [Position](#position)
- [Trade](#trade)

## Strategy

トレーディング戦略の基底クラス。独自の戦略を実装する際は、このクラスを継承してください。

### メソッド

#### `init()`
戦略の初期化メソッド。バックテスト開始前に一度だけ呼び出されます。

```python
def init(self):
    # インジケーターの事前計算
    self.data['SMA'] = self.data.Close.rolling(20).mean()
    self.data['RSI'] = calculate_rsi(self.data)
```

#### `next()`
各バー（ローソク足）ごとに呼び出されるメインメソッド。

```python
def next(self):
    # エントリー条件の判定
    if self.data.SMA.iloc[-1] > self.data.Close.iloc[-1]:
        self.buy()
```

### 取引メソッド

#### `buy(size, limit, stop, sl, tp, tag)`
ロングポジションを開きます。

**パラメータ:**
- `size` (float): 取引サイズ。デフォルトは利用可能資金の99.99%
- `limit` (float, optional): 指値価格
- `stop` (float, optional): ストップ価格
- `sl` (float, optional): ストップロス価格
- `tp` (float, optional): テイクプロフィット価格
- `tag` (object, optional): 注文タグ

**戻り値:** `Order`オブジェクト

#### `sell(size, limit, stop, sl, tp, tag)`
ショートポジションを開きます。

パラメータは`buy()`と同じです。

### プロパティ

#### `equity`
現在のアカウント資産（現金 + 保有資産の評価額）

#### `data`
価格データのDataFrame

#### `position`
現在のポジション情報

#### `orders`
実行待ちのオーダーリスト

#### `trades`
アクティブなトレードリスト

#### `closed_trades`
決済済みトレードリスト

## Backtest

バックテストを実行するメインクラス。

### コンストラクタ

```python
Backtest(data, strategy, *, cash=10000, spread=0.0, commission=0.0, 
         margin=1.0, trade_on_close=False, hedging=False, 
         exclusive_orders=False, finalize_trades=False)
```

**パラメータ:**
- `data` (pd.DataFrame): OHLCVデータ
- `strategy` (Strategy): 戦略クラス（インスタンスではない）
- `cash` (float): 初期資金。デフォルト10,000
- `spread` (float): スプレッド率。デフォルト0.0
- `commission` (float): 手数料率。デフォルト0.0
- `margin` (float): 必要証拠金率。デフォルト1.0
- `trade_on_close` (bool): 終値で約定するか。デフォルトFalse
- `hedging` (bool): 両建てを許可するか。デフォルトFalse
- `exclusive_orders` (bool): 排他的注文か。デフォルトFalse
- `finalize_trades` (bool): 終了時に未決済をクローズするか。デフォルトFalse

### メソッド

#### `run()`
バックテストを実行し、結果を返します。

**戻り値:** `pd.Series` - バックテスト結果と統計情報

**例:**
```python
bt = Backtest(data, MyStrategy, cash=10000, commission=0.001)
results = bt.run()
print(results)
```

## DataReader

株価データを取得するためのクラス。

### 関数

#### `DataReader(code, start_date=None, end_date=None)`
指定された銘柄の株価データを取得します。

**パラメータ:**
- `code` (str): 銘柄コード（例: '7203'）
- `start_date` (str/datetime, optional): 開始日
- `end_date` (str/datetime, optional): 終了日

**戻り値:** `pd.DataFrame` - OHLCVデータ

**例:**
```python
from BackcastPro.data import DataReader

# トヨタの過去1年分のデータを取得
data = DataReader('7203')
```

#### `JapanStocks()`
日本株の銘柄リストを取得します。

**戻り値:** `pd.DataFrame` - 銘柄リスト

## Order

注文を表すクラス。

### プロパティ

- `size`: 注文サイズ
- `limit`: 指値価格
- `stop`: ストップ価格
- `sl`: ストップロス価格
- `tp`: テイクプロフィット価格
- `tag`: 注文タグ

### メソッド

#### `cancel()`
注文をキャンセルします。

## Position

現在のポジションを表すクラス。

### プロパティ

- `size`: ポジションサイズ
- `is_long`: ロングポジションかどうか
- `is_short`: ショートポジションかどうか
- `pl`: 現在の損益

### メソッド

#### `close(portion: float = 1.0)`
ポジションの一部または全量をクローズします（0 < portion ≤ 1）。

## Trade

個別のトレードを表すクラス。

### プロパティ

- `size`: トレードサイズ
- `entry_price`: エントリー価格
- `entry_time`: エントリータイム
- `exit_price`: エグジット価格
- `exit_time`: エグジットタイム
- `pl`: 損益
- `pl_pct`: 損益率
- `is_long`: ロングトレードかどうか
- `is_short`: ショートトレードかどうか
- `sl`: ストップロス価格
- `tp`: テイクプロフィット価格

### メソッド

#### `close(portion: float = 1.0)`
トレードの一部または全量をクローズします（0 < portion ≤ 1）。

## データ形式

### OHLCVデータ

BackcastProで使用するデータは以下の列を持つDataFrameである必要があります：

- `Open`: 始値
- `High`: 高値
- `Low`: 安値
- `Close`: 終値
- `Volume`: 出来高（オプション）

インデックスは日時（DatetimeIndex）または単調増加の数値インデックスである必要があります。

### 例

```python
import pandas as pd

data = pd.DataFrame({
    'Open': [100, 101, 102],
    'High': [105, 106, 107],
    'Low': [99, 100, 101],
    'Close': [104, 105, 106],
    'Volume': [1000, 1100, 1200]
}, index=pd.date_range('2023-01-01', periods=3))
```

## エラーハンドリング

### よくあるエラー

#### `TypeError: strategy must be a Strategy sub-type`
戦略クラスがStrategyを継承していない場合に発生します。

**解決方法:**
```python
from BackcastPro import Strategy

class MyStrategy(Strategy):  # Strategyを継承
    def init(self):
        pass
    
    def next(self):
        pass
```

#### `ValueError: data must be a pandas.DataFrame with columns`
データがDataFrameでない、または必要な列がない場合に発生します。

**解決方法:**
```python
# 必要な列を確認
required_columns = ['Open', 'High', 'Low', 'Close']
if not all(col in data.columns for col in required_columns):
    raise ValueError("必要な列が不足しています")
```

#### `ValueError: Some OHLC values are missing (NaN)`
OHLCデータに欠損値がある場合に発生します。

**解決方法:**
```python
# 欠損値を削除
data = data.dropna()

# または補間
data = data.interpolate()
```
