import pandas as pd


def calculate_rsi(data, window=14):
    """RSI計算"""
    delta = data['Close'].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(window, min_periods=window).mean()
    avg_loss = loss.rolling(window, min_periods=window).mean()
    rs = avg_gain / (avg_loss.replace(0, pd.NA))
    return 100 - (100 / (1 + rs))


def calculate_atr(data, window=14):
    """ATR計算"""
    high = data['High']
    low = data['Low']
    close = data['Close']
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=window).mean()


def crossover(sma1, sma2):
    """クロスオーバー検出（lib.pyのcross_over関数を簡略化）"""
    if len(sma1) < 2 or len(sma2) < 2:
        return False
    if pd.isna(sma1.iloc[-2]) or pd.isna(sma2.iloc[-2]) or pd.isna(sma1.iloc[-1]) or pd.isna(sma2.iloc[-1]):
        return False
    return (sma1.iloc[-2] <= sma2.iloc[-2]) and (sma1.iloc[-1] > sma2.iloc[-1])

