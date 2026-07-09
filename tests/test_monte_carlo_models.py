from options_pricing_research.heston import (
    HestonParameters,
    feller_condition,
    heston_monte_carlo_price,
)
from options_pricing_research.monte_carlo import (
    barrier_discount_to_vanilla,
    barrier_monte_carlo_price,
    european_monte_carlo_price,
)


def test_european_monte_carlo_is_close_to_black_scholes_benchmark():
    result = european_monte_carlo_price(
        "call",
        spot=100.0,
        strike=100.0,
        time_to_expiry=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        paths=80_000,
        seed=7,
    )

    assert abs(result.price - 10.450584) < 0.12


def test_knock_out_barrier_option_is_cheaper_than_vanilla_option():
    comparison = barrier_discount_to_vanilla(
        "call",
        "down-and-out",
        spot=100.0,
        strike=100.0,
        barrier=85.0,
        time_to_expiry=1.0,
        risk_free_rate=0.03,
        volatility=0.25,
        paths=40_000,
        steps=126,
        seed=11,
    )

    assert comparison["barrier_price"] < comparison["vanilla_price"]
    assert comparison["discount_to_vanilla"] > 0


def test_barrier_option_is_zero_if_already_knocked_out():
    result = barrier_monte_carlo_price(
        "call",
        "down-and-out",
        spot=80.0,
        strike=100.0,
        barrier=85.0,
        time_to_expiry=1.0,
        risk_free_rate=0.03,
        volatility=0.25,
    )

    assert result.price == 0.0


def test_heston_model_returns_positive_option_price_and_variance():
    params = HestonParameters(
        initial_variance=0.04,
        long_run_variance=0.04,
        mean_reversion=2.0,
        vol_of_variance=0.35,
        correlation=-0.6,
    )

    result = heston_monte_carlo_price(
        "call",
        spot=100.0,
        strike=100.0,
        time_to_expiry=1.0,
        risk_free_rate=0.03,
        params=params,
        paths=20_000,
        steps=126,
        seed=19,
    )

    assert result.price > 0.0
    assert result.average_terminal_variance >= 0.0


def test_feller_condition_positive_when_mean_reversion_dominates_vol_of_variance():
    params = HestonParameters(
        initial_variance=0.04,
        long_run_variance=0.04,
        mean_reversion=3.0,
        vol_of_variance=0.30,
        correlation=-0.5,
    )

    assert feller_condition(params) > 0
