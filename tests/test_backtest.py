import pandas as pd

from quant_factor_research.backtest import run_backtest
from quant_factor_research.portfolio import make_long_short_weights


def test_long_short_weights_are_market_neutral_and_gross_one():
    signal = pd.DataFrame(
        {"AAA": [1.0], "BBB": [2.0], "CCC": [3.0], "DDD": [4.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )

    weights = make_long_short_weights(signal, n_long=1, n_short=1)

    assert weights.sum(axis=1).iloc[0] == 0.0
    assert weights.abs().sum(axis=1).iloc[0] == 1.0
    assert weights.loc[signal.index[0], "DDD"] == 0.5
    assert weights.loc[signal.index[0], "AAA"] == -0.5


def test_backtest_applies_turnover_transaction_costs():
    dates = pd.bdate_range("2024-01-01", periods=3)
    close = pd.DataFrame({"AAA": [100.0, 110.0, 121.0], "BBB": [100.0, 100.0, 100.0]}, index=dates)
    weights = pd.DataFrame({"AAA": [1.0, 1.0, 0.0], "BBB": [0.0, 0.0, 0.0]}, index=dates)

    result = run_backtest(close, weights, cost_bps=10.0)

    assert len(result.returns) == 2
    assert round(result.turnover.iloc[0], 6) == 1.0
    assert round(result.costs.iloc[0], 6) == 0.001
    assert round(result.returns.iloc[0], 6) == 0.099
    assert round(result.returns.iloc[1], 6) == 0.1
