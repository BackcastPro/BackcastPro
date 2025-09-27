import pandas as pd


def cross_over(data, sma_fast_window, sma_slow_window, atr_window, rsi_window) -> bool:
    """短期が長期を上抜け"""
    if len(data) < max(sma_slow_window, atr_window, rsi_window) + 2:
        return False
    # 現在のバーでのSMAを計算
    current_data = data['Close']
    sma_fast_current = current_data.rolling(sma_fast_window, min_periods=sma_fast_window).mean()
    sma_slow_current = current_data.rolling(sma_slow_window, min_periods=sma_slow_window).mean()
    
    if len(current_data) < 2 or pd.isna(sma_fast_current.iloc[-2]) or pd.isna(sma_slow_current.iloc[-2]) or pd.isna(sma_fast_current.iloc[-1]) or pd.isna(sma_slow_current.iloc[-1]):
        return False
        
    return (sma_fast_current.iloc[-2] <= sma_slow_current.iloc[-2]) and (sma_fast_current.iloc[-1] > sma_slow_current.iloc[-1])


def cross_under(data, sma_fast_window, sma_slow_window, atr_window, rsi_window) -> bool:
    """短期が長期を下抜け"""
    if len(data) < max(sma_slow_window, atr_window, rsi_window) + 2:
        return False
    # 現在のバーでのSMAを計算
    current_data = data['Close']
    sma_fast_current = current_data.rolling(sma_fast_window, min_periods=sma_fast_window).mean()
    sma_slow_current = current_data.rolling(sma_slow_window, min_periods=sma_slow_window).mean()
    
    if len(current_data) < 2 or pd.isna(sma_fast_current.iloc[-2]) or pd.isna(sma_slow_current.iloc[-2]) or pd.isna(sma_fast_current.iloc[-1]) or pd.isna(sma_slow_current.iloc[-1]):
        return False
        
    return (sma_fast_current.iloc[-2] >= sma_slow_current.iloc[-2]) and (sma_fast_current.iloc[-1] < sma_slow_current.iloc[-1])


def position_size_by_risk(equity, risk_per_trade, stop_distance: float) -> int:
    """口座資産×risk_per_trade を最大損失とする単位数"""
    if stop_distance <= 0 or pd.isna(stop_distance):
        return 0
    risk_amount = equity * risk_per_trade
    units = int(risk_amount // stop_distance)
    return max(units, 0)


def update_trailing_stops_and_partials(self, data, trades, position, atr, trailing_atr_mult, atr_tp_mult, partial_tp_rr):
    """トレーリングSLと部分利確（閾値クロス時に一度のみ発火）"""
    if not position:
        return

    close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[-2]
    atr_value = atr.iloc[-1]
    if pd.isna(atr_value):
        return

    for t in list(trades):
        if t.is_long:
            # トレーリングSL（価格 - k * ATR）を引き上げ
            new_sl = max((t.sl or -float('inf')), close - trailing_atr_mult * atr_value)
            # エントリーより下にしない（ブレイクイーブン以上）
            new_sl = max(new_sl, t.entry_price)
            if t.sl is None or new_sl > t.sl:
                t.sl = new_sl

            # 部分利確: TP距離のpartial_tp_rr倍に初到達したとき
            tp_price = t.entry_price + atr_tp_mult * atr_value
            threshold = t.entry_price + partial_tp_rr * (tp_price - t.entry_price)
            if prev_close < threshold <= close:
                t.close(0.5)
        else:
            # ショートのトレーリングSL（価格 + k * ATR）を引き下げ
            new_sl = min((t.sl or float('inf')), close + trailing_atr_mult * atr_value)
            new_sl = min(new_sl, t.entry_price)
            if t.sl is None or new_sl < t.sl:
                t.sl = new_sl

            # 部分利確（ショート）
            tp_price = t.entry_price - atr_tp_mult * atr_value
            threshold = t.entry_price + partial_tp_rr * (tp_price - t.entry_price)
            if prev_close > threshold >= close:
                t.close(0.5)
