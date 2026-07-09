from options_pricing_research.hedging import simulate_delta_hedge, simulate_gbm_path


def test_gbm_path_has_requested_length_and_positive_spots():
    path = simulate_gbm_path(
        spot=100.0,
        time_to_expiry=1.0,
        drift=0.05,
        volatility=0.20,
        steps=20,
        seed=1,
    )

    assert len(path) == 21
    assert (path["spot"] > 0).all()
    assert path["time"].iloc[0] == 0.0
    assert path["time"].iloc[-1] == 1.0


def test_delta_hedge_path_has_consistent_summary_values():
    hedge_path, summary = simulate_delta_hedge(
        "call",
        spot=100.0,
        strike=100.0,
        time_to_expiry=1.0,
        risk_free_rate=0.05,
        pricing_volatility=0.20,
        realized_volatility=0.20,
        steps=52,
        transaction_cost_bps=0.0,
        seed=7,
    )

    assert len(hedge_path) == 53
    assert summary.option_premium > 0.0
    assert summary.final_hedge_pnl == hedge_path["portfolio_value"].iloc[-1]
    assert summary.terminal_spot == hedge_path["spot"].iloc[-1]
    assert summary.total_transaction_costs == 0.0


def test_delta_hedge_transaction_costs_accumulate():
    hedge_path, summary = simulate_delta_hedge(
        "put",
        spot=100.0,
        strike=100.0,
        time_to_expiry=0.5,
        risk_free_rate=0.03,
        pricing_volatility=0.25,
        realized_volatility=0.30,
        steps=40,
        transaction_cost_bps=5.0,
        seed=11,
    )

    assert summary.total_transaction_costs > 0.0
    assert hedge_path["cumulative_transaction_costs"].is_monotonic_increasing


def test_delta_hedge_starts_near_zero_without_transaction_costs():
    hedge_path, _ = simulate_delta_hedge(
        "call",
        spot=100.0,
        strike=105.0,
        time_to_expiry=1.0,
        risk_free_rate=0.04,
        pricing_volatility=0.22,
        realized_volatility=0.22,
        steps=24,
        transaction_cost_bps=0.0,
        seed=3,
    )

    assert abs(hedge_path["portfolio_value"].iloc[0]) < 1e-10
