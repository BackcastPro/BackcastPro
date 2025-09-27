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
from BackcastPro.data import TOYOTA

from BackcastPro import Backtest
bt = Backtest(TOYOTA, SmaCross, cash=10_000, commission=.002, finalize_trades=True)
stats = bt.run()
stats
