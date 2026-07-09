"""Option pricing research utilities."""

from options_pricing_research.black_scholes import (
    black_scholes_greeks,
    black_scholes_price,
    implied_volatility,
)
from options_pricing_research.binomial import cox_ross_rubinstein_price
from options_pricing_research.heston import HestonParameters, heston_monte_carlo_price
from options_pricing_research.monte_carlo import barrier_monte_carlo_price
from options_pricing_research.hedging import simulate_delta_hedge
from options_pricing_research.portfolio_lab import (
    build_portfolio_report,
    rolling_average_correlation,
    rolling_portfolio_volatility,
    stress_test_portfolio,
)

__all__ = [
    "HestonParameters",
    "barrier_monte_carlo_price",
    "black_scholes_greeks",
    "black_scholes_price",
    "build_portfolio_report",
    "cox_ross_rubinstein_price",
    "heston_monte_carlo_price",
    "implied_volatility",
    "rolling_average_correlation",
    "rolling_portfolio_volatility",
    "simulate_delta_hedge",
    "stress_test_portfolio",
]
