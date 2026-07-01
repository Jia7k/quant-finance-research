from __future__ import annotations

import math

import numpy as np
import pandas as pd


def performance_summary(
    returns: pd.Series,
    turnover: pd.Series | None = None,
    periods_per_year: int = 252,
) -> pd.Series:
    """Summarize daily strategy returns."""

    returns = returns.dropna()
    if returns.empty:
        raise ValueError("Cannot summarize an empty return series.")

    equity = (1.0 + returns).cumprod()
    total_return = equity.iloc[-1] - 1.0
    annual_return = (1.0 + total_return) ** (periods_per_year / len(returns)) - 1.0
    annual_volatility = returns.std(ddof=0) * math.sqrt(periods_per_year)
    sharpe = np.nan
    if returns.std(ddof=0) > 0:
        sharpe = returns.mean() / returns.std(ddof=0) * math.sqrt(periods_per_year)

    drawdown = equity.div(equity.cummax()).sub(1.0)
    max_drawdown = drawdown.min()
    calmar = np.nan if max_drawdown == 0 else annual_return / abs(max_drawdown)

    values = {
        "total_return": total_return,
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "calmar": calmar,
        "hit_rate": (returns > 0).mean(),
        "daily_mean_return": returns.mean(),
        "daily_return_std": returns.std(ddof=0),
    }

    if turnover is not None:
        aligned_turnover = turnover.reindex(returns.index).dropna()
        values["average_daily_turnover"] = aligned_turnover.mean()

    return pd.Series(values, name="value")


def information_coefficient(
    signal: pd.DataFrame,
    forward_returns: pd.DataFrame,
    method: str = "spearman",
    min_assets: int = 4,
) -> pd.Series:
    """Cross-sectional correlation between signal and next-period returns."""

    if method not in {"spearman", "pearson"}:
        raise ValueError("method must be 'spearman' or 'pearson'.")

    signal, forward_returns = signal.align(forward_returns, join="inner", axis=None)
    values = {}
    for date in signal.index:
        scores = signal.loc[date]
        returns = forward_returns.loc[date]
        paired = pd.concat({"signal": scores, "return": returns}, axis=1).dropna()
        if len(paired) < min_assets:
            values[date] = np.nan
            continue

        if method == "spearman":
            paired = paired.rank()
        values[date] = paired["signal"].corr(paired["return"])

    series = pd.Series(values, name="information_coefficient")
    series.index = pd.to_datetime(series.index)
    return series


def ic_summary(ic: pd.Series) -> pd.Series:
    """Summarize an information coefficient time series."""

    ic = ic.dropna()
    if ic.empty:
        return pd.Series(
            {
                "mean_ic": np.nan,
                "ic_std": np.nan,
                "ic_t_stat": np.nan,
                "ic_hit_rate": np.nan,
            }
        )

    std = ic.std(ddof=1)
    t_stat = np.nan if std == 0 else ic.mean() / (std / math.sqrt(len(ic)))
    return pd.Series(
        {
            "mean_ic": ic.mean(),
            "ic_std": std,
            "ic_t_stat": t_stat,
            "ic_hit_rate": (ic > 0).mean(),
        }
    )
