from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from options_pricing_research.black_scholes import (
    OptionKind,
    black_scholes_greeks,
    black_scholes_price,
)


@dataclass(frozen=True)
class DeltaHedgeSummary:
    option_premium: float
    final_hedge_pnl: float
    total_transaction_costs: float
    terminal_spot: float
    payoff: float


def simulate_gbm_path(
    spot: float,
    time_to_expiry: float,
    drift: float,
    volatility: float,
    dividend_yield: float = 0.0,
    steps: int = 126,
    seed: int | None = 42,
) -> pd.DataFrame:
    """Simulate one geometric Brownian motion path."""

    _validate_path_inputs(spot, time_to_expiry, volatility, steps)
    rng = np.random.default_rng(seed)
    dt = time_to_expiry / steps
    shocks = rng.standard_normal(steps)
    log_returns = (
        (drift - dividend_yield - 0.5 * volatility**2) * dt
        + volatility * np.sqrt(dt) * shocks
    )
    spots = np.empty(steps + 1)
    spots[0] = spot
    spots[1:] = spot * np.exp(np.cumsum(log_returns))
    times = np.linspace(0.0, time_to_expiry, steps + 1)
    return pd.DataFrame({"step": np.arange(steps + 1), "time": times, "spot": spots})


def simulate_delta_hedge(
    kind: OptionKind,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    pricing_volatility: float,
    realized_volatility: float | None = None,
    drift: float | None = None,
    dividend_yield: float = 0.0,
    steps: int = 126,
    transaction_cost_bps: float = 0.0,
    seed: int | None = 42,
) -> tuple[pd.DataFrame, DeltaHedgeSummary]:
    """Simulate a short option position hedged with Black-Scholes Delta."""

    _validate_path_inputs(spot, time_to_expiry, pricing_volatility, steps)
    if strike <= 0:
        raise ValueError("strike must be positive.")
    if realized_volatility is not None and realized_volatility <= 0:
        raise ValueError("realized_volatility must be positive.")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps cannot be negative.")

    realized_volatility = realized_volatility or pricing_volatility
    drift = risk_free_rate if drift is None else drift
    cost_rate = transaction_cost_bps / 10_000.0
    dt = time_to_expiry / steps

    path = simulate_gbm_path(
        spot=spot,
        time_to_expiry=time_to_expiry,
        drift=drift,
        volatility=realized_volatility,
        dividend_yield=dividend_yield,
        steps=steps,
        seed=seed,
    )

    option_premium = black_scholes_price(
        kind,
        spot,
        strike,
        time_to_expiry,
        risk_free_rate,
        pricing_volatility,
        dividend_yield,
    )
    initial_delta = black_scholes_greeks(
        kind,
        spot,
        strike,
        time_to_expiry,
        risk_free_rate,
        pricing_volatility,
        dividend_yield,
    )["delta"]

    shares = initial_delta
    initial_trade_cost = abs(shares * spot) * cost_rate
    cash = option_premium - shares * spot - initial_trade_cost
    cumulative_cost = initial_trade_cost
    records = [
        _hedge_record(
            step=0,
            time=0.0,
            spot=spot,
            time_remaining=time_to_expiry,
            option_value=option_premium,
            delta=initial_delta,
            shares=shares,
            cash=cash,
            cumulative_cost=cumulative_cost,
            payoff=0.0,
        )
    ]

    for step in range(1, steps):
        current_spot = float(path.loc[step, "spot"])
        current_time = float(path.loc[step, "time"])
        time_remaining = time_to_expiry - current_time

        cash *= np.exp(risk_free_rate * dt)
        option_value = black_scholes_price(
            kind,
            current_spot,
            strike,
            time_remaining,
            risk_free_rate,
            pricing_volatility,
            dividend_yield,
        )
        new_delta = black_scholes_greeks(
            kind,
            current_spot,
            strike,
            time_remaining,
            risk_free_rate,
            pricing_volatility,
            dividend_yield,
        )["delta"]

        trade_shares = new_delta - shares
        trade_cost = abs(trade_shares * current_spot) * cost_rate
        cash -= trade_shares * current_spot + trade_cost
        cumulative_cost += trade_cost
        shares = new_delta

        records.append(
            _hedge_record(
                step=step,
                time=current_time,
                spot=current_spot,
                time_remaining=time_remaining,
                option_value=float(option_value),
                delta=new_delta,
                shares=shares,
                cash=cash,
                cumulative_cost=cumulative_cost,
                payoff=0.0,
            )
        )

    terminal_spot = float(path.loc[steps, "spot"])
    cash *= np.exp(risk_free_rate * dt)
    payoff = _payoff(kind, terminal_spot, strike)
    final_portfolio_value = cash + shares * terminal_spot - payoff
    records.append(
        {
            "step": steps,
            "time": time_to_expiry,
            "spot": terminal_spot,
            "time_remaining": 0.0,
            "option_value": payoff,
            "delta": np.nan,
            "stock_position": shares,
            "stock_value": shares * terminal_spot,
            "cash": cash,
            "portfolio_value": final_portfolio_value,
            "cumulative_transaction_costs": cumulative_cost,
            "payoff": payoff,
        }
    )

    hedge_path = pd.DataFrame(records)
    summary = DeltaHedgeSummary(
        option_premium=float(option_premium),
        final_hedge_pnl=float(final_portfolio_value),
        total_transaction_costs=float(cumulative_cost),
        terminal_spot=terminal_spot,
        payoff=float(payoff),
    )
    return hedge_path, summary


def _hedge_record(
    step: int,
    time: float,
    spot: float,
    time_remaining: float,
    option_value: float,
    delta: float,
    shares: float,
    cash: float,
    cumulative_cost: float,
    payoff: float,
) -> dict[str, float]:
    stock_value = shares * spot
    portfolio_value = cash + stock_value - option_value
    return {
        "step": step,
        "time": time,
        "spot": spot,
        "time_remaining": time_remaining,
        "option_value": option_value,
        "delta": delta,
        "stock_position": shares,
        "stock_value": stock_value,
        "cash": cash,
        "portfolio_value": portfolio_value,
        "cumulative_transaction_costs": cumulative_cost,
        "payoff": payoff,
    }


def _payoff(kind: OptionKind, spot: float, strike: float) -> float:
    normalized = kind.lower().strip()
    if normalized == "call":
        return float(max(spot - strike, 0.0))
    if normalized == "put":
        return float(max(strike - spot, 0.0))
    raise ValueError("kind must be 'call' or 'put'.")


def _validate_path_inputs(
    spot: float,
    time_to_expiry: float,
    volatility: float,
    steps: int,
) -> None:
    if spot <= 0:
        raise ValueError("spot must be positive.")
    if time_to_expiry <= 0:
        raise ValueError("time_to_expiry must be positive.")
    if volatility <= 0:
        raise ValueError("volatility must be positive.")
    if steps < 2:
        raise ValueError("steps must be at least 2.")
