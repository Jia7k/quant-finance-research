import numpy as np

from options_pricing_research.black_scholes import (
    black_scholes_greeks,
    black_scholes_price,
    implied_volatility,
)


def test_black_scholes_prices_match_known_benchmark():
    call = black_scholes_price("call", 100.0, 100.0, 1.0, 0.05, 0.20)
    put = black_scholes_price("put", 100.0, 100.0, 1.0, 0.05, 0.20)

    assert round(call, 6) == 10.450584
    assert round(put, 6) == 5.573526


def test_put_call_parity_without_dividends():
    spot = 100.0
    strike = 95.0
    time_to_expiry = 0.75
    risk_free_rate = 0.04
    volatility = 0.25

    call = black_scholes_price("call", spot, strike, time_to_expiry, risk_free_rate, volatility)
    put = black_scholes_price("put", spot, strike, time_to_expiry, risk_free_rate, volatility)
    parity_gap = call - put - (spot - strike * np.exp(-risk_free_rate * time_to_expiry))

    assert abs(parity_gap) < 1e-10


def test_greeks_match_known_call_benchmark():
    greeks = black_scholes_greeks("call", 100.0, 100.0, 1.0, 0.05, 0.20)

    assert round(greeks["delta"], 6) == 0.636831
    assert round(greeks["gamma"], 6) == 0.018762
    assert round(greeks["vega"], 6) == 37.524035
    assert round(greeks["theta"], 6) == -6.414028
    assert round(greeks["rho"], 6) == 53.232482


def test_implied_volatility_recovers_model_input():
    price = black_scholes_price("call", 100.0, 105.0, 0.5, 0.03, 0.32)

    implied = implied_volatility("call", price, 100.0, 105.0, 0.5, 0.03)

    assert abs(implied - 0.32) < 1e-6


def test_price_function_vectorizes_over_strikes():
    strikes = np.array([90.0, 100.0, 110.0])

    prices = black_scholes_price("call", 100.0, strikes, 1.0, 0.05, 0.20)

    assert prices.shape == (3,)
    assert prices[0] > prices[1] > prices[2]
