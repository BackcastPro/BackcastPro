"""
Backtest management module.
"""

import sys
import warnings
from copy import copy
from functools import lru_cache, partial
from itertools import chain, product, repeat
from math import copysign
from numbers import Number
from typing import Callable, List, Optional, Sequence, Tuple, Type, Union

import numpy as np
import pandas as pd
from numpy.random import default_rng

from ._broker import _Broker
from ._exceptions import _OutOfMoneyError
from ._plotting import plot  # noqa: I001
from ._stats import compute_stats, dummy_stats
from ._util import (
    SharedMemoryManager, _as_str, _Indicator, _Data, _batch, _indicator_warmup_nbars,
    _strategy_indicators, patch, try_, _tqdm,
)


class Backtest:
    """
    Backtest a particular (parameterized) strategy
    on particular data.

    Initialize a backtest. Requires data and a strategy to test.
    After initialization, you can call method
    `backtesting.backtesting.Backtest.run` to run a backtest
    instance, or `backtesting.backtesting.Backtest.optimize` to
    optimize it.

    `data` is a `pd.DataFrame` with columns:
    `Open`, `High`, `Low`, `Close`, and (optionally) `Volume`.
    If any columns are missing, set them to what you have available,
    e.g.

        df['Open'] = df['High'] = df['Low'] = df['Close']

    The passed data frame can contain additional columns that
    can be used by the strategy (e.g. sentiment info).
    DataFrame index can be either a datetime index (timestamps)
    or a monotonic range index (i.e. a sequence of periods).

    `strategy` is a `backtesting.backtesting.Strategy`
    _subclass_ (not an instance).

    `cash` is the initial cash to start with.

    `spread` is the the constant bid-ask spread rate (relative to the price).
    E.g. set it to `0.0002` for commission-less forex
    trading where the average spread is roughly 0.2‰ of the asking price.

    `commission` is the commission rate. E.g. if your broker's commission
    is 1% of order value, set commission to `0.01`.
    The commission is applied twice: at trade entry and at trade exit.
    Besides one single floating value, `commission` can also be a tuple of floating
    values `(fixed, relative)`. E.g. set it to `(100, .01)`
    if your broker charges minimum $100 + 1%.
    Additionally, `commission` can be a callable
    `func(order_size: int, price: float) -> float`
    (note, order size is negative for short orders),
    which can be used to model more complex commission structures.
    Negative commission values are interpreted as market-maker's rebates.

    .. note::
        Before v0.4.0, the commission was only applied once, like `spread` is now.
        If you want to keep the old behavior, simply set `spread` instead.

    .. note::
        With nonzero `commission`, long and short orders will be placed
        at an adjusted price that is slightly higher or lower (respectively)
        than the current price. See e.g.
        [#153](https://github.com/kernc/backtesting.py/issues/153),
        [#538](https://github.com/kernc/backtesting.py/issues/538),
        [#633](https://github.com/kernc/backtesting.py/issues/633).

    `margin` is the required margin (ratio) of a leveraged account.
    No difference is made between initial and maintenance margins.
    To run the backtest using e.g. 50:1 leverge that your broker allows,
    set margin to `0.02` (1 / leverage).

    If `trade_on_close` is `True`, market orders will be filled
    with respect to the current bar's closing price instead of the
    next bar's open.

    If `hedging` is `True`, allow trades in both directions simultaneously.
    If `False`, the opposite-facing orders first close existing trades in
    a [FIFO] manner.

    If `exclusive_orders` is `True`, each new order auto-closes the previous
    trade/position, making at most a single trade (long or short) in effect
    at each time.

    If `finalize_trades` is `True`, the trades that are still
    [active and ongoing] at the end of the backtest will be closed on
    the last bar and will contribute to the computed backtest statistics.

    .. tip:: Fractional trading
        See also `backtesting.lib.FractionalBacktest` if you want to trade
        fractional units (of e.g. bitcoin).

    [FIFO]: https://www.investopedia.com/terms/n/nfa-compliance-rule-2-43b.asp
    [active and ongoing]: https://kernc.github.io/backtesting.py/doc/backtesting/backtesting.html#backtesting.backtesting.Strategy.trades
    """  # noqa: E501
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
        # Import here to avoid circular imports
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

        # Convert index to datetime index
        if (not isinstance(data.index, pd.DatetimeIndex) and
            not isinstance(data.index, pd.RangeIndex) and
            # Numeric index with most large numbers
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
        self._broker = partial(
            _Broker, cash=cash, spread=spread, commission=commission, margin=margin,
            trade_on_close=trade_on_close, hedging=hedging,
            exclusive_orders=exclusive_orders, index=data.index,
        )
        self._strategy = strategy
        self._results: Optional[pd.Series] = None
        self._finalize_trades = bool(finalize_trades)

    def run(self, **kwargs) -> pd.Series:
        """
        Run the backtest. Returns `pd.Series` with results and statistics.

        Keyword arguments are interpreted as strategy parameters.

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
            You may obtain different results for different strategy parameters.
            E.g. if you use 50- and 200-bar SMA, the trading simulation will
            begin on bar 201. The actual length of delay is equal to the lookback
            period of the `Strategy.I` indicator which lags the most.
            Obviously, this can affect results.
        """
        # Import here to avoid circular imports
        from .strategy import Strategy
        
        data = _Data(self._data.copy(deep=False))
        broker: _Broker = self._broker(data=data)
        strategy: Strategy = self._strategy(broker, data, kwargs)

        strategy.init()
        data._update()  # Strategy.init might have changed/added to data.df

        # Indicators used in Strategy.next()
        indicator_attrs = _strategy_indicators(strategy)

        # Skip first few candles where indicators are still "warming up"
        # +1 to have at least two entries available
        start = 1 + _indicator_warmup_nbars(strategy)

        # Disable "invalid value encountered in ..." warnings. Comparison
        # np.nan >= 3 is not invalid; it's False.
        with np.errstate(invalid='ignore'):

            for i in _tqdm(range(start, len(self._data)), desc=self.run.__qualname__,
                           unit='bar', mininterval=2, miniters=100):
                # Prepare data and indicators for `next` call
                data._set_length(i + 1)
                for attr, indicator in indicator_attrs:
                    # Slice indicator on the last dimension (case of 2d indicator)
                    setattr(strategy, attr, indicator[..., :i + 1])

                # Handle orders processing and broker stuff
                try:
                    broker.next()
                except _OutOfMoneyError:
                    break

                # Next tick, a moment before bar close
                strategy.next()
            else:
                if self._finalize_trades is True:
                    # Close any remaining open trades so they produce some stats
                    for trade in reversed(broker.trades):
                        trade.close()

                    # HACK: Re-run broker one last time to handle close orders placed in the last
                    #  strategy iteration. Use the same OHLC values as in the last broker iteration.
                    if start < len(self._data):
                        try_(broker.next, exception=_OutOfMoneyError)
                elif len(broker.trades):
                    warnings.warn(
                        'Some trades remain open at the end of backtest. Use '
                        '`Backtest(..., finalize_trades=True)` to close them and '
                        'include them in stats.', stacklevel=2)

            # Set data back to full length
            # for future `indicator._opts['data'].index` calls to work
            data._set_length(len(self._data))

            equity = pd.Series(broker._equity).bfill().fillna(broker._cash).values
            self._results = compute_stats(
                trades=broker.closed_trades,
                equity=equity,
                ohlc_data=self._data,
                risk_free_rate=0.0,
                strategy_instance=strategy,
            )

        return self._results

    def optimize(self, *,
                 maximize: Union[str, Callable[[pd.Series], float]] = 'SQN',
                 method: str = 'grid',
                 max_tries: Optional[Union[int, float]] = None,
                 constraint: Optional[Callable[[dict], bool]] = None,
                 return_heatmap: bool = False,
                 return_optimization: bool = False,
                 random_state: Optional[int] = None,
                 **kwargs) -> Union[pd.Series,
                                    Tuple[pd.Series, pd.Series],
                                    Tuple[pd.Series, pd.Series, dict]]:
        """
        Optimize strategy parameters to an optimal combination.
        Returns result `pd.Series` of the best run.

        `maximize` is a string key from the
        `backtesting.backtesting.Backtest.run`-returned results series,
        or a function that accepts this series object and returns a number;
        the higher the better. By default, the method maximizes
        Van Tharp's [System Quality Number](https://google.com/search?q=System+Quality+Number).

        `method` is the optimization method. Currently two methods are supported:

        * `"grid"` which does an exhaustive (or randomized) search over the
          cartesian product of parameter combinations, and
        * `"sambo"` which finds close-to-optimal strategy parameters using
          [model-based optimization], making at most `max_tries` evaluations.

        [model-based optimization]: https://sambo-optimization.github.io

        `max_tries` is the maximal number of strategy runs to perform.
        If `method="grid"`, this results in randomized grid search.
        If `max_tries` is a floating value between (0, 1], this sets the
        number of runs to approximately that fraction of full grid space.
        Alternatively, if integer, it denotes the absolute maximum number
        of evaluations. If unspecified (default), grid search is exhaustive,
        whereas for `method="sambo"`, `max_tries` is set to 200.

        `constraint` is a function that accepts a dict-like object of
        parameters (with values) and returns `True` when the combination
        is admissible to test with. By default, any parameters combination
        is considered admissible.

        If `return_heatmap` is `True`, besides returning the result
        series, an additional `pd.Series` is returned with a multiindex
        of all admissible parameter combinations, which can be further
        inspected or projected onto 2D to plot a heatmap
        (see `backtesting.lib.plot_heatmaps()`).

        If `return_optimization` is True and `method = 'sambo'`,
        in addition to result series (and maybe heatmap), return raw
        [`scipy.optimize.OptimizeResult`][OptimizeResult] for further
        inspection, e.g. with [SAMBO]'s [plotting tools].

        [OptimizeResult]: https://sambo-optimization.github.io/doc/sambo/#sambo.OptimizeResult
        [SAMBO]: https://sambo-optimization.github.io
        [plotting tools]: https://sambo-optimization.github.io/doc/sambo/plot.html

        If you want reproducible optimization results, set `random_state`
        to a fixed integer random seed.

        Additional keyword arguments represent strategy arguments with
        list-like collections of possible values. For example, the following
        code finds and returns the "best" of the 7 admissible (of the
        9 possible) parameter combinations:

            best_stats = backtest.optimize(sma1=[5, 10, 15], sma2=[10, 20, 40],
                                           constraint=lambda p: p.sma1 < p.sma2)
        """
        if not kwargs:
            raise ValueError('Need some strategy parameters to optimize')

        maximize_key = None
        if isinstance(maximize, str):
            maximize_key = str(maximize)
            if maximize not in dummy_stats().index:
                raise ValueError('`maximize`, if str, must match a key in pd.Series '
                                 'result of backtest.run()')

            def maximize(stats: pd.Series, _key=maximize):
                return stats[_key]

        elif not callable(maximize):
            raise TypeError('`maximize` must be str (a field of backtest.run() result '
                            'Series) or a function that accepts result Series '
                            'and returns a number; the higher the better')
        assert callable(maximize), maximize

        have_constraint = bool(constraint)
        if constraint is None:

            def constraint(_):
                return True

        elif not callable(constraint):
            raise TypeError("`constraint` must be a function that accepts a dict "
                            "of strategy parameters and returns a bool whether "
                            "the combination of parameters is admissible or not")
        assert callable(constraint), constraint

        if method == 'skopt':
            method = 'sambo'
            warnings.warn('`Backtest.optimize(method="skopt")` is deprecated. Use `method="sambo"`.',
                          DeprecationWarning, stacklevel=2)
        if return_optimization and method != 'sambo':
            raise ValueError("return_optimization=True only valid if method='sambo'")

        def _tuple(x):
            return x if isinstance(x, Sequence) and not isinstance(x, str) else (x,)

        for k, v in kwargs.items():
            if len(_tuple(v)) == 0:
                raise ValueError(f"Optimization variable '{k}' is passed no "
                                 f"optimization values: {k}={v}")

        class AttrDict(dict):
            def __getattr__(self, item):
                return self[item]

        def _grid_size():
            size = int(np.prod([len(_tuple(v)) for v in kwargs.values()]))
            if size < 10_000 and have_constraint:
                size = sum(1 for p in product(*(zip(repeat(k), _tuple(v))
                                                for k, v in kwargs.items()))
                           if constraint(AttrDict(p)))
            return size

        def _optimize_grid() -> Union[pd.Series, Tuple[pd.Series, pd.Series]]:
            rand = default_rng(random_state).random
            grid_frac = (1 if max_tries is None else
                         max_tries if 0 < max_tries <= 1 else
                         max_tries / _grid_size())
            param_combos = [dict(params)  # back to dict so it pickles
                            for params in (AttrDict(params)
                                           for params in product(*(zip(repeat(k), _tuple(v))
                                                                   for k, v in kwargs.items())))
                            if constraint(params)
                            and rand() <= grid_frac]
            if not param_combos:
                raise ValueError('No admissible parameter combinations to test')

            if len(param_combos) > 300:
                warnings.warn(f'Searching for best of {len(param_combos)} configurations.',
                              stacklevel=2)

            heatmap = pd.Series(np.nan,
                                name=maximize_key,
                                index=pd.MultiIndex.from_tuples(
                                    [p.values() for p in param_combos],
                                    names=next(iter(param_combos)).keys()))

            from . import Pool
            with Pool() as pool, \
                    SharedMemoryManager() as smm:
                with patch(self, '_data', None):
                    bt = copy(self)  # bt._data will be reassigned in _mp_task worker
                results = _tqdm(
                    pool.imap(Backtest._mp_task,
                              ((bt, smm.df2shm(self._data), params_batch)
                               for params_batch in _batch(param_combos))),
                    total=len(param_combos),
                    desc='Backtest.optimize'
                )
                for param_batch, result in zip(_batch(param_combos), results):
                    for params, stats in zip(param_batch, result):
                        if stats is not None:
                            heatmap[tuple(params.values())] = maximize(stats)

            if pd.isnull(heatmap).all():
                # No trade was made in any of the runs. Just make a random
                # run so we get some, if empty, results
                stats = self.run(**param_combos[0])
            else:
                best_params = heatmap.idxmax(skipna=True)
                stats = self.run(**dict(zip(heatmap.index.names, best_params)))

            if return_heatmap:
                return stats, heatmap
            return stats

        def _optimize_sambo() -> Union[pd.Series,
                                       Tuple[pd.Series, pd.Series],
                                       Tuple[pd.Series, pd.Series, dict]]:
            try:
                import sambo
            except ImportError:
                raise ImportError("Need package 'sambo' for method='sambo'. pip install sambo") from None

            nonlocal max_tries
            max_tries = (200 if max_tries is None else
                         max(1, int(max_tries * _grid_size())) if 0 < max_tries <= 1 else
                         max_tries)

            dimensions = []
            for key, values in kwargs.items():
                values = np.asarray(values)
                if values.dtype.kind in 'mM':  # timedelta, datetime64
                    # these dtypes are unsupported in SAMBO, so convert to raw int
                    # TODO: save dtype and convert back later
                    values = values.astype(np.int64)

                if values.dtype.kind in 'iumM':
                    dimensions.append((values.min(), values.max() + 1))
                elif values.dtype.kind == 'f':
                    dimensions.append((values.min(), values.max()))
                else:
                    dimensions.append(values.tolist())

            # Avoid recomputing re-evaluations
            @lru_cache()
            def memoized_run(tup):
                nonlocal maximize, self
                stats = self.run(**dict(tup))
                return -maximize(stats)

            progress = iter(_tqdm(repeat(None), total=max_tries, leave=False,
                                  desc=self.optimize.__qualname__, mininterval=2))
            _names = tuple(kwargs.keys())

            def objective_function(x):
                nonlocal progress, memoized_run, constraint, _names
                next(progress)
                value = memoized_run(tuple(zip(_names, x)))
                return 0 if np.isnan(value) else value

            def cons(x):
                nonlocal constraint, _names
                return constraint(AttrDict(zip(_names, x)))

            res = sambo.minimize(
                fun=objective_function,
                bounds=dimensions,
                constraints=cons,
                max_iter=max_tries,
                method='sceua',
                rng=random_state)

            stats = self.run(**dict(zip(kwargs.keys(), res.x)))
            output = [stats]

            if return_heatmap:
                heatmap = pd.Series(dict(zip(map(tuple, res.xv), -res.funv)),
                                    name=maximize_key)
                heatmap.index.names = kwargs.keys()
                heatmap.sort_index(inplace=True)
                output.append(heatmap)

            if return_optimization:
                output.append(res)

            return stats if len(output) == 1 else tuple(output)

        if method == 'grid':
            output = _optimize_grid()
        elif method in ('sambo', 'skopt'):
            output = _optimize_sambo()
        else:
            raise ValueError(f"Method should be 'grid' or 'sambo', not {method!r}")
        return output

    @staticmethod
    def _mp_task(arg):
        bt, data_shm, params_batch = arg
        bt._data, shm = SharedMemoryManager.shm2df(data_shm)
        try:
            return [stats.filter(regex='^[^_]') if stats['# Trades'] else None
                    for stats in (bt.run(**params)
                                  for params in params_batch)]
        finally:
            for shmem in shm:
                shmem.close()

    def plot(self, *, results: pd.Series = None, filename=None, plot_width=None,
             plot_equity=True, plot_return=False, plot_pl=True,
             plot_volume=True, plot_drawdown=False, plot_trades=True,
             smooth_equity=False, relative_equity=True,
             superimpose: Union[bool, str] = True,
             resample=True, reverse_indicators=False,
             show_legend=True, open_browser=True):
        """
        Plot the progression of the last backtest run.

        If `results` is provided, it should be a particular result
        `pd.Series` such as returned by
        `backtesting.backtesting.Backtest.run` or
        `backtesting.backtesting.Backtest.optimize`, otherwise the last
        run's results are used.

        `filename` is the path to save the interactive HTML plot to.
        By default, a strategy/parameter-dependent file is created in the
        current working directory.

        `plot_width` is the width of the plot in pixels. If None (default),
        the plot is made to span 100% of browser width. The height is
        currently non-adjustable.

        If `plot_equity` is `True`, the resulting plot will contain
        an equity (initial cash plus assets) graph section. This is the same
        as `plot_return` plus initial 100%.

        If `plot_return` is `True`, the resulting plot will contain
        a cumulative return graph section. This is the same
        as `plot_equity` minus initial 100%.

        If `plot_pl` is `True`, the resulting plot will contain
        a profit/loss (P/L) indicator section.

        If `plot_volume` is `True`, the resulting plot will contain
        a trade volume section.

        If `plot_drawdown` is `True`, the resulting plot will contain
        a separate drawdown graph section.

        If `plot_trades` is `True`, the stretches between trade entries
        and trade exits are marked by hash-marked tractor beams.

        If `smooth_equity` is `True`, the equity graph will be
        interpolated between fixed points at trade closing times,
        unaffected by any interim asset volatility.

        If `relative_equity` is `True`, scale and label equity graph axis
        with return percent, not absolute cash-equivalent values.

        If `superimpose` is `True`, superimpose larger-timeframe candlesticks
        over the original candlestick chart. Default downsampling rule is:
        monthly for daily data, daily for hourly data, hourly for minute data,
        and minute for (sub-)second data.
        `superimpose` can also be a valid [Pandas offset string],
        such as `'5T'` or `'5min'`, in which case this frequency will be
        used to superimpose.
        Note, this only works for data with a datetime index.

        If `resample` is `True`, the OHLC data is resampled in a way that
        makes the upper number of candles for Bokeh to plot limited to 10_000.
        This may, in situations of overabundant data,
        improve plot's interactive performance and avoid browser's
        `Javascript Error: Maximum call stack size exceeded` or similar.
        Equity & dropdown curves and individual trades data is,
        likewise, [reasonably _aggregated_][TRADES_AGG].
        `resample` can also be a [Pandas offset string],
        such as `'5T'` or `'5min'`, in which case this frequency will be
        used to resample, overriding above numeric limitation.
        Note, all this only works for data with a datetime index.

        If `reverse_indicators` is `True`, the indicators below the OHLC chart
        are plotted in reverse order of declaration.

        [Pandas offset string]: \
            https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects

        [TRADES_AGG]: lib.html#backtesting.lib.TRADES_AGG

        If `show_legend` is `True`, the resulting plot graphs will contain
        labeled legends.

        If `open_browser` is `True`, the resulting `filename` will be
        opened in the default web browser.
        """
        if results is None:
            if self._results is None:
                raise RuntimeError('First issue `backtest.run()` to obtain results.')
            results = self._results

        return plot(
            results=results,
            df=self._data,
            indicators=results._strategy._indicators,
            filename=filename,
            plot_width=plot_width,
            plot_equity=plot_equity,
            plot_return=plot_return,
            plot_pl=plot_pl,
            plot_volume=plot_volume,
            plot_drawdown=plot_drawdown,
            plot_trades=plot_trades,
            smooth_equity=smooth_equity,
            relative_equity=relative_equity,
            superimpose=superimpose,
            resample=resample,
            reverse_indicators=reverse_indicators,
            show_legend=show_legend,
            open_browser=open_browser)
