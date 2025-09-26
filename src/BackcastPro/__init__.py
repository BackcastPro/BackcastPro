"""
## マニュアル

* [**クイックスタート ユーザーガイド**](../examples/Quick Start User Guide.html)

## チュートリアル

チュートリアルにはフレームワークのほとんどの機能が含まれているため、
すべてを通して読むことが重要で推奨されます。短時間で完了できます。

* [ユーティリティライブラリとコンポーザブルベースストラテジー](../examples/Strategies Library.html)
* [複数時間軸](../examples/Multiple Time Frames.html)
* [**パラメータヒートマップと最適化**](../examples/Parameter Heatmap &amp; Optimization.html)
* [機械学習を使ったトレーディング](../examples/Trading with Machine Learning.html)

これらのチュートリアルはライブJupyterノートブックとしても利用可能です：
[![Binder](https://mybinder.org/badge_logo.svg)][binder]
[![Google Colab](https://colab.research.google.com/assets/colab-badge.png)][colab]
<br>Colabでは、`!pip install backtesting`が必要な場合があります。

[binder]: \
    https://mybinder.org/v2/gh/kernc/backtesting.py/master?\
urlpath=lab%2Ftree%2Fdoc%2Fexamples%2FQuick%20Start%20User%20Guide.ipynb
[colab]: https://colab.research.google.com/github/kernc/backtesting.py/

## サンプルストラテジー

* （貢献を歓迎します）


.. tip::
    最近の変更の概要については、
    [新機能、すなわち **変更ログ**](https://github.com/kernc/backtesting.py/blob/master/CHANGELOG.md)をご覧ください。


## よくある質問

頻繁に寄せられる人気の質問への回答は、
[issue tracker](https://github.com/kernc/backtesting.py/issues?q=label%3Aquestion+-label%3Ainvalid)
またはGitHubの[ディスカッションフォーラム](https://github.com/kernc/backtesting.py/discussions)で見つけることができます。
検索機能をご利用ください！

## ライセンス

このソフトウェアは[AGPL 3.0]{: rel=license}の条件でライセンスされており、
合理的な目的で使用でき、作成した優秀なトレーディングストラテジーの完全な所有権を維持できますが、
_Backtesting.py_自体へのアップグレードがコミュニティに還元されることを推奨します。

[AGPL 3.0]: https://www.gnu.org/licenses/agpl-3.0.html

# APIリファレンスドキュメント
"""
try:
    from ._version import version as __version__
except ImportError:
    __version__ = '?.?.?'  # Package not installed

from . import lib  # noqa: F401
from ._plotting import set_bokeh_output  # noqa: F401
from .backtesting import Backtest, Strategy  # noqa: F401


# Add overridable backtesting.Pool used for parallel optimization
def Pool(processes=None, initializer=None, initargs=()):
    import multiprocessing as mp
    if mp.get_start_method() == 'spawn':
        import warnings
        warnings.warn(
            "If you want to use multi-process optimization with "
            "`multiprocessing.get_start_method() == 'spawn'` (e.g. on Windows),"
            "set `backtesting.Pool = multiprocessing.Pool` (or of the desired context) "
            "and hide `bt.optimize()` call behind a `if __name__ == '__main__'` guard. "
            "Currently using thread-based paralellism, "
            "which might be slightly slower for non-numpy / non-GIL-releasing code. "
            "See https://github.com/kernc/backtesting.py/issues/1256",
            category=RuntimeWarning, stacklevel=3)
        from multiprocessing.dummy import Pool
        return Pool(processes, initializer, initargs)
    else:
        return mp.Pool(processes, initializer, initargs)
