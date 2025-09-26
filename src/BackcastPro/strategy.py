"""
コアフレームワークのデータ構造。
このモジュールのオブジェクトは、トップレベルモジュールから直接インポートすることもできます。例：

    from BackcastPro import Backtest, Strategy
"""

from __future__ import annotations

import sys
import warnings
from abc import ABCMeta, abstractmethod
from copy import copy
from functools import lru_cache, partial
from itertools import chain, product, repeat
from math import copysign
from numbers import Number
from typing import Callable, List, Optional, Sequence, Tuple, Type, Union

import numpy as np
import pandas as pd
from numpy.random import default_rng

from ._plotting import plot  # noqa: I001
from ._stats import compute_stats, dummy_stats
from ._util import (
    SharedMemoryManager, _as_str, _Indicator, _Data, _batch, _indicator_warmup_nbars,
    _strategy_indicators, patch, try_, _tqdm,
)

# Import classes from their new modules
from ._orders import _Orders
from ._exceptions import _OutOfMoneyError
from .order import Order
from .position import Position
from .trade import Trade
from ._broker import _Broker
from .backtest import Backtest

__pdoc__ = {
    'Strategy.__init__': False,
    'Order.__init__': False,
    'Position.__init__': False,
    'Trade.__init__': False,
}


class Strategy(metaclass=ABCMeta):
    """
    トレーディング戦略の基底クラス。このクラスを拡張し、
    `backtesting.backtesting.Strategy.init` と
    `backtesting.backtesting.Strategy.next` メソッドを
    オーバーライドして独自の戦略を定義してください。
    """
    def __init__(self, broker: _Broker, data: _Data, params):
        self._indicators = []
        self._broker: _Broker = broker
        self._data: _Data = data
        self._params = self._check_params(params)

    def __repr__(self):
        return '<Strategy ' + str(self) + '>'

    def __str__(self):
        params = ','.join(f'{i[0]}={i[1]}' for i in zip(self._params.keys(),
                                                        map(_as_str, self._params.values())))
        if params:
            params = '(' + params + ')'
        return f'{self.__class__.__name__}{params}'

    def _check_params(self, params):
        for k, v in params.items():
            if not hasattr(self, k):
                raise AttributeError(
                    f"戦略 '{self.__class__.__name__}' にパラメータ '{k}' がありません。"
                    "戦略クラスは、パラメータを最適化または実行する前に、"
                    "クラス変数としてパラメータを定義する必要があります。")
            setattr(self, k, v)
        return params

    def I(self,  # noqa: E743
          func: Callable, *args,
          name=None, plot=True, overlay=None, color=None, scatter=False,
          **kwargs) -> np.ndarray:
        """
        インジケーターを宣言します。インジケーターは単なる値の配列（MACDインジケーターの場合は配列のタプル）ですが、
        `backtesting.backtesting.Strategy.data` と同様に、`backtesting.backtesting.Strategy.next` で徐々に明らかになるものです。
        インジケーター値の `np.ndarray` を返します。

        `func` は、`backtesting.backtesting.Strategy.data` と同じ長さのインジケーター配列を返す関数です。

        プロットの凡例では、インジケーターは関数名でラベル付けされます（`name` で上書きされない限り）。
        `func` が配列のタプルを返す場合、`name` は文字列のシーケンスでもよく、
        そのサイズは返される配列の数と一致する必要があります。

        `plot` が `True` の場合、インジケーターは結果の `backtesting.backtesting.Backtest.plot` にプロットされます。

        `overlay` が `True` の場合、インジケーターは価格ローソク足チャートに重ねてプロットされます（移動平均線などに適しています）。
        `False` の場合、インジケーターはローソク足チャートの下に単独でプロットされます。デフォルトでは、ほとんどの場合正しく判定されるヒューリスティックが使用されます。

        `color` は、16進数の RGB 3値文字列または X11 の色名です。
        デフォルトでは、次に使用可能な色が割り当てられます。

        `scatter` が `True` の場合、プロットされるインジケーターマーカーは、接続された線分（デフォルト）ではなく円になります。

        追加の `*args` と `**kwargs` は `func` に渡され、パラメータとして使用できます。

        例えば、TA-Lib の単純移動平均関数を使用する場合：:

            def init():
                self.sma = self.I(ta.SMA, self.data.Close, self.n_sma)

        .. warning::
            ローリングインジケーターは、ウォームアップ値をNaNで埋め込む場合があります。
            この場合、**バックテストは、宣言されたすべてのインジケーターがNaN以外の値である場合にのみ最初のバーから開始されます**（例：200バーの移動平均線を使用する戦略の場合、バー番号201）。
            これは結果に影響を与える可能性があります。
        """
        def _format_name(name: str) -> str:
            return name.format(*map(_as_str, args),
                               **dict(zip(kwargs.keys(), map(_as_str, kwargs.values()))))

        if name is None:
            params = ','.join(filter(None, map(_as_str, chain(args, kwargs.values()))))
            func_name = _as_str(func)
            name = (f'{func_name}({params})' if params else f'{func_name}')
        elif isinstance(name, str):
            name = _format_name(name)
        elif try_(lambda: all(isinstance(item, str) for item in name), False):
            name = [_format_name(item) for item in name]
        else:
            raise TypeError(f'Unexpected `name=` type {type(name)}; expected `str` or '
                            '`Sequence[str]`')

        try:
            value = func(*args, **kwargs)
        except Exception as e:
            raise RuntimeError(f'インジケーター "{name}" エラー。上記のトレースバックを参照してください。') from e

        if isinstance(value, pd.DataFrame):
            value = value.values.T

        if value is not None:
            value = try_(lambda: np.asarray(value, order='C'), None)
        is_arraylike = bool(value is not None and value.shape)

        # Optionally flip the array if the user returned e.g. `df.values`
        if is_arraylike and np.argmax(value.shape) == 0:
            value = value.T

        if isinstance(name, list) and (np.atleast_2d(value).shape[0] != len(name)):
            raise ValueError(
                f'`name=` の長さ ({len(name)}) は、インジケーターが返す配列の数 '
                f'({value.shape[0]}) と一致する必要があります。')

        if not is_arraylike or not 1 <= value.ndim <= 2 or value.shape[-1] != len(self._data.Close):
            raise ValueError(
                'インジケーターは、`data` と同じ長さのnumpy配列（オプションでタプル）を返す必要があります '
                f'(データ形状: {self._data.Close.shape}; インジケーター "{name}" '
                f'形状: {getattr(value, "shape", "")}, 返された値: {value})')

        if overlay is None and np.issubdtype(value.dtype, np.number):
            x = value / self._data.Close
            # デフォルトでは、インジケーター値の大部分が終値の30%以内にある場合にオーバーレイ
            with np.errstate(invalid='ignore'):
                overlay = ((x < 1.4) & (x > .6)).mean() > .6

        value = _Indicator(value, name=name, plot=plot, overlay=overlay,
                           color=color, scatter=scatter,
                           # _Indicator.s シリーズアクセサがこれを使用：
                           index=self.data.index)
        self._indicators.append(value)
        return value

    @abstractmethod
    def init(self):
        """
        戦略を初期化します。
        このメソッドをオーバーライドしてください。
        インジケーターを宣言します（`backtesting.backtesting.Strategy.I`を使用）。
        戦略開始前に、事前計算が必要なものやベクトル化された方法で
        事前計算できるものを事前計算します。

        `backtesting.lib`からコンポーザブル戦略を拡張する場合は、
        必ず以下を呼び出してください：

            super().init()
        """

    @abstractmethod
    def next(self):
        """
        メインのストラテジー実行メソッド。新しい
        `backtesting.backtesting.Strategy.data`
        インスタンス（行；完全なローソク足バー）が利用可能になるたびに呼び出されます。
        これは、`backtesting.backtesting.Strategy.init`で
        事前計算されたデータに基づくストラテジーの意思決定が
        行われるメインメソッドです。

        `backtesting.lib`からコンポーザブルストラテジーを拡張する場合は、
        必ず以下を呼び出してください：

            super().next()
        """

    class __FULL_EQUITY(float):  # noqa: N801
        def __repr__(self): return '.9999'  # noqa: E704
    _FULL_EQUITY = __FULL_EQUITY(1 - sys.float_info.epsilon)

    def buy(self, *,
            size: float = _FULL_EQUITY,
            limit: Optional[float] = None,
            stop: Optional[float] = None,
            sl: Optional[float] = None,
            tp: Optional[float] = None,
            tag: object = None) -> 'Order':
        """
        新しいロングオーダーを発注し、それを返します。パラメータの説明については、
        `Order` とそのプロパティを参照してください。
        `Backtest(..., trade_on_close=True)` で実行していない限り、
        成行注文は次のバーの始値で約定され、
        その他の注文タイプ（指値、ストップ指値、ストップ成行）は
        それぞれの条件が満たされたときに約定されます。

        既存のポジションをクローズするには、`Position.close()` と `Trade.close()` を参照してください。

        `Strategy.sell()` も参照してください。
        """
        assert 0 < size < 1 or round(size) == size >= 1, \
            "sizeは正の資産割合または正の整数単位である必要があります"
        return self._broker.new_order(size, limit, stop, sl, tp, tag)

    def sell(self, *,
             size: float = _FULL_EQUITY,
             limit: Optional[float] = None,
             stop: Optional[float] = None,
             sl: Optional[float] = None,
             tp: Optional[float] = None,
             tag: object = None) -> 'Order':
        """
        新しいショートオーダーを発注し、それを返します。パラメータの説明については、
        `Order` とそのプロパティを参照してください。

        .. caution::
            `self.sell(size=.1)` は、以下の場合を除いて、
            既存の `self.buy(size=.1)` トレードをクローズしないことに注意してください：

            * バックテストが `exclusive_orders=True` で実行された場合、
            * 両方のケースで原資産価格が等しく、
              バックテストが `spread = commission = 0` で実行された場合。

            トレードを明示的に終了するには、`Trade.close()` または `Position.close()` を使用してください。

        `Strategy.buy()` も参照してください。

        .. note::
            既存のロングポジションをクローズしたいだけの場合は、
            `Position.close()` または `Trade.close()` を使用してください。
        """
        assert 0 < size < 1 or round(size) == size >= 1, \
            "sizeは正の資産割合または正の整数単位である必要があります"
        return self._broker.new_order(-size, limit, stop, sl, tp, tag)

    @property
    def equity(self) -> float:
        """現在のアカウント資産（現金プラス資産）。"""
        return self._broker.equity

    @property
    def data(self) -> _Data:
        """
        価格データは、`backtesting.backtesting.Backtest.__init__`に渡されるものと
        ほぼ同じですが、2つの重要な例外があります：

        * `data`はDataFrameではなく、パフォーマンスと利便性の理由で
          カスタマイズされたnumpy配列を提供するカスタム構造です。
          OHLCVカラム、`.index`、長さに加えて、最小価格変動単位である
          `.pip`プロパティを提供します。
        * `backtesting.backtesting.Strategy.init`内では、`data`配列は
          `backtesting.backtesting.Backtest.__init__`に渡された
          全長で利用可能です（指標の事前計算などに使用）。
          しかし、`backtesting.backtesting.Strategy.next`内では、
          `data`配列は現在のイテレーションの長さのみで、
          段階的な価格ポイントの開示をシミュレートします。
          `backtesting.backtesting.Strategy.next`の各呼び出し
          （`backtesting.backtesting.Backtest`によって内部的に
          反復的に呼び出される）では、最後の配列値
          （例：`data.Close[-1]`）は常に_最新_の値です。
        * データ配列（例：`data.Close`）を**Pandasシリーズ**として
          インデックス付きで必要とする場合は、`.s`アクセサを呼び出してください
          （例：`data.Close.s`）。データ全体を**DataFrame**として
          必要とする場合は、`.df`アクセサを使用してください
          （例：`data.df`）。
        """
        return self._data

    @property
    def position(self) -> 'Position':
        """`backtesting.backtesting.Position` のインスタンス。"""
        return self._broker.position

    @property
    def orders(self) -> 'Tuple[Order, ...]':
        """実行待ちのオーダーリスト（`Order` を参照）。"""
        return _Orders(self._broker.orders)

    @property
    def trades(self) -> 'Tuple[Trade, ...]':
        """アクティブなトレードリスト（`Trade` を参照）。"""
        return tuple(self._broker.trades)

    @property
    def closed_trades(self) -> 'Tuple[Trade, ...]':
        """決済済みトレードリスト（`Trade` を参照）。"""
        return tuple(self._broker.closed_trades)


# 注意: この __all__ リストの下にパブリックなものを配置しないでください

__all__ = [getattr(v, '__name__', k)
           for k, v in globals().items()                        # エクスポート
           if ((callable(v) and getattr(v, '__module__', None) == __name__ or  # このモジュールからの呼び出し可能オブジェクト; Python 3.9用getattr; # noqa: E501
                k.isupper()) and                                # または定数
               not getattr(v, '__name__', k).startswith('_'))]  # 内部マークされていない

# 注意: ここより下にパブリックなものを配置しないでください。上記を参照してください。