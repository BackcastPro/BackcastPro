import os
from os.path import dirname, join
import sys
# プロジェクトのルートフォルダをパスに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.insert(0, project_root)

import pandas as pd
import pandas_datareader.data as web

from BackcastPro import Strategy
from SmaCross import crossover, SMA
from Streamlit import plot

class SmaCross(Strategy):
    # Define the two MA lags as *class variables*
    # for later optimization
    n1 = 10
    n2 = 20
    
    def init(self):
        # 改修前のような単一銘柄アクセスのため、最初の銘柄を取得
        self.primary_code = next(iter(self.data.keys()))
        primary_data = self.data[self.primary_code]
        
        # Precompute the two moving averages (改修前と同じような方式)
        self.sma1 = SMA(primary_data.Close, self.n1)
        self.sma2 = SMA(primary_data.Close, self.n2)
    
    def next(self):
        # If sma1 crosses above sma2, close any existing
        # short trades, and buy the asset
        if crossover(self.sma1, self.sma2):
            self.position.close()
            self.buy(code=self.primary_code)

        # Else, if sma1 crosses below sma2, close any existing
        # long trades, and sell the asset
        elif crossover(self.sma2, self.sma1):
            self.position.close()
            self.sell(code=self.primary_code)


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

