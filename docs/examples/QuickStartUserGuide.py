import os
from os.path import dirname, join
import sys
# プロジェクトのルートフォルダをパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, project_root)

import pandas as pd
import pandas_datareader.data as web

from BackcastPro import Strategy
from SmaCross import crossover
from Streamlit import plot

def SMA(values, n):
    """
    Return simple moving average of `values`, at
    each step taking into account `n` previous values.
    """
    return pd.Series(values).rolling(n).mean()

class SmaCross(Strategy):
    # Define the two MA lags as *class variables*
    # for later optimization
    n1 = 10
    n2 = 20
    
    def init(self):
        for code, df in self.data.items():
            # Precompute the two moving averages and add to data
            df['sma1'] = SMA(df.Close, self.n1)
            df['sma2'] = SMA(df.Close, self.n2)
            
    
    def next(self):

        if self.progress < self.n2:
            """Calculate the number of bars needed for indicators to warm up"""
            return

        for code, df in self.data.items():
            # If sma1 crosses above sma2, close any existing
            # short trades, and buy the asset
            if crossover(df.sma1, df.sma2):
                self.position.close()
                self.buy(code=code)

            # Else, if sma1 crosses below sma2, close any existing
            # long trades, and sell the asset
            elif crossover(df.sma2, df.sma1):
                self.position.close()
                self.sell(code=code)


# データ取得とバックテスト実行
from BackcastPro import Backtest

# データ取得
code='GOOG'
df = pd.read_csv(join(dirname(__file__), f'{code}.csv'),
                       index_col=0, parse_dates=True)

bt = Backtest({code: df}, SmaCross, cash=10_000, commission=.002, finalize_trades=False)
stats = bt.run()
print(stats)


# Streamlit で表示
# page_title = os.path.splitext(os.path.basename(__file__))[0]
# plot(page_title, bt)

