import numpy as np

from options_pricing_research.strategies import (
    OptionLeg,
    aggregate_strategy_greeks,
    payoff_table,
    strategy_presets,
    summarize_strategy,
)


def test_bull_call_spread_has_expected_debit_profit_and_loss():
    legs = [
        OptionLeg(kind="call", side="long", strike=100.0, premium=6.0),
        OptionLeg(kind="call", side="short", strike=110.0, premium=2.0),
    ]

    summary = summarize_strategy(legs, spot=100.0, price_range=np.array([90.0, 100.0, 110.0, 120.0]))

    assert summary.entry_cost == 4.0
    assert summary.max_loss == -4.0
    assert summary.max_profit == 6.0
    assert summary.risk_label == "Defined risk"
    assert summary.profit_label == "Defined profit"
    assert summary.breakevens == [104.0]


def test_long_straddle_reports_two_breakevens():
    legs = [
        OptionLeg(kind="call", side="long", strike=100.0, premium=5.0),
        OptionLeg(kind="put", side="long", strike=100.0, premium=4.0),
    ]

    summary = summarize_strategy(legs, spot=100.0, price_range=np.linspace(80.0, 120.0, 81))

    assert summary.entry_cost == 9.0
    assert summary.risk_label == "Defined risk"
    assert summary.profit_label == "Unbounded profit"
    assert summary.breakevens == [91.0, 109.0]


def test_short_call_reports_unbounded_risk():
    legs = [OptionLeg(kind="call", side="short", strike=100.0, premium=3.0)]

    summary = summarize_strategy(legs, spot=100.0, price_range=np.array([90.0, 100.0, 120.0]))

    assert summary.entry_cost == -3.0
    assert summary.risk_label == "Unbounded risk"
    assert summary.profit_label == "Defined profit"


def test_payoff_table_returns_leg_columns_and_total():
    legs = strategy_presets(100.0, 0.20)["Bull Call Spread"]

    table = payoff_table(legs, np.array([90.0, 100.0, 110.0]))

    assert list(table.columns) == ["underlying_price", "leg_1", "leg_2", "total_payoff"]
    assert table["total_payoff"].iloc[-1] > table["total_payoff"].iloc[0]


def test_aggregate_strategy_greeks_scales_by_side_and_quantity():
    legs = [
        OptionLeg(kind="call", side="long", strike=100.0, premium=5.0, quantity=2.0),
        OptionLeg(kind="put", side="short", strike=95.0, premium=3.0, quantity=1.0),
    ]

    greeks = aggregate_strategy_greeks(
        legs,
        spot=100.0,
        time_to_expiry=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
    )

    assert {"delta", "gamma", "vega", "theta", "rho"}.issubset(greeks.index)
    assert greeks["gamma"] > 0.0
    assert greeks["delta"] > 0.0
