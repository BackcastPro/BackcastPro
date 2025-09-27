import pandas as pd
from datetime import datetime, timedelta

# from BackcastPro import Strategy
# class SmaCross(Strategy):
   
#     def init(self):
#         pass
    
#     def next(self):
#         self.position.close()
#         self.buy()



# データ取得
from BackcastPro.data import DataReader as web

## 開始日、終了日を指定する場合1
end_date = datetime.now()
start_date = end_date - timedelta(days=365)
df1: pd.DataFrame = web.DataReader('7203', start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

## 開始日、終了日を指定する場合2
df2: pd.DataFrame = web.DataReader('7203', start_date, end_date)

## 開始日、終了日を指定しない場合
df3: pd.DataFrame = web.DataReader('7203')


# from BackcastPro import Backtest
# bt = Backtest(df, SmaCross, cash=10_000, commission=.002)
# stats = bt.run()
# stats
