import pandas as pd
from datetime import datetime, timedelta

from BackcastPro import Strategy
from lib import cross_over, cross_under, position_size_by_risk, update_trailing_stops_and_partials


class SmaCross(Strategy):
    """
    実践向けサンプル戦略:
      - シグナル: SMAクロス（短期>長期でロング、短期<長期でショート）+ RSIフィルタ
      - リスク管理: ATRベースの初期SL/TP（ブラケット注文）、トレーリングSL、部分利確
      - ポジションサイジング: 口座資産の一定割合を最大損失とするユニット計算

    注意:
      - この戦略はデモ目的です。パラメータはデータ特性に合わせて調整してください。
    """

    # パラメータ（必要に応じて調整）
    sma_fast_window = 5    # より短い期間でクロスを増やす
    sma_slow_window = 15   # より短い期間でクロスを増やす
    rsi_window = 14
    rsi_long_threshold = 40  # より緩い条件
    rsi_short_threshold = 60  # より緩い条件
    atr_window = 14
    atr_sl_mult = 2.0
    atr_tp_mult = 3.0
    trailing_atr_mult = 1.5
    risk_per_trade = 0.02  # 口座資産の2%を最大リスク（より大きなポジション）
    partial_tp_rr = 0.5  # TP距離の50%到達で部分利確

    def init(self):
        data = self.data

        # 指標の事前計算（ベクトル化）
        self._sma_fast = data['Close'].rolling(self.sma_fast_window, min_periods=self.sma_fast_window).mean()
        self._sma_slow = data['Close'].rolling(self.sma_slow_window, min_periods=self.sma_slow_window).mean()

        # RSI（SMA方式）
        delta = data['Close'].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.rolling(self.rsi_window, min_periods=self.rsi_window).mean()
        avg_loss = loss.rolling(self.rsi_window, min_periods=self.rsi_window).mean()
        rs = avg_gain / (avg_loss.replace(0, pd.NA))
        self._rsi = 100 - (100 / (1 + rs))

        # ATR（一般的なTRの単純移動平均）
        high = data['High']
        low = data['Low']
        close = data['Close']
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        self._atr = tr.rolling(self.atr_window, min_periods=self.atr_window).mean()





    def next(self):
        # 毎バーの実行ロジック
        close = self.data['Close'].iloc[-1]
        atr = self._atr.iloc[-1]
        rsi = self._rsi.iloc[-1]
        
        # デバッグ情報（最初の数回のみ）
        if len(self.data) <= 20:
            current_data = self.data['Close']
            sma_fast_current = current_data.rolling(self.sma_fast_window, min_periods=self.sma_fast_window).mean()
            sma_slow_current = current_data.rolling(self.sma_slow_window, min_periods=self.sma_slow_window).mean()
            print(f"Bar {len(self.data)}: Close={close:.1f}, ATR={atr:.1f}, RSI={rsi:.1f}")
            sma_fast_val = sma_fast_current.iloc[-1] if not pd.isna(sma_fast_current.iloc[-1]) else 'N/A'
            sma_slow_val = sma_slow_current.iloc[-1] if not pd.isna(sma_slow_current.iloc[-1]) else 'N/A'
            print(f"  SMA Fast={sma_fast_val}, SMA Slow={sma_slow_val}")
            print(f"  Cross Over: {cross_over(self.data, self.sma_fast_window, self.sma_slow_window, self.atr_window, self.rsi_window)}, Cross Under: {cross_under(self.data, self.sma_fast_window, self.sma_slow_window, self.atr_window, self.rsi_window)}")
        
        if pd.isna(atr) or pd.isna(rsi):
            return

        # まず既存ポジションの保守（トレーリング、部分利確）
        update_trailing_stops_and_partials(self, self.data, self.trades, self.position, self._atr, self.trailing_atr_mult, self.atr_tp_mult, self.partial_tp_rr)

        # 新規エントリは未保有のときのみ
        if not self.position:
            stop_distance = self.atr_sl_mult * atr
            units = position_size_by_risk(self.equity, self.risk_per_trade, stop_distance)
            if units <= 0:
                if len(self.data) <= 20:
                    print(f"  Units calculation failed: stop_distance={stop_distance:.1f}, equity={self.equity:.1f}")
                return

            if cross_over(self.data, self.sma_fast_window, self.sma_slow_window, self.atr_window, self.rsi_window) and rsi >= self.rsi_long_threshold:
                sl = close - stop_distance
                tp = close + self.atr_tp_mult * atr
                print(f"LONG SIGNAL: Close={close:.1f}, Units={units}, SL={sl:.1f}, TP={tp:.1f}")
                self.buy(size=units, sl=sl, tp=tp, tag='long')
            elif cross_under(self.data, self.sma_fast_window, self.sma_slow_window, self.atr_window, self.rsi_window) and rsi <= self.rsi_short_threshold:
                sl = close + stop_distance
                tp = close - self.atr_tp_mult * atr
                print(f"SHORT SIGNAL: Close={close:.1f}, Units={units}, SL={sl:.1f}, TP={tp:.1f}")
                self.sell(size=units, sl=sl, tp=tp, tag='short')


# データ取得
from BackcastPro.data import TOYOTA

from BackcastPro import Backtest

# 実行例
bt = Backtest(
    TOYOTA,
    SmaCross,
    cash=10_000,
    commission=.002,        # 0.2% 手数料
    spread=.0,              # スプレッド（必要なら設定）
    margin=1.0,             # 現物想定（レバ1倍）
    exclusive_orders=True,  # 同時に1ポジションのみ
    finalize_trades=True,   # 終了時に未決済をクローズ
)
stats = bt.run()
print(stats)
