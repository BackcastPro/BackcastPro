import os
import sys
sys.path.append('../../src')

import pandas_datareader.data as web

from BackcastPro import Strategy
from SmaCross import crossover, calculate_rsi, calculate_atr
from Streamlit import plot

class SmaCross(Strategy):
    # Define the two MA lags as *class variables*
    # for later optimization
    n1 = 10
    n2 = 20
    
    def init(self):
        for code, df in self.data.items():
            # Precompute the two moving averages and add to data
            df['SMA1'] = df.Close.rolling(self.n1).mean()
            df['SMA2'] = df.Close.rolling(self.n2).mean()
            
            # Calculate RSI and ATR for risk management and add to data
            df['RSI'] = calculate_rsi(df)
            df['ATR'] = calculate_atr(df)
    
    def next(self):
        for code, df in self.data.items():
            # If sma1 crosses above sma2, close any existing
            # short trades, and buy the asset
            if crossover(df.SMA1, df.SMA2):
                self.buy(code=code)

            # Else, if sma1 crosses below sma2, close any existing
            # long trades, and sell the asset
            elif crossover(df.SMA2, df.SMA1):
                self.sell(code=code)


# データ取得とバックテスト実行
from BackcastPro import Backtest

# データ取得（例: トヨタ 7203）
code='7203.JP'
df = web.DataReader(code, 'stooq')
bt = Backtest({code: df}, SmaCross, cash=10_000, commission=.002, finalize_trades=True)
stats = bt.run()
print(stats)

# Streamlit で表示
page_title = os.path.splitext(os.path.basename(__file__))[0]
plot(page_title, bt)



