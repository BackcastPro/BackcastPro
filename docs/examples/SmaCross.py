import pandas as pd

def crossover(sma1, sma2):
    """クロスオーバー検出（lib.pyのcross_over関数を簡略化）"""
    if len(sma1) < 2 or len(sma2) < 2:
        return False
    if pd.isna(sma1.iloc[-2]) or pd.isna(sma2.iloc[-2]) or pd.isna(sma1.iloc[-1]) or pd.isna(sma2.iloc[-1]):
        return False
    return (sma1.iloc[-2] <= sma2.iloc[-2]) and (sma1.iloc[-1] > sma2.iloc[-1])

