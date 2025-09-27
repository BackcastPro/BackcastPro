import os
import sys
sys.path.append('../../src')

from BackcastPro import Strategy
from SmaCross import crossover, calculate_rsi, calculate_atr, position_size_by_risk
from Streamlit import plot

class SmaCross(Strategy):
    # Define the two MA lags as *class variables*
    # for later optimization
    n1 = 10
    n2 = 20
    
    def init(self):
        # Precompute the two moving averages and add to data
        self.data['SMA1'] = self.data.Close.rolling(self.n1).mean()
        self.data['SMA2'] = self.data.Close.rolling(self.n2).mean()
        
        # Calculate RSI and ATR for risk management and add to data
        self.data['RSI'] = calculate_rsi(self.data)
        self.data['ATR'] = calculate_atr(self.data)
    
    def next(self):
        # If sma1 crosses above sma2, close any existing
        # short trades, and buy the asset
        if crossover(self.data.SMA1, self.data.SMA2):
            self.position.close()
            self.buy()

        # Else, if sma1 crosses below sma2, close any existing
        # long trades, and sell the asset
        elif crossover(self.data.SMA2, self.data.SMA1):
            self.position.close()
            self.sell()


# データ取得とバックテスト実行
from BackcastPro.data import DataReader
from BackcastPro import Backtest

# データ取得（例: トヨタ 7203）
data = DataReader('7203')
bt = Backtest(data, SmaCross, cash=10_000, commission=.002, finalize_trades=True)
stats = bt.run()
print(stats)

# Streamlit で表示
page_title = os.path.splitext(os.path.basename(__file__))[0]
plot(page_title, bt)