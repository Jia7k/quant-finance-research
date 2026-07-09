from __future__ import annotations

import numpy as np
import pandas as pd

from options_pricing_research.binomial import cox_ross_rubinstein_price
from options_pricing_research.black_scholes import (
    OptionKind,
    black_scholes_greeks,
    black_scholes_price,
    implied_volatility,
)
from options_pricing_research.heston import HestonParameters, heston_monte_carlo_price
from options_pricing_research.monte_carlo import barrier_monte_carlo_price


def black_scholes_surface(
    kind: OptionKind,
    spot: float,
    strikes: np.ndarray,
    volatilities: np.ndarray,
    time_to_expiry: float,
    risk_free_rate: float,
    dividend_yield: float = 0.0,
) -> pd.DataFrame:
    """Build a price grid with volatility rows and strike columns."""

    values = [
        black_scholes_price(
            kind,
            spot,
            strikes,
            time_to_expiry,
            risk_free_rate,
            volatility,
            dividend_yield,
        )
        for volatility in volatilities
    ]
    surface = pd.DataFrame(values, index=volatilities, columns=strikes)
    surface.index.name = "volatility"
    surface.columns.name = "strike"
    return surface


def synthetic_smile(
    spot: float,
    strikes: np.ndarray,
    base_volatility: float,
    skew: float = 0.08,
    curvature: float = 0.55,
) -> pd.DataFrame:
    """Create a stable synthetic implied-volatility smile for demonstration."""

    moneyness = strikes / spot
    log_moneyness = np.log(moneyness)
    implied_vol = base_volatility + curvature * (log_moneyness**2)
    implied_vol += skew * np.maximum(1.0 - moneyness, 0.0)
    implied_vol = np.maximum(implied_vol, 0.01)
    return pd.DataFrame(
        {
            "strike": strikes,
            "moneyness": moneyness,
            "implied_volatility": implied_vol,
        }
    )


def recover_smile_prices(
    kind: OptionKind,
    spot: float,
    smile: pd.DataFrame,
    time_to_expiry: float,
    risk_free_rate: float,
    dividend_yield: float = 0.0,
) -> pd.DataFrame:
    """Generate option prices from a smile and recover IV through inversion."""

    rows = []
    for row in smile.itertuples(index=False):
        market_price = black_scholes_price(
            kind,
            spot,
            float(row.strike),
            time_to_expiry,
            risk_free_rate,
            float(row.implied_volatility),
            dividend_yield,
        )
        recovered = implied_volatility(
            kind,
            market_price,
            spot,
            float(row.strike),
            time_to_expiry,
            risk_free_rate,
            dividend_yield,
        )
        rows.append(
            {
                "strike": float(row.strike),
                "moneyness": float(row.moneyness),
                "market_price": float(market_price),
                "implied_volatility": float(row.implied_volatility),
                "recovered_implied_volatility": recovered,
            }
        )
    return pd.DataFrame(rows)


def model_snapshot(
    kind: OptionKind,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    binomial_steps: int = 300,
    heston_paths: int = 15_000,
    heston_steps: int = 96,
    seed: int = 42,
) -> pd.DataFrame:
    """Compare prices from Black-Scholes, CRR binomial, and Heston MC."""

    heston_params = HestonParameters(
        initial_variance=volatility**2,
        long_run_variance=volatility**2,
        mean_reversion=2.0,
        vol_of_variance=max(0.15, volatility * 1.5),
        correlation=-0.55,
    )
    heston = heston_monte_carlo_price(
        kind,
        spot,
        strike,
        time_to_expiry,
        risk_free_rate,
        heston_params,
        dividend_yield=dividend_yield,
        paths=heston_paths,
        steps=heston_steps,
        seed=seed,
    )
    prices = [
        {
            "model": "Black-Scholes",
            "price": black_scholes_price(
                kind,
                spot,
                strike,
                time_to_expiry,
                risk_free_rate,
                volatility,
                dividend_yield,
            ),
            "standard_error": np.nan,
        },
        {
            "model": "CRR binomial",
            "price": cox_ross_rubinstein_price(
                kind,
                spot,
                strike,
                time_to_expiry,
                risk_free_rate,
                volatility,
                steps=binomial_steps,
                dividend_yield=dividend_yield,
            ),
            "standard_error": np.nan,
        },
        {
            "model": "Heston MC",
            "price": heston.price,
            "standard_error": heston.standard_error,
        },
    ]
    return pd.DataFrame(prices)


def option_metrics(
    kind: OptionKind,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> tuple[float, pd.Series]:
    """Return Black-Scholes price and Greeks as display-friendly values."""

    price = black_scholes_price(
        kind,
        spot,
        strike,
        time_to_expiry,
        risk_free_rate,
        volatility,
        dividend_yield,
    )
    greeks = pd.Series(
        black_scholes_greeks(
            kind,
            spot,
            strike,
            time_to_expiry,
            risk_free_rate,
            volatility,
            dividend_yield,
        )
    )
    greeks.loc["vega_per_1pct"] = greeks.loc["vega"] / 100.0
    greeks.loc["theta_per_day"] = greeks.loc["theta"] / 365.0
    return float(price), greeks


def barrier_snapshot(
    kind: OptionKind,
    barrier_kind: str,
    spot: float,
    strike: float,
    barrier: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    paths: int = 25_000,
    steps: int = 126,
    seed: int = 42,
) -> pd.Series:
    """Compare a knock-out barrier option with the vanilla price."""

    vanilla = black_scholes_price(
        kind,
        spot,
        strike,
        time_to_expiry,
        risk_free_rate,
        volatility,
        dividend_yield,
    )
    barrier = barrier_monte_carlo_price(
        kind,
        barrier_kind,  # type: ignore[arg-type]
        spot,
        strike,
        barrier,
        time_to_expiry,
        risk_free_rate,
        volatility,
        dividend_yield,
        paths=paths,
        steps=steps,
        seed=seed,
    )
    return pd.Series(
        {
            "vanilla_price": float(vanilla),
            "barrier_price": barrier.price,
            "standard_error": barrier.standard_error,
            "knock_out_discount": float(vanilla) - barrier.price,
        }
    )
