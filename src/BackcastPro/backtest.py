"""
バックテスト管理モジュール。
"""

import warnings
from functools import partial
from numbers import Number
from typing import Optional, Tuple, Type, Union

import numpy as np
import pandas as pd
from tqdm import tqdm # プログレスバー

from ._broker import _Broker
from ._stats import compute_stats


class Backtest:
    """
    特定のデータに対して特定の（パラメータ化された）戦略をバックテストします。

    バックテストを初期化します。テストするデータと戦略が必要です。
    初期化後、バックテストインスタンスを実行するために
    `Backtest.run`メソッドを呼び出す。

    `data`は以下の列を持つ`pd.DataFrame`です：
    `Open`, `High`, `Low`, `Close`, および（オプションで）`Volume`。
    列が不足している場合は、利用可能なものに設定してください。
    例：

        df['Open'] = df['High'] = df['Low'] = df['Close']

    渡されたデータフレームには、戦略で使用できる追加の列
    （例：センチメント情報）を含めることができます。
    DataFrameのインデックスは、datetimeインデックス（タイムスタンプ）または
    単調増加の範囲インデックス（期間のシーケンス）のいずれかです。

    `strategy`は`Strategy`の
    _サブクラス_（インスタンスではありません）です。

    `cash`は開始時の初期現金です。

    `spread`は一定のビッドアスクスプレッド率（価格に対する相対値）です。
    例：平均スプレッドがアスク価格の約0.2‰である手数料なしの
    外国為替取引では`0.0002`に設定してください。

    `commission`は手数料率です。例：ブローカーの手数料が
    注文価値の1%の場合、commissionを`0.01`に設定してください。
    手数料は2回適用されます：取引開始時と取引終了時です。
    単一の浮動小数点値に加えて、`commission`は浮動小数点値の
    タプル`(fixed, relative)`にすることもできます。例：ブローカーが
    最低$100 + 1%を請求する場合は`(100, .01)`に設定してください。
    さらに、`commission`は呼び出し可能な
    `func(order_size: int, price: float) -> float`
    （注：ショート注文では注文サイズは負の値）にすることもでき、
    より複雑な手数料構造をモデル化するために使用できます。
    負の手数料値はマーケットメーカーのリベートとして解釈されます。

    `margin`はレバレッジアカウントの必要証拠金（比率）です。
    初期証拠金と維持証拠金の区別はありません。
    ブローカーが許可する50:1レバレッジなどでバックテストを実行するには、
    marginを`0.02`（1 / レバレッジ）に設定してください。

    `trade_on_close`が`True`の場合、成行注文は
    次のバーの始値ではなく、現在のバーの終値で約定されます。

    `hedging`が`True`の場合、両方向の取引を同時に許可します。
    `False`の場合、反対方向の注文は既存の取引を
    [FIFO]方式で最初にクローズします。

    `exclusive_orders`が`True`の場合、各新しい注文は前の
    取引/ポジションを自動クローズし、各時点で最大1つの取引
    （ロングまたはショート）のみが有効になります。

    `finalize_trades`が`True`の場合、バックテスト終了時に
    まだ[アクティブで継続中]の取引は最後のバーでクローズされ、
    計算されたバックテスト統計に貢献します。
    """  
    def __init__(self,
                 data: pd.DataFrame,
                 strategy: Type,
                 *,
                 cash: float = 10_000,
                 spread: float = .0,
                 commission: Union[float, Tuple[float, float]] = .0,
                 margin: float = 1.,
                 trade_on_close=False,
                 hedging=False,
                 exclusive_orders=False,
                 finalize_trades=False,
                 ):
        # 循環インポートを避けるためにここでインポート
        from .strategy import Strategy
        
        if not (isinstance(strategy, type) and issubclass(strategy, Strategy)):
            raise TypeError('`strategy` must be a Strategy sub-type')
        if not isinstance(data, pd.DataFrame):
            raise TypeError("`data` must be a pandas.DataFrame with columns")
        if not isinstance(spread, Number):
            raise TypeError('`spread` must be a float value, percent of '
                            'entry order price')
        if not isinstance(commission, (Number, tuple)) and not callable(commission):
            raise TypeError('`commission` must be a float percent of order value, '
                            'a tuple of `(fixed, relative)` commission, '
                            'or a function that takes `(order_size, price)`'
                            'and returns commission dollar value')

        data = data.copy(deep=False)

        # インデックスをdatetimeインデックスに変換
        if (not isinstance(data.index, pd.DatetimeIndex) and
            not isinstance(data.index, pd.RangeIndex) and
            # 大部分が大きな数値の数値インデックス
            (data.index.is_numeric() and
             (data.index > pd.Timestamp('1975').timestamp()).mean() > .8)):
            try:
                data.index = pd.to_datetime(data.index, infer_datetime_format=True)
            except ValueError:
                pass

        if 'Volume' not in data:
            data['Volume'] = np.nan

        if len(data) == 0:
            raise ValueError('OHLC `data` is empty')
        if len(data.columns.intersection({'Open', 'High', 'Low', 'Close', 'Volume'})) != 5:
            raise ValueError("`data` must be a pandas.DataFrame with columns "
                             "'Open', 'High', 'Low', 'Close', and (optionally) 'Volume'")
        if data[['Open', 'High', 'Low', 'Close']].isnull().values.any():
            raise ValueError('Some OHLC values are missing (NaN). '
                             'Please strip those lines with `df.dropna()` or '
                             'fill them in with `df.interpolate()` or whatever.')
        if np.any(data['Close'] > cash):
            warnings.warn('Some prices are larger than initial cash value. Note that fractional '
                          'trading is not supported by this class. If you want to trade Bitcoin, '
                          'increase initial cash, or trade μBTC or satoshis instead (see e.g. class '
                          '`backtesting.lib.FractionalBacktest`.',
                          stacklevel=2)
        if not data.index.is_monotonic_increasing:
            warnings.warn('Data index is not sorted in ascending order. Sorting.',
                          stacklevel=2)
            data = data.sort_index()
        if not isinstance(data.index, pd.DatetimeIndex):
            warnings.warn('Data index is not datetime. Assuming simple periods, '
                          'but `pd.DateTimeIndex` is advised.',
                          stacklevel=2)

        self._data: pd.DataFrame = data

        # partialとは、関数の一部の引数を事前に固定して、新しい関数を作成します。
        # これにより、後で残りの引数だけを渡せば関数を実行できるようになります。
        # 1. _Brokerクラスのコンストラクタの引数の一部（cash, spread, commissionなど）を事前に固定
        # 2. 新しい関数（実際には呼び出し可能オブジェクト）を作成
        # 3. 後で残りの引数（おそらくdataなど）を渡すだけで_Brokerのインスタンスを作成できるようにする
        self._broker = partial(
            _Broker, cash=cash, spread=spread, commission=commission, margin=margin,
            trade_on_close=trade_on_close, hedging=hedging,
            exclusive_orders=exclusive_orders, index=data.index,
        )

        self._strategy = strategy
        self._results: Optional[pd.Series] = None
        self._finalize_trades = bool(finalize_trades)
        

    def run(self) -> pd.Series:
        """
        バックテストを実行します。結果と統計を含む `pd.Series` を返します。

        キーワード引数は戦略パラメータとして解釈されます。

            >>> Backtest(GOOG, SmaCross).run()
            Start                     2004-08-19 00:00:00
            End                       2013-03-01 00:00:00
            Duration                   3116 days 00:00:00
            Exposure Time [%]                    96.74115
            Equity Final [$]                     51422.99
            Equity Peak [$]                      75787.44
            Return [%]                           414.2299
            Buy & Hold Return [%]               703.45824
            Return (Ann.) [%]                    21.18026
            Volatility (Ann.) [%]                36.49391
            CAGR [%]                             14.15984
            Sharpe Ratio                          0.58038
            Sortino Ratio                         1.08479
            Calmar Ratio                          0.44144
            Alpha [%]                           394.37391
            Beta                                  0.03803
            Max. Drawdown [%]                   -47.98013
            Avg. Drawdown [%]                    -5.92585
            Max. Drawdown Duration      584 days 00:00:00
            Avg. Drawdown Duration       41 days 00:00:00
            # Trades                                   66
            Win Rate [%]                          46.9697
            Best Trade [%]                       53.59595
            Worst Trade [%]                     -18.39887
            Avg. Trade [%]                        2.53172
            Max. Trade Duration         183 days 00:00:00
            Avg. Trade Duration          46 days 00:00:00
            Profit Factor                         2.16795
            Expectancy [%]                        3.27481
            SQN                                   1.07662
            Kelly Criterion                       0.15187
            _strategy                            SmaCross
            _equity_curve                           Eq...
            _trades                       Size  EntryB...
            dtype: object

        .. warning::
            異なる戦略パラメータに対して異なる結果が得られる場合があります。
            例：50本と200本のSMAを使用する場合、取引シミュレーションは
            201本目から開始されます。実際の遅延の長さは、最も遅延する
            `Strategy.I`インジケーターのルックバック期間に等しくなります。
            明らかに、これは結果に影響を与える可能性があります。
        """
        # 循環インポートを避けるためにここでインポート
        from .strategy import Strategy
        
        data = self._data.copy(deep=False)
        broker: _Broker = self._broker(data=data)
        strategy: Strategy = self._strategy(broker, data)

        strategy.init()

        # strategy.init()で加工されたdataを再登録
        self._data = data
        
        # インジケーターがまだ「ウォームアップ」中の最初の数本のキャンドルをスキップ
        # 少なくとも2つのエントリが利用可能になるように+1
        start = 1

        # "invalid value encountered in ..."警告を無効化。比較
        # np.nan >= 3は無効ではない；Falseです。
        with np.errstate(invalid='ignore'):

            # プログレスバーを表示
            progress_bar = tqdm(range(start, len(self._data)), 
                              desc="バックテスト実行中", 
                              unit="step",
                              ncols=120,
                              leave=True,
                              dynamic_ncols=True)
            
            for i in progress_bar:
                # 注文処理とブローカー関連の処理
                data = self._data.iloc[:i]
                try:
                    broker._data = data
                    broker.next()
                except:
                    break

                # 次のティック、バークローズ直前
                strategy._data = data
                strategy.next()
                
                # プログレスバーの説明を更新（現在の日付を表示）
                if hasattr(self._data.index, 'strftime') and i > 0:
                    try:
                        current_date = self._data.index[i-1].strftime('%Y-%m-%d')
                        progress_bar.set_postfix({"日付": current_date})
                    except:
                        pass
            else:
                if self._finalize_trades is True:
                    # 統計を生成するために残っているオープン取引をクローズ
                    for trade in reversed(broker.trades):
                        trade.close()

                    # HACK: 最後の戦略イテレーションで配置されたクローズ注文を処理するために
                    #  ブローカーを最後にもう一度実行。最後のブローカーイテレーションと同じOHLC値を使用。
                    if start < len(self._data):
                        broker.next()
                elif len(broker.trades):
                    warnings.warn(
                        'バックテスト終了時に一部の取引がオープンのままです。'
                        '`Backtest(..., finalize_trades=True)`を使用してクローズし、'
                        '統計に含めてください。', stacklevel=2)

            equity = pd.Series(broker._equity).bfill().fillna(broker._cash).values
            self._results = compute_stats(
                trades=broker.closed_trades,
                equity=equity,
                ohlc_data=self._data,
                strategy_instance=strategy,
                risk_free_rate=0.0,
            )

        return self._results


    @property
    def cash(self):
        # partialで初期化されている場合、初期化時のcash値を返す
        return self._broker.keywords.get('cash', 0)

   
    @property
    def commission(self):
        # partialで初期化されている場合、初期化時のcommission値を返す
        return self._broker.keywords.get('commission', 0)   
