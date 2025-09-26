from BackcastPro import Strategy

class SmaCross(Strategy):
   
    def init(self):
        pass
    
    def next(self):
        self.position.close()
        self.buy()


from BackcastPro import Backtest

bt = Backtest(GOOG, SmaCross, cash=10_000, commission=.002)
stats = bt.run()
stats
