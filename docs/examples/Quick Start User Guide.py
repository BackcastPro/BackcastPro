import pandas as pd
from datetime import datetime, timedelta

from BackcastPro import Strategy
class SmaCross(Strategy):
   
    def init(self):
        pass
    
    def next(self):
        self.position.close()
        self.buy()


# データ取得
from BackcastPro.data.datareader import DataReader

df: pd.DataFrame = DataReader('72030')

from BackcastPro import Backtest
bt = Backtest(df, SmaCross, cash=10_000, commission=.002)
stats = bt.run()
stats
