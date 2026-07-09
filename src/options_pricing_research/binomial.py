from __future__ import annotations

from typing import Literal

import numpy as np

from options_pricing_research.black_scholes import OptionKind

ExerciseStyle = Literal["european", "american"]


def cox_ross_rubinstein_price(
    kind: OptionKind,
    spot: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    steps: int = 250,
    dividend_yield: float = 0.0,
    exercise_style: ExerciseStyle = "european",
) -> float:
    """Price a vanilla option with the Cox-Ross-Rubinstein binomial tree."""

    _validate_inputs(spot, strike, time_to_expiry, volatility, steps)
    kind = _normalize_kind(kind)
    exercise_style = _normalize_exercise_style(exercise_style)

    dt = time_to_expiry / steps
    up = np.exp(volatility * np.sqrt(dt))
    down = 1.0 / up
    discount = np.exp(-risk_free_rate * dt)
    growth = np.exp((risk_free_rate - dividend_yield) * dt)
    probability = (growth - down) / (up - down)

    if probability < 0.0 or probability > 1.0:
        raise ValueError(
            "Risk-neutral probability is outside [0, 1]. Increase steps or check inputs."
        )

    node_indexes = np.arange(steps + 1)
    terminal_spots = spot * (up ** (steps - node_indexes)) * (down**node_indexes)
    option_values = _payoff(kind, terminal_spots, strike)

    for step in range(steps - 1, -1, -1):
        option_values = discount * (
            probability * option_values[:-1] + (1.0 - probability) * option_values[1:]
        )

        if exercise_style == "american":
            node_indexes = np.arange(step + 1)
            node_spots = spot * (up ** (step - node_indexes)) * (down**node_indexes)
            option_values = np.maximum(option_values, _payoff(kind, node_spots, strike))

    return float(option_values[0])


def terminal_stock_tree(
    spot: float,
    time_to_expiry: float,
    volatility: float,
    steps: int,
) -> list[list[float]]:
    """Build stock-price levels for visualizing a small CRR tree."""

    _validate_inputs(spot, 1.0, time_to_expiry, volatility, steps)
    dt = time_to_expiry / steps
    up = np.exp(volatility * np.sqrt(dt))
    down = 1.0 / up

    tree = []
    for step in range(steps + 1):
        row = [spot * (up ** (step - down_moves)) * (down**down_moves) for down_moves in range(step + 1)]
        tree.append(row)
    return tree


def _payoff(kind: OptionKind, spots: np.ndarray, strike: float) -> np.ndarray:
    if kind == "call":
        return np.maximum(spots - strike, 0.0)
    return np.maximum(strike - spots, 0.0)


def _validate_inputs(
    spot: float,
    strike: float,
    time_to_expiry: float,
    volatility: float,
    steps: int,
) -> None:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive.")
    if time_to_expiry <= 0:
        raise ValueError("time_to_expiry must be positive.")
    if volatility <= 0:
        raise ValueError("volatility must be positive.")
    if steps < 1:
        raise ValueError("steps must be at least 1.")


def _normalize_kind(kind: str) -> OptionKind:
    normalized = kind.lower().strip()
    if normalized not in {"call", "put"}:
        raise ValueError("kind must be 'call' or 'put'.")
    return normalized  # type: ignore[return-value]


def _normalize_exercise_style(style: str) -> ExerciseStyle:
    normalized = style.lower().strip()
    if normalized not in {"european", "american"}:
        raise ValueError("exercise_style must be 'european' or 'american'.")
    return normalized  # type: ignore[return-value]
