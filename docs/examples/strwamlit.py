import sys
sys.path.append('../../src')

import pandas as pd
from datetime import datetime, timedelta

import streamlit as st

from BackcastPro import Strategy, Backtest
from BackcastPro.data import DataReader

from SmaCross import crossover, calculate_rsi, calculate_atr, position_size_by_risk


class SmaCross(Strategy):
    n1 = 10
    n2 = 20

    def init(self):
        self.data['SMA1'] = self.data.Close.rolling(self.n1).mean()
        self.data['SMA2'] = self.data.Close.rolling(self.n2).mean()
        self.data['RSI'] = calculate_rsi(self.data)
        self.data['ATR'] = calculate_atr(self.data)

    def next(self):
        if crossover(self.data.SMA1, self.data.SMA2):
            self.position.close()
            stop_distance = 2.0 * self.data.ATR.iloc[-1]
            units = position_size_by_risk(self.equity, 0.02, stop_distance)
            if units > 0:
                self.buy(size=units, sl=self.data.Close.iloc[-1] - stop_distance)
        elif crossover(self.data.SMA2, self.data.SMA1):
            self.position.close()
            stop_distance = 2.0 * self.data.ATR.iloc[-1]
            units = position_size_by_risk(self.equity, 0.02, stop_distance)
            if units > 0:
                self.sell(size=units, sl=self.data.Close.iloc[-1] + stop_distance)


st.set_page_config(page_title='BackcastPro Streamlit', layout='wide')
st.title('BackcastPro Quick Start - Streamlit')

with st.sidebar:
    st.header('設定')
    code = st.text_input('銘柄コード', value='72030')
    years = st.slider('取得年数', min_value=1, max_value=10, value=1)
    cash = st.number_input('初期資金', value=10000, step=1000)
    commission = st.number_input('手数料（率）', value=0.002, step=0.001, format='%.4f')
    run = st.button('実行')

if run:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)

    with st.spinner('データ取得中...'):
        data = DataReader(code, start_date, end_date)

    if data is None or len(data) == 0:
        st.error('データが取得できませんでした。コードや期間を確認してください。')
        st.stop()

    st.subheader('価格データ（終値）')
    st.line_chart(data[['Close']])

    bt = Backtest(data, SmaCross, cash=cash, commission=commission)

    with st.spinner('バックテスト実行中...'):
        stats = bt.run()

    # 成績表（Backtesting.pyの出力に相当）
    excluded = {'_strategy', '_equity_curve', '_trades'}
    scalar_stats = {}
    for k, v in stats.items():
        if k in excluded:
            continue
        if isinstance(v, (pd.DataFrame, pd.Series)):
            continue
        if hasattr(v, 'components') and hasattr(v, 'total_seconds'):
            # timedeltaを文字列化
            scalar_stats[k] = str(v)
        else:
            scalar_stats[k] = v

    st.subheader('成績サマリ')
    summary_df = pd.DataFrame(scalar_stats, index=[0]).T
    summary_df.columns = ['Value']
    st.table(summary_df)

    # エクイティカーブとドローダウン
    st.subheader('エクイティ・ドローダウン')
    equity_df = stats['_equity_curve'][['Equity', 'DrawdownPct']]
    st.line_chart(equity_df)

    # トレード一覧
    st.subheader('トレード一覧')
    trades_df = stats['_trades']
    st.dataframe(trades_df)

    # 価格にエントリー/エグジットを重ねた簡易可視化
    st.subheader('価格とエントリー（簡易）')
    close = data['Close'].rename('Close')
    buy_points = pd.Series(index=data.index, dtype=float, name='Buy')
    sell_points = pd.Series(index=data.index, dtype=float, name='Sell')
    for row in trades_df.itertuples(index=False):
        if pd.notna(row.EntryTime):
            if row.Size > 0:
                buy_points.loc[row.EntryTime] = row.EntryPrice
            elif row.Size < 0:
                sell_points.loc[row.EntryTime] = row.EntryPrice
    plot_df = pd.concat([close, buy_points, sell_points], axis=1)
    st.line_chart(plot_df)


