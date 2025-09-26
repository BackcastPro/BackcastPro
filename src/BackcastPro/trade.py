"""
取引管理モジュール。
"""

import numpy as np
import pandas as pd
from copy import copy
from math import copysign
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from ._broker import _Broker
    from .order import Order


class Trade:
    """
    `Order`が約定されると、アクティブな`Trade`が発生します。
    アクティブな取引は`Strategy.trades`で、クローズされた決済済み取引は`Strategy.closed_trades`で見つけることができます。
    """
    def __init__(self, broker: '_Broker', size: int, entry_price: float, entry_bar, tag):
        self.__broker = broker
        self.__size = size
        self.__entry_price = entry_price
        self.__exit_price: Optional[float] = None
        self.__entry_bar: int = entry_bar
        self.__exit_bar: Optional[int] = None
        self.__sl_order: Optional[Order] = None
        self.__tp_order: Optional[Order] = None
        self.__tag = tag
        self._commissions = 0

    def __repr__(self):
        return f'<Trade size={self.__size} time={self.__entry_bar}-{self.__exit_bar or ""} ' \
               f'price={self.__entry_price}-{self.__exit_price or ""} pl={self.pl:.0f}' \
               f'{" tag=" + str(self.__tag) if self.__tag is not None else ""}>'

    def _replace(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, f'_{self.__class__.__qualname__}__{k}', v)
        return self

    def _copy(self, **kwargs):
        return copy(self)._replace(**kwargs)

    def close(self, portion: float = 1.):
        """次の市場価格で取引の`portion`をクローズする新しい`Order`を出します。"""
        assert 0 < portion <= 1, "portion must be a fraction between 0 and 1"
        # Ensure size is an int to avoid rounding errors on 32-bit OS
        size = copysign(max(1, int(round(abs(self.__size) * portion))), -self.__size)
        from .order import Order
        order = Order(self.__broker, size, parent_trade=self, tag=self.__tag)
        self.__broker.orders.insert(0, order)

    # Fields getters

    @property
    def size(self):
        """取引サイズ（ボリューム；ショート取引の場合は負の値）。"""
        return self.__size

    @property
    def entry_price(self) -> float:
        """取引エントリー価格。"""
        return self.__entry_price

    @property
    def exit_price(self) -> Optional[float]:
        """取引エグジット価格（取引がまだアクティブな場合はNone）。"""
        return self.__exit_price

    @property
    def entry_bar(self) -> int:
        """取引がエントリーされた時のローソク足バーのインデックス。"""
        return self.__entry_bar

    @property
    def exit_bar(self) -> Optional[int]:
        """
        取引がエグジットされた時のローソク足バーのインデックス
        （取引がまだアクティブな場合はNone）。
        """
        return self.__exit_bar

    @property
    def tag(self):
        """
        この取引を開始した`Order`から継承されたタグ値。

        取引の追跡や条件付きロジック/サブグループ分析に使用できます。

        `Order.tag`も参照してください。
        """
        return self.__tag

    @property
    def _sl_order(self):
        return self.__sl_order

    @property
    def _tp_order(self):
        return self.__tp_order

    # Extra properties

    @property
    def entry_time(self) -> Union[pd.Timestamp, int]:
        """取引がエントリーされた日時。"""
        return self.__broker._data.index[self.__entry_bar]

    @property
    def exit_time(self) -> Optional[Union[pd.Timestamp, int]]:
        """取引がエグジットされた日時。"""
        if self.__exit_bar is None:
            return None
        return self.__broker._data.index[self.__exit_bar]

    @property
    def is_long(self):
        """取引がロングの場合True（取引サイズが正の値）。"""
        return self.__size > 0

    @property
    def is_short(self):
        """取引がショートの場合True（取引サイズが負の値）。"""
        return not self.is_long

    @property
    def pl(self):
        """
        取引の利益（正の値）または損失（負の値）を現金単位で表示。
        手数料は取引がクローズされた後にのみ反映されます。
        """
        price = self.__exit_price or self.__broker.last_price
        return (self.__size * (price - self.__entry_price)) - self._commissions

    @property
    def pl_pct(self):
        """取引の利益（正の値）または損失（負の値）をパーセントで表示。"""
        price = self.__exit_price or self.__broker.last_price
        gross_pl_pct = copysign(1, self.__size) * (price / self.__entry_price - 1)

        # 取引全体のサイズに対する手数料を個別単位に換算
        commission_pct = self._commissions / (abs(self.__size) * self.__entry_price)
        return gross_pl_pct - commission_pct

    @property
    def value(self):
        """取引の総価値を現金単位で表示（ボリューム × 価格）。"""
        price = self.__exit_price or self.__broker.last_price
        return abs(self.__size) * price

    # SL/TP management API

    @property
    def sl(self):
        """
        取引をクローズするストップロス価格。

        この変数は書き込み可能です。新しい価格値を割り当てることで、
        既存のSLオーダーを作成または修正します。
        `None`を割り当てることでキャンセルできます。
        """
        return self.__sl_order and self.__sl_order.stop

    @sl.setter
    def sl(self, price: float):
        self.__set_contingent('sl', price)

    @property
    def tp(self):
        """
        取引をクローズするテイクプロフィット価格。

        このプロパティは書き込み可能です。新しい価格値を割り当てることで、
        既存のTPオーダーを作成または修正します。
        `None`を割り当てることでキャンセルできます。
        """
        return self.__tp_order and self.__tp_order.limit

    @tp.setter
    def tp(self, price: float):
        self.__set_contingent('tp', price)

    def __set_contingent(self, type, price):
        assert type in ('sl', 'tp')
        assert price is None or 0 < price < np.inf, f'Make sure 0 < price < inf! price: {price}'
        attr = f'_{self.__class__.__qualname__}__{type}_order'
        order: Order = getattr(self, attr)
        if order:
            order.cancel()
        if price:
            kwargs = {'stop': price} if type == 'sl' else {'limit': price}
            order = self.__broker.new_order(-self.size, trade=self, tag=self.tag, **kwargs)
            setattr(self, attr, order)
