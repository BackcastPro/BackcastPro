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

### 複雑なインジケーターの組み合わせ

```python
import pandas as pd
import numpy as np
from BackcastPro import Strategy

class AdvancedStrategy(Strategy):
    def init(self):
        # 複数のインジケーターを計算
        self.data['SMA_20'] = self.data.Close.rolling(20).mean()
        self.data['SMA_50'] = self.data.Close.rolling(50).mean()
        self.data['RSI'] = self.calculate_rsi(14)
        self.data['ATR'] = self.calculate_atr(14)
        self.data['BB_upper'] = self.calculate_bollinger_bands(20, 2)[0]
        self.data['BB_lower'] = self.calculate_bollinger_bands(20, 2)[1]
        self.data['MACD'] = self.calculate_macd(12, 26, 9)[0]
        self.data['MACD_signal'] = self.calculate_macd(12, 26, 9)[1]
        
        # トレンドの強さを計算
        self.data['trend_strength'] = self.calculate_trend_strength()
    
    def calculate_rsi(self, period):
        """RSI計算"""
        delta = self.data['Close'].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.rolling(period, min_periods=period).mean()
        avg_loss = loss.rolling(period, min_periods=period).mean()
        rs = avg_gain / (avg_loss.replace(0, pd.NA))
        return 100 - (100 / (1 + rs))
    
    def calculate_atr(self, period):
        """ATR計算"""
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close']
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(period, min_periods=period).mean()
    
    def calculate_bollinger_bands(self, period, std_dev):
        """ボリンジャーバンド計算"""
        sma = self.data.Close.rolling(period).mean()
        std = self.data.Close.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, lower
    
    def calculate_macd(self, fast, slow, signal):
        """MACD計算"""
        ema_fast = self.data.Close.ewm(span=fast).mean()
        ema_slow = self.data.Close.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        return macd, macd_signal
    
    def calculate_trend_strength(self):
        """トレンドの強さを計算"""
        # 価格の傾きを計算
        price_slope = self.data.Close.rolling(20).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0]
        )
        # 正規化
        return (price_slope - price_slope.rolling(100).mean()) / price_slope.rolling(100).std()
    
    def next(self):
        # 複数の条件を組み合わせたエントリー
        if self.should_enter_long():
            self.enter_long()
        elif self.should_enter_short():
            self.enter_short()
        
        # ポジション管理
        if self.position.size != 0:
            self.manage_position()
    
    def should_enter_long(self):
        """ロングエントリー条件"""
        current = self.data.iloc[-1]
        prev = self.data.iloc[-2]
        
        # 複数の条件をチェック
        conditions = [
            current['SMA_20'] > current['SMA_50'],  # ゴールデンクロス
            current['RSI'] > 30 and current['RSI'] < 70,  # RSIが適正範囲
            current['Close'] > current['BB_lower'],  # ボリンジャーバンド下限を上回る
            current['MACD'] > current['MACD_signal'],  # MACDがシグナルを上回る
            current['trend_strength'] > 0.5,  # トレンドが強い
        ]
        
        return all(conditions)
    
    def should_enter_short(self):
        """ショートエントリー条件"""
        current = self.data.iloc[-1]
        prev = self.data.iloc[-2]
        
        conditions = [
            current['SMA_20'] < current['SMA_50'],  # デッドクロス
            current['RSI'] > 30 and current['RSI'] < 70,  # RSIが適正範囲
            current['Close'] < current['BB_upper'],  # ボリンジャーバンド上限を下回る
            current['MACD'] < current['MACD_signal'],  # MACDがシグナルを下回る
            current['trend_strength'] < -0.5,  # 下降トレンドが強い
        ]
        
        return all(conditions)
    
    def enter_long(self):
        """ロングエントリー"""
        if self.position.size == 0:
            # リスク管理付きでエントリー
            stop_loss = self.data.Close.iloc[-1] - 2 * self.data.ATR.iloc[-1]
            take_profit = self.data.Close.iloc[-1] + 3 * self.data.ATR.iloc[-1]
            
            self.buy(sl=stop_loss, tp=take_profit)
    
    def enter_short(self):
        """ショートエントリー"""
        if self.position.size == 0:
            # リスク管理付きでエントリー
            stop_loss = self.data.Close.iloc[-1] + 2 * self.data.ATR.iloc[-1]
            take_profit = self.data.Close.iloc[-1] - 3 * self.data.ATR.iloc[-1]
            
            self.sell(sl=stop_loss, tp=take_profit)
    
    def manage_position(self):
        """ポジション管理"""
        current = self.data.iloc[-1]
        
        # トレーリングストップ
        if self.position.is_long:
            new_stop = current['Close'] - 1.5 * current['ATR']
            if new_stop > self.position.sl:
                self.position.sl = new_stop
        
        # 利益確定条件
        if self.position.is_long and current['RSI'] > 80:
            self.position.close(0.5)  # 半分利確
        
        if self.position.is_short and current['RSI'] < 20:
            self.position.close(0.5)  # 半分利確
```

## リスク管理

### ポジションサイジング

```python
class RiskManagedStrategy(Strategy):
    def init(self):
        self.data['ATR'] = self.calculate_atr(14)
        self.risk_per_trade = 0.02  # 1トレードあたり2%のリスク
        self.max_position_size = 0.1  # 最大ポジションサイズ10%
    
    def calculate_position_size(self, stop_distance):
        """リスクベースのポジションサイズ計算"""
        if stop_distance <= 0:
            return 0
        
        risk_amount = self.equity * self.risk_per_trade
        position_size = risk_amount / stop_distance
        
        # 最大ポジションサイズで制限
        max_size = self.equity * self.max_position_size
        return min(position_size, max_size)
    
    def next(self):
        if self.should_enter():
            # ストップロス距離を計算
            stop_distance = 2 * self.data.ATR.iloc[-1]
            
            # ポジションサイズを計算
            position_size = self.calculate_position_size(stop_distance)
            
            if position_size > 0:
                stop_loss = self.data.Close.iloc[-1] - stop_distance
                self.buy(size=position_size, sl=stop_loss)
```

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

### ベクトル化された計算

```python
class OptimizedStrategy(Strategy):
    def init(self):
        # ベクトル化された計算でパフォーマンスを向上
        self.data['SMA'] = self.data.Close.rolling(20).mean()
        self.data['RSI'] = self.calculate_rsi_vectorized(14)
        self.data['ATR'] = self.calculate_atr_vectorized(14)
        
        # 事前計算されたシグナル
        self.data['buy_signal'] = (
            (self.data['SMA'] > self.data['Close'].shift(1)) &
            (self.data['RSI'] > 30) &
            (self.data['RSI'] < 70)
        )
        
        self.data['sell_signal'] = (
            (self.data['SMA'] < self.data['Close'].shift(1)) &
            (self.data['RSI'] > 30) &
            (self.data['RSI'] < 70)
        )
    
    def calculate_rsi_vectorized(self, period):
        """ベクトル化されたRSI計算"""
        delta = self.data['Close'].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        
        # 指数移動平均を使用
        avg_gain = gain.ewm(span=period).mean()
        avg_loss = loss.ewm(span=period).mean()
        
        rs = avg_gain / (avg_loss.replace(0, pd.NA))
        return 100 - (100 / (1 + rs))
    
    def calculate_atr_vectorized(self, period):
        """ベクトル化されたATR計算"""
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close']
        prev_close = close.shift(1)
        
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        
        return tr.ewm(span=period).mean()
    
    def next(self):
        # 事前計算されたシグナルを使用
        if self.data['buy_signal'].iloc[-1]:
            self.buy()
        elif self.data['sell_signal'].iloc[-1]:
            self.sell()
```

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

### ポートフォリオ戦略

```python
class PortfolioStrategy(Strategy):
    def init(self):
        # 複数銘柄のデータを統合
        self.stocks = ['7203', '6758', '9984']  # トヨタ、ソニー、ソフトバンク
        self.weights = [0.4, 0.3, 0.3]  # ポートフォリオの重み
        
        # 各銘柄のインジケーターを計算
        for stock in self.stocks:
            self.data[f'{stock}_SMA'] = self.data[f'{stock}_Close'].rolling(20).mean()
            self.data[f'{stock}_RSI'] = self.calculate_rsi(f'{stock}_Close', 14)
    
    def calculate_rsi(self, column, period):
        """指定された列のRSIを計算"""
        delta = self.data[column].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.rolling(period, min_periods=period).mean()
        avg_loss = loss.rolling(period, min_periods=period).mean()
        rs = avg_gain / (avg_loss.replace(0, pd.NA))
        return 100 - (100 / (1 + rs))
    
    def next(self):
        # 各銘柄のシグナルを計算
        signals = {}
        for i, stock in enumerate(self.stocks):
            sma_col = f'{stock}_SMA'
            close_col = f'{stock}_Close'
            rsi_col = f'{stock}_RSI'
            
            # シグナルを計算
            if (self.data[sma_col].iloc[-1] > self.data[close_col].iloc[-1] and
                self.data[rsi_col].iloc[-1] > 30):
                signals[stock] = 'BUY'
            elif (self.data[sma_col].iloc[-1] < self.data[close_col].iloc[-1] and
                  self.data[rsi_col].iloc[-1] < 70):
                signals[stock] = 'SELL'
            else:
                signals[stock] = 'HOLD'
        
        # ポートフォリオのリバランス
        self.rebalance_portfolio(signals)
    
    def rebalance_portfolio(self, signals):
        """ポートフォリオのリバランス"""
        # 現在のポジションをクローズ
        self.position.close()
        
        # 新しいポジションを開く
        for i, stock in enumerate(self.stocks):
            if signals[stock] == 'BUY':
                weight = self.weights[i]
                size = self.equity * weight / self.data[f'{stock}_Close'].iloc[-1]
                self.buy(size=size)
```

## カスタムブローカー

### スプレッドとスリッページのモデリング

```python
class CustomBroker:
    def __init__(self, base_spread=0.0002, slippage=0.0001):
        self.base_spread = base_spread
        self.slippage = slippage
    
    def calculate_execution_price(self, order_price, order_size, market_volatility):
        """実行価格を計算"""
        # スプレッドを適用
        spread = self.base_spread * (1 + market_volatility)
        
        # スリッページを適用
        slippage = self.slippage * abs(order_size) / 1000
        
        # 実行価格を計算
        if order_size > 0:  # 買い注文
            execution_price = order_price * (1 + spread + slippage)
        else:  # 売り注文
            execution_price = order_price * (1 - spread - slippage)
        
        return execution_price
```

## カスタム統計指標

### 独自のパフォーマンス指標

```python
def calculate_custom_stats(trades, equity_curve):
    """カスタム統計指標を計算"""
    stats = {}
    
    # カスタム指標1: 最大連続勝ち数
    consecutive_wins = 0
    max_consecutive_wins = 0
    for trade in trades:
        if trade.pl > 0:
            consecutive_wins += 1
            max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
        else:
            consecutive_wins = 0
    
    stats['Max Consecutive Wins'] = max_consecutive_wins
    
    # カスタム指標2: 平均保有期間
    if len(trades) > 0:
        avg_holding_period = trades['Duration'].mean()
        stats['Avg Holding Period'] = avg_holding_period
    
    # カスタム指標3: ボラティリティ調整リターン
    returns = equity_curve['Equity'].pct_change().dropna()
    volatility = returns.std() * np.sqrt(252)
    annual_return = (equity_curve['Equity'].iloc[-1] / equity_curve['Equity'].iloc[0]) ** (252 / len(equity_curve)) - 1
    
    if volatility > 0:
        stats['Volatility Adjusted Return'] = annual_return / volatility
    
    return stats
```

## バックテストの最適化

### パラメータ最適化

```python
from itertools import product
import pandas as pd

def optimize_strategy(data, strategy_class, param_ranges):
    """戦略のパラメータを最適化"""
    best_params = None
    best_return = -float('inf')
    results = []
    
    # パラメータの組み合わせを生成
    param_names = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    
    for params in product(*param_values):
        param_dict = dict(zip(param_names, params))
        
        # 戦略クラスにパラメータを設定
        strategy = type('OptimizedStrategy', (strategy_class,), param_dict)
        
        # バックテストを実行
        bt = Backtest(data, strategy, cash=10000)
        result = bt.run()
        
        # 結果を記録
        results.append({
            'params': param_dict,
            'return': result['Return [%]'],
            'sharpe': result['Sharpe Ratio'],
            'max_dd': result['Max. Drawdown [%]']
        })
        
        # 最良のパラメータを更新
        if result['Return [%]'] > best_return:
            best_return = result['Return [%]']
            best_params = param_dict
    
    return best_params, pd.DataFrame(results)

# 使用例
param_ranges = {
    'sma_short': [5, 10, 15, 20],
    'sma_long': [20, 30, 40, 50],
    'rsi_period': [10, 14, 20]
}

best_params, results_df = optimize_strategy(data, MyStrategy, param_ranges)
print("最良のパラメータ:", best_params)
print("結果一覧:")
print(results_df.sort_values('return', ascending=False).head())
```

## リアルタイム取引への応用

### シグナル生成

```python
class SignalGenerator:
    def __init__(self, strategy_class, data):
        self.strategy_class = strategy_class
        self.data = data
        self.strategy = None
    
    def initialize(self):
        """戦略を初期化"""
        # ダミーのブローカーで戦略を初期化
        from BackcastPro._broker import _Broker
        dummy_broker = _Broker(cash=10000, data=self.data)
        self.strategy = self.strategy_class(dummy_broker, self.data)
        self.strategy.init()
    
    def generate_signal(self, new_data):
        """新しいデータでシグナルを生成"""
        # データを更新
        self.data = pd.concat([self.data, new_data])
        self.strategy._data = self.data
        
        # シグナルを生成
        self.strategy.next()
        
        # シグナルを返す
        return {
            'action': 'BUY' if self.strategy.position.size > 0 else 'SELL' if self.strategy.position.size < 0 else 'HOLD',
            'size': abs(self.strategy.position.size),
            'price': self.data['Close'].iloc[-1]
        }

# 使用例
signal_generator = SignalGenerator(MyStrategy, historical_data)
signal_generator.initialize()

# リアルタイムでシグナルを生成
new_bar = pd.DataFrame({
    'Open': [100], 'High': [105], 'Low': [99], 'Close': [104], 'Volume': [1000]
}, index=[pd.Timestamp.now()])

signal = signal_generator.generate_signal(new_bar)
print("シグナル:", signal)
```

## まとめ

この高度な使い方ガイドでは、BackcastProの高度な機能とテクニックを説明しました：

1. **カスタム戦略の実装**: 複雑なインジケーターの組み合わせ
2. **リスク管理**: ポジションサイジングとポートフォリオリスク管理
3. **パフォーマンス最適化**: ベクトル化とメモリ効率の改善
4. **複数銘柄の同時バックテスト**: ポートフォリオ戦略の実装
5. **カスタムブローカー**: スプレッドとスリッページのモデリング
6. **カスタム統計指標**: 独自のパフォーマンス指標
7. **バックテストの最適化**: パラメータ最適化
8. **リアルタイム取引への応用**: シグナル生成

これらのテクニックを組み合わせることで、より高度で実用的なバックテストシステムを構築できます。
