from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    returns: pd.Series
    gross_returns: pd.Series
    costs: pd.Series
    turnover: pd.Series
    weights: pd.DataFrame
    equity_curve: pd.Series


def next_close_returns(close: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """Forward close-to-close returns indexed by the signal formation date."""

    if horizon < 1:
        raise ValueError("horizon must be positive.")
    return close.shift(-horizon).div(close).sub(1.0)


def run_backtest(
    close: pd.DataFrame,
    weights: pd.DataFrame,
    cost_bps: float = 5.0,
    horizon: int = 1,
) -> BacktestResult:
    """Apply weights to forward returns and subtract turnover-based costs."""

    if cost_bps < 0:
        raise ValueError("cost_bps cannot be negative.")

    close = close.sort_index()
    weights = weights.reindex(index=close.index, columns=close.columns).fillna(0.0)
    asset_returns = next_close_returns(close, horizon=horizon)
    valid_dates = asset_returns.notna().any(axis=1)

    turnover = weights.diff().fillna(weights).abs().sum(axis=1)
    costs = turnover * (cost_bps / 10_000.0)
    gross_returns = weights.mul(asset_returns).sum(axis=1, min_count=1).fillna(0.0)
    net_returns = gross_returns.sub(costs)

    returns = net_returns.loc[valid_dates]
    gross_returns = gross_returns.loc[valid_dates]
    costs = costs.loc[valid_dates]
    turnover = turnover.loc[valid_dates]
    equity_curve = (1.0 + returns).cumprod()
    equity_curve.name = "equity"
    returns.name = "return"
    gross_returns.name = "gross_return"
    costs.name = "cost"
    turnover.name = "turnover"

    return BacktestResult(
        returns=returns,
        gross_returns=gross_returns,
        costs=costs,
        turnover=turnover,
        weights=weights.loc[valid_dates],
        equity_curve=equity_curve,
    )
