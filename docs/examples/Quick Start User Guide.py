import pandas as pd
from datetime import datetime, timedelta

from BackcastPro import Strategy


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

    def _cross_over(self) -> bool:
        # 短期が長期を上抜け
        if len(self.data) < max(self.sma_slow_window, self.atr_window, self.rsi_window) + 2:
            return False
        # 現在のバーでのSMAを計算
        current_data = self.data['Close']
        sma_fast_current = current_data.rolling(self.sma_fast_window, min_periods=self.sma_fast_window).mean()
        sma_slow_current = current_data.rolling(self.sma_slow_window, min_periods=self.sma_slow_window).mean()
        
        if len(current_data) < 2 or pd.isna(sma_fast_current.iloc[-2]) or pd.isna(sma_slow_current.iloc[-2]) or pd.isna(sma_fast_current.iloc[-1]) or pd.isna(sma_slow_current.iloc[-1]):
            return False
            
        return (sma_fast_current.iloc[-2] <= sma_slow_current.iloc[-2]) and (sma_fast_current.iloc[-1] > sma_slow_current.iloc[-1])

    def _cross_under(self) -> bool:
        # 短期が長期を下抜け
        if len(self.data) < max(self.sma_slow_window, self.atr_window, self.rsi_window) + 2:
            return False
        # 現在のバーでのSMAを計算
        current_data = self.data['Close']
        sma_fast_current = current_data.rolling(self.sma_fast_window, min_periods=self.sma_fast_window).mean()
        sma_slow_current = current_data.rolling(self.sma_slow_window, min_periods=self.sma_slow_window).mean()
        
        if len(current_data) < 2 or pd.isna(sma_fast_current.iloc[-2]) or pd.isna(sma_slow_current.iloc[-2]) or pd.isna(sma_fast_current.iloc[-1]) or pd.isna(sma_slow_current.iloc[-1]):
            return False
            
        return (sma_fast_current.iloc[-2] >= sma_slow_current.iloc[-2]) and (sma_fast_current.iloc[-1] < sma_slow_current.iloc[-1])

    def _position_size_by_risk(self, stop_distance: float) -> int:
        # 口座資産×risk_per_trade を最大損失とする単位数
        if stop_distance <= 0 or pd.isna(stop_distance):
            return 0
        risk_amount = self.equity * self.risk_per_trade
        units = int(risk_amount // stop_distance)
        return max(units, 0)

    def _update_trailing_stops_and_partials(self):
        # トレーリングSLと部分利確（閾値クロス時に一度のみ発火）
        if not self.position:
            return

        close = self.data['Close'].iloc[-1]
        prev_close = self.data['Close'].iloc[-2]
        atr = self._atr.iloc[-1]
        if pd.isna(atr):
            return

        for t in list(self.trades):
            if t.is_long:
                # トレーリングSL（価格 - k * ATR）を引き上げ
                new_sl = max((t.sl or -float('inf')), close - self.trailing_atr_mult * atr)
                # エントリーより下にしない（ブレイクイーブン以上）
                new_sl = max(new_sl, t.entry_price)
                if t.sl is None or new_sl > t.sl:
                    t.sl = new_sl

                # 部分利確: TP距離のpartial_tp_rr倍に初到達したとき
                tp_price = t.entry_price + self.atr_tp_mult * atr
                threshold = t.entry_price + self.partial_tp_rr * (tp_price - t.entry_price)
                if prev_close < threshold <= close:
                    t.close(0.5)
            else:
                # ショートのトレーリングSL（価格 + k * ATR）を引き下げ
                new_sl = min((t.sl or float('inf')), close + self.trailing_atr_mult * atr)
                new_sl = min(new_sl, t.entry_price)
                if t.sl is None or new_sl < t.sl:
                    t.sl = new_sl

                # 部分利確（ショート）
                tp_price = t.entry_price - self.atr_tp_mult * atr
                threshold = t.entry_price + self.partial_tp_rr * (tp_price - t.entry_price)
                if prev_close > threshold >= close:
                    t.close(0.5)

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
            print(f"  Cross Over: {self._cross_over()}, Cross Under: {self._cross_under()}")
        
        if pd.isna(atr) or pd.isna(rsi):
            return

        # まず既存ポジションの保守（トレーリング、部分利確）
        self._update_trailing_stops_and_partials()

        # 新規エントリは未保有のときのみ
        if not self.position:
            stop_distance = self.atr_sl_mult * atr
            units = self._position_size_by_risk(stop_distance)
            if units <= 0:
                if len(self.data) <= 20:
                    print(f"  Units calculation failed: stop_distance={stop_distance:.1f}, equity={self.equity:.1f}")
                return

            if self._cross_over() and rsi >= self.rsi_long_threshold:
                sl = close - stop_distance
                tp = close + self.atr_tp_mult * atr
                print(f"LONG SIGNAL: Close={close:.1f}, Units={units}, SL={sl:.1f}, TP={tp:.1f}")
                self.buy(size=units, sl=sl, tp=tp, tag='long')
            elif self._cross_under() and rsi <= self.rsi_short_threshold:
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
