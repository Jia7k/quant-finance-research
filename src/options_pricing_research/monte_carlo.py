from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from options_pricing_research.black_scholes import OptionKind, black_scholes_price

BarrierKind = Literal["down-and-out", "up-and-out"]


@dataclass(frozen=True)
class MonteCarloResult:
    price: float
    standard_error: float
    paths: int


def european_monte_carlo_price(
    kind: OptionKind,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    paths: int = 100_000,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Price a European option by simulating terminal GBM prices."""

    _validate_common(spot, strike, time_to_expiry, volatility, paths)
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(paths)
    terminal_spot = spot * np.exp(
        (risk_free_rate - dividend_yield - 0.5 * volatility**2) * time_to_expiry
        + volatility * np.sqrt(time_to_expiry) * z
    )
    payoff = _vanilla_payoff(kind, terminal_spot, strike)
    return _discounted_result(payoff, risk_free_rate, time_to_expiry, paths)


def barrier_monte_carlo_price(
    kind: OptionKind,
    barrier_kind: BarrierKind,
    spot: float,
    strike: float,
    barrier: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    paths: int = 100_000,
    steps: int = 252,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Price a knock-out barrier option by simulating full GBM paths."""

    _validate_common(spot, strike, time_to_expiry, volatility, paths)
    if barrier <= 0:
        raise ValueError("barrier must be positive.")
    if steps < 1:
        raise ValueError("steps must be at least 1.")

    barrier_kind = _normalize_barrier_kind(barrier_kind)
    if barrier_kind == "down-and-out" and spot <= barrier:
        return MonteCarloResult(price=0.0, standard_error=0.0, paths=paths)
    if barrier_kind == "up-and-out" and spot >= barrier:
        return MonteCarloResult(price=0.0, standard_error=0.0, paths=paths)

    rng = np.random.default_rng(seed)
    dt = time_to_expiry / steps
    drift = (risk_free_rate - dividend_yield - 0.5 * volatility**2) * dt
    diffusion = volatility * np.sqrt(dt)
    shocks = rng.standard_normal((paths, steps))
    log_paths = np.log(spot) + np.cumsum(drift + diffusion * shocks, axis=1)
    price_paths = np.exp(log_paths)

    if barrier_kind == "down-and-out":
        alive = price_paths.min(axis=1) > barrier
    else:
        alive = price_paths.max(axis=1) < barrier

    terminal_spot = price_paths[:, -1]
    payoff = _vanilla_payoff(kind, terminal_spot, strike) * alive
    return _discounted_result(payoff, risk_free_rate, time_to_expiry, paths)


def barrier_discount_to_vanilla(
    kind: OptionKind,
    barrier_kind: BarrierKind,
    spot: float,
    strike: float,
    barrier: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
    paths: int = 100_000,
    steps: int = 252,
    seed: int | None = 42,
) -> dict[str, float]:
    """Compare a knock-out option price to the vanilla Black-Scholes price."""

    barrier_result = barrier_monte_carlo_price(
        kind,
        barrier_kind,
        spot,
        strike,
        barrier,
        time_to_expiry,
        risk_free_rate,
        volatility,
        dividend_yield,
        paths,
        steps,
        seed,
    )
    vanilla = black_scholes_price(
        kind,
        spot,
        strike,
        time_to_expiry,
        risk_free_rate,
        volatility,
        dividend_yield,
    )
    return {
        "vanilla_price": float(vanilla),
        "barrier_price": barrier_result.price,
        "barrier_standard_error": barrier_result.standard_error,
        "discount_to_vanilla": float(vanilla) - barrier_result.price,
    }


def _discounted_result(
    payoff: np.ndarray,
    risk_free_rate: float,
    time_to_expiry: float,
    paths: int,
) -> MonteCarloResult:
    discounted = np.exp(-risk_free_rate * time_to_expiry) * payoff
    return MonteCarloResult(
        price=float(discounted.mean()),
        standard_error=float(discounted.std(ddof=1) / np.sqrt(paths)),
        paths=paths,
    )


def _vanilla_payoff(kind: OptionKind, spots: np.ndarray, strike: float) -> np.ndarray:
    normalized = kind.lower().strip()
    if normalized == "call":
        return np.maximum(spots - strike, 0.0)
    if normalized == "put":
        return np.maximum(strike - spots, 0.0)
    raise ValueError("kind must be 'call' or 'put'.")


def _validate_common(
    spot: float,
    strike: float,
    time_to_expiry: float,
    volatility: float,
    paths: int,
) -> None:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive.")
    if time_to_expiry <= 0:
        raise ValueError("time_to_expiry must be positive.")
    if volatility <= 0:
        raise ValueError("volatility must be positive.")
    if paths < 2:
        raise ValueError("paths must be at least 2.")


def _normalize_barrier_kind(kind: str) -> BarrierKind:
    normalized = kind.lower().strip()
    if normalized not in {"down-and-out", "up-and-out"}:
        raise ValueError("barrier_kind must be 'down-and-out' or 'up-and-out'.")
    return normalized  # type: ignore[return-value]
