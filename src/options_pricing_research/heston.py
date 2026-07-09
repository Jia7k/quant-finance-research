from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from options_pricing_research.black_scholes import OptionKind


@dataclass(frozen=True)
class HestonParameters:
    initial_variance: float
    long_run_variance: float
    mean_reversion: float
    vol_of_variance: float
    correlation: float


@dataclass(frozen=True)
class HestonMonteCarloResult:
    price: float
    standard_error: float
    paths: int
    average_terminal_variance: float


def simulate_heston_paths(
    spot: float,
    time_to_expiry: float,
    risk_free_rate: float,
    dividend_yield: float,
    params: HestonParameters,
    paths: int = 50_000,
    steps: int = 252,
    seed: int | None = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate Heston spot and variance paths with full truncation Euler."""

    _validate_heston_inputs(spot, time_to_expiry, params, paths, steps)
    rng = np.random.default_rng(seed)
    dt = time_to_expiry / steps

    spots = np.empty((paths, steps + 1), dtype=float)
    variances = np.empty((paths, steps + 1), dtype=float)
    spots[:, 0] = spot
    variances[:, 0] = params.initial_variance

    for step in range(1, steps + 1):
        z_variance = rng.standard_normal(paths)
        z_independent = rng.standard_normal(paths)
        z_spot = (
            params.correlation * z_variance
            + np.sqrt(1.0 - params.correlation**2) * z_independent
        )

        previous_variance = np.maximum(variances[:, step - 1], 0.0)
        variances[:, step] = variances[:, step - 1] + (
            params.mean_reversion * (params.long_run_variance - previous_variance) * dt
            + params.vol_of_variance * np.sqrt(previous_variance * dt) * z_variance
        )
        variance_for_spot = np.maximum(variances[:, step], 0.0)

        spots[:, step] = spots[:, step - 1] * np.exp(
            (risk_free_rate - dividend_yield - 0.5 * variance_for_spot) * dt
            + np.sqrt(variance_for_spot * dt) * z_spot
        )

    return spots, np.maximum(variances, 0.0)


def heston_monte_carlo_price(
    kind: OptionKind,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    params: HestonParameters,
    dividend_yield: float = 0.0,
    paths: int = 50_000,
    steps: int = 252,
    seed: int | None = 42,
) -> HestonMonteCarloResult:
    """Price a European option under the Heston model by Monte Carlo."""

    if strike <= 0:
        raise ValueError("strike must be positive.")
    spots, variances = simulate_heston_paths(
        spot,
        time_to_expiry,
        risk_free_rate,
        dividend_yield,
        params,
        paths,
        steps,
        seed,
    )
    terminal_spot = spots[:, -1]
    kind = _normalize_kind(kind)
    if kind == "call":
        payoff = np.maximum(terminal_spot - strike, 0.0)
    else:
        payoff = np.maximum(strike - terminal_spot, 0.0)

    discounted = np.exp(-risk_free_rate * time_to_expiry) * payoff
    return HestonMonteCarloResult(
        price=float(discounted.mean()),
        standard_error=float(discounted.std(ddof=1) / np.sqrt(paths)),
        paths=paths,
        average_terminal_variance=float(variances[:, -1].mean()),
    )


def feller_condition(params: HestonParameters) -> float:
    """Return 2*kappa*theta - xi^2; positive values satisfy the Feller condition."""

    return 2.0 * params.mean_reversion * params.long_run_variance - params.vol_of_variance**2


def _validate_heston_inputs(
    spot: float,
    time_to_expiry: float,
    params: HestonParameters,
    paths: int,
    steps: int,
) -> None:
    if spot <= 0:
        raise ValueError("spot must be positive.")
    if time_to_expiry <= 0:
        raise ValueError("time_to_expiry must be positive.")
    if params.initial_variance < 0 or params.long_run_variance < 0:
        raise ValueError("variance parameters cannot be negative.")
    if params.mean_reversion <= 0:
        raise ValueError("mean_reversion must be positive.")
    if params.vol_of_variance < 0:
        raise ValueError("vol_of_variance cannot be negative.")
    if not -1.0 <= params.correlation <= 1.0:
        raise ValueError("correlation must be between -1 and 1.")
    if paths < 2:
        raise ValueError("paths must be at least 2.")
    if steps < 1:
        raise ValueError("steps must be at least 1.")


def _normalize_kind(kind: str) -> OptionKind:
    normalized = kind.lower().strip()
    if normalized not in {"call", "put"}:
        raise ValueError("kind must be 'call' or 'put'.")
    return normalized  # type: ignore[return-value]
