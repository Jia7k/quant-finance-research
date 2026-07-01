import pandas as pd
from pandas.testing import assert_frame_equal

from quant_factor_research.data import PriceData
from quant_factor_research.factors import build_composite_signal, compute_factors


def test_momentum_factor_is_shifted_to_avoid_same_day_lookahead():
    dates = pd.bdate_range("2024-01-01", periods=90)
    close = pd.DataFrame(
        {
            "AAA": range(100, 190),
            "BBB": range(200, 290),
            "CCC": range(300, 390),
            "DDD": range(400, 490),
        },
        index=dates,
        dtype=float,
    )
    data = PriceData(
        open=close.copy(),
        high=close * 1.01,
        low=close * 0.99,
        close=close,
        volume=close * 10_000,
    )

    factors = compute_factors(data)

    expected = close.pct_change(21).shift(1)
    assert_frame_equal(factors["momentum_21"], expected)


def test_composite_signal_requires_minimum_factor_coverage():
    index = pd.bdate_range("2024-01-01", periods=2)
    factor_a = pd.DataFrame({"AAA": [1.0, 2.0], "BBB": [2.0, 1.0], "CCC": [3.0, None]}, index=index)
    factor_b = pd.DataFrame({"AAA": [3.0, 2.0], "BBB": [2.0, 1.0], "CCC": [1.0, None]}, index=index)

    signal = build_composite_signal(
        {"a": factor_a, "b": factor_b},
        min_factors=2,
    )

    assert signal.loc[index[0]].notna().all()
    assert pd.isna(signal.loc[index[1], "CCC"])
