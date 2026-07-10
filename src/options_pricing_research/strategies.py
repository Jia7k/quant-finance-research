from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from options_pricing_research.black_scholes import black_scholes_greeks

OptionSide = Literal["long", "short"]
OptionKindName = Literal["call", "put"]


@dataclass(frozen=True)
class OptionLeg:
    kind: OptionKindName
    side: OptionSide
    strike: float
    premium: float
    quantity: float = 1.0

    @property
    def signed_quantity(self) -> float:
        return self.quantity if self.side == "long" else -self.quantity


@dataclass(frozen=True)
class StrategySummary:
    entry_cost: float
    max_profit: float | None
    max_loss: float | None
    breakevens: list[float]
    risk_label: str
    profit_label: str


def payoff_table(legs: list[OptionLeg], prices: np.ndarray) -> pd.DataFrame:
    """Return per-leg and total expiration payoff over underlying prices."""

    price_grid = np.asarray(prices, dtype=float)
    frame = pd.DataFrame({"underlying_price": price_grid})
    total = np.zeros_like(price_grid, dtype=float)
    for index, leg in enumerate(legs, start=1):
        leg_payoff = _leg_payoff(leg, price_grid)
        frame[f"leg_{index}"] = leg_payoff
        total += leg_payoff
    frame["total_payoff"] = total
    return frame


def summarize_strategy(
    legs: list[OptionLeg],
    spot: float,
    price_range: np.ndarray | None = None,
) -> StrategySummary:
    """Summarize entry cost, breakevens, and finite-grid risk/reward."""

    if price_range is None:
        price_range = np.linspace(max(0.01, spot * 0.5), spot * 1.5, 121)
    table = payoff_table(legs, price_range)
    total_payoff = table["total_payoff"]
    risk_label = _risk_label(legs)
    profit_label = _profit_label(legs)

    max_profit = None if profit_label == "Unbounded profit" else float(total_payoff.max())
    max_loss = None if risk_label == "Unbounded risk" else float(total_payoff.min())
    return StrategySummary(
        entry_cost=_entry_cost(legs),
        max_profit=max_profit,
        max_loss=max_loss,
        breakevens=_breakevens(table["underlying_price"].to_numpy(), total_payoff.to_numpy()),
        risk_label=risk_label,
        profit_label=profit_label,
    )


def aggregate_strategy_greeks(
    legs: list[OptionLeg],
    spot: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float = 0.0,
) -> pd.Series:
    """Aggregate Black-Scholes Greeks across strategy legs."""

    totals = pd.Series({"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0})
    for leg in legs:
        leg_greeks = pd.Series(
            black_scholes_greeks(
                leg.kind,
                spot,
                leg.strike,
                time_to_expiry,
                risk_free_rate,
                volatility,
                dividend_yield,
            )
        )
        totals = totals.add(leg_greeks * leg.signed_quantity, fill_value=0.0)
    return totals


def strategy_presets(spot: float, volatility: float) -> dict[str, list[OptionLeg]]:
    """Build practical strategy presets around current spot."""

    atm = round(spot, 2)
    lower = round(spot * 0.95, 2)
    upper = round(spot * 1.05, 2)
    premium_scale = max(1.0, spot * volatility * 0.2)
    return {
        "Long Call": [OptionLeg("call", "long", atm, round(premium_scale, 2))],
        "Bull Call Spread": [
            OptionLeg("call", "long", atm, round(premium_scale, 2)),
            OptionLeg("call", "short", upper, round(premium_scale * 0.45, 2)),
        ],
        "Bear Put Spread": [
            OptionLeg("put", "long", atm, round(premium_scale, 2)),
            OptionLeg("put", "short", lower, round(premium_scale * 0.45, 2)),
        ],
        "Long Straddle": [
            OptionLeg("call", "long", atm, round(premium_scale, 2)),
            OptionLeg("put", "long", atm, round(premium_scale * 0.9, 2)),
        ],
        "Long Strangle": [
            OptionLeg("put", "long", lower, round(premium_scale * 0.65, 2)),
            OptionLeg("call", "long", upper, round(premium_scale * 0.65, 2)),
        ],
        "Collar Overlay": [
            OptionLeg("put", "long", lower, round(premium_scale * 0.65, 2)),
            OptionLeg("call", "short", upper, round(premium_scale * 0.55, 2)),
        ],
    }


def _leg_payoff(leg: OptionLeg, prices: np.ndarray) -> np.ndarray:
    if leg.kind == "call":
        intrinsic = np.maximum(prices - leg.strike, 0.0)
    elif leg.kind == "put":
        intrinsic = np.maximum(leg.strike - prices, 0.0)
    else:
        raise ValueError("kind must be 'call' or 'put'.")

    if leg.side not in {"long", "short"}:
        raise ValueError("side must be 'long' or 'short'.")
    return (intrinsic - leg.premium) * leg.signed_quantity


def _entry_cost(legs: list[OptionLeg]) -> float:
    return float(sum(leg.premium * leg.signed_quantity for leg in legs))


def _breakevens(prices: np.ndarray, payoffs: np.ndarray) -> list[float]:
    breakevens: list[float] = []
    for left_index, right_index in zip(range(len(prices) - 1), range(1, len(prices)), strict=True):
        left_payoff = payoffs[left_index]
        right_payoff = payoffs[right_index]
        if np.isclose(left_payoff, 0.0):
            breakevens.append(float(prices[left_index]))
        if left_payoff * right_payoff < 0:
            slope = (right_payoff - left_payoff) / (prices[right_index] - prices[left_index])
            breakevens.append(float(prices[left_index] - left_payoff / slope))
    if np.isclose(payoffs[-1], 0.0):
        breakevens.append(float(prices[-1]))
    return _dedupe_rounded(breakevens)


def _dedupe_rounded(values: list[float]) -> list[float]:
    rounded: list[float] = []
    for value in values:
        candidate = round(value, 4)
        if candidate not in rounded:
            rounded.append(candidate)
    return rounded


def _risk_label(legs: list[OptionLeg]) -> str:
    has_short_call = any(leg.kind == "call" and leg.side == "short" for leg in legs)
    long_call_cover = sum(
        leg.quantity for leg in legs if leg.kind == "call" and leg.side == "long"
    )
    short_call_exposure = sum(
        leg.quantity for leg in legs if leg.kind == "call" and leg.side == "short"
    )
    if has_short_call and short_call_exposure > long_call_cover:
        return "Unbounded risk"
    return "Defined risk"


def _profit_label(legs: list[OptionLeg]) -> str:
    long_call_exposure = sum(
        leg.quantity for leg in legs if leg.kind == "call" and leg.side == "long"
    )
    short_call_exposure = sum(
        leg.quantity for leg in legs if leg.kind == "call" and leg.side == "short"
    )
    if long_call_exposure > short_call_exposure:
        return "Unbounded profit"
    return "Defined profit"
