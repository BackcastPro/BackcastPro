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
            # Calculate position size based on risk
            stop_distance = 2.0 * self.data.ATR.iloc[-1]
            units = position_size_by_risk(self.equity, 0.02, stop_distance)
            if units > 0:
                self.buy(size=units, sl=self.data.Close.iloc[-1] - stop_distance)

        # Else, if sma1 crosses below sma2, close any existing
        # long trades, and sell the asset
        elif crossover(self.data.SMA2, self.data.SMA1):
            self.position.close()
            # Calculate position size based on risk
            stop_distance = 2.0 * self.data.ATR.iloc[-1]
            units = position_size_by_risk(self.equity, 0.02, stop_distance)
            if units > 0:
                self.sell(size=units, sl=self.data.Close.iloc[-1] + stop_distance)


# データ取得とバックテスト実行
from BackcastPro.data import TOYOTA
from BackcastPro import Backtest

bt = Backtest(TOYOTA, SmaCross, cash=10_000, commission=.002)
stats = bt.run()
print(stats)

# Streamlit で表示
filename_without_ext = os.path.splitext(os.path.basename(__file__))[0]
plot(filename_without_ext, bt)