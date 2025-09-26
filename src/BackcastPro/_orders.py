"""
注文管理モジュール。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .order import Order


class _Orders(tuple):
    """
    TODO: このクラスを削除する。非推奨のためのみ。
    """
    def cancel(self):
        """すべての非条件付き（つまりSL/TP）注文をキャンセルします。"""
        for order in self:
            if not order.is_contingent:
                order.cancel()

    def __getattr__(self, item):
        # TODO: 前バージョンからの非推奨について警告する。次バージョンで削除。
        removed_attrs = ('entry', 'set_entry', 'is_long', 'is_short',
                         'sl', 'tp', 'set_sl', 'set_tp')
        if item in removed_attrs:
            raise AttributeError(f'Strategy.orders.{"/.".join(removed_attrs)} were removed in'
                                 'Backtesting 0.2.0. '
                                 'Use `Order` API instead. See docs.')
        raise AttributeError(f"'tuple' object has no attribute {item!r}")
