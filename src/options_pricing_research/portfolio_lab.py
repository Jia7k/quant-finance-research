from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioReport:
    holdings: pd.DataFrame
    weights: pd.Series
    asset_returns: pd.DataFrame
    returns: pd.Series
    cumulative_returns: pd.Series
    drawdown: pd.Series
    summary: pd.Series
    correlation: pd.DataFrame


def normalize_portfolio(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize uploaded/manual portfolio rows into ticker and quantity columns."""

    if raw.empty:
        raise ValueError("Portfolio is empty.")

    frame = raw.copy()
    frame.columns = [_normalize_column_name(column) for column in frame.columns]
    aliases = {
        "symbol": "ticker",
        "shares": "quantity",
        "units": "quantity",
        "qty": "quantity",
        "target_weight": "weight",
        "portfolio_weight": "weight",
        "average_cost": "cost_basis",
        "avg_cost": "cost_basis",
    }
    frame = frame.rename(columns={column: aliases.get(column, column) for column in frame.columns})

    if "ticker" not in frame.columns:
        raise ValueError("Portfolio must include a ticker column.")
    if "quantity" not in frame.columns and "weight" not in frame.columns:
        raise ValueError("Portfolio must include either quantity or weight.")

    frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    frame = frame[frame["ticker"] != ""].copy()
    if frame.empty:
        raise ValueError("Portfolio has no valid tickers.")

    if "quantity" in frame.columns:
        frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce").fillna(0.0)
    else:
        frame["quantity"] = np.nan

    if "weight" in frame.columns:
        frame["weight"] = pd.to_numeric(frame["weight"], errors="coerce")
    else:
        frame["weight"] = np.nan

    if "cost_basis" in frame.columns:
        frame["cost_basis"] = pd.to_numeric(frame["cost_basis"], errors="coerce")
    else:
        frame["cost_basis"] = np.nan

    grouped = (
        frame.groupby("ticker", as_index=False)
        .agg({"quantity": "sum", "weight": "sum", "cost_basis": "mean"})
        .sort_values("ticker")
    )
    if grouped["quantity"].fillna(0.0).sum() <= 0 and grouped["weight"].fillna(0.0).sum() <= 0:
        raise ValueError("Portfolio quantity or weight must be positive.")
    return grouped.reset_index(drop=True)


def clean_tickers(tickers: Iterable[str]) -> list[str]:
    cleaned = []
    for ticker in tickers:
        normalized = str(ticker).strip().upper()
        if normalized:
            cleaned.append(normalized)
    return list(dict.fromkeys(cleaned))


def download_adjusted_close(
    tickers: Iterable[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """Download adjusted close prices from Yahoo Finance."""

    tickers = clean_tickers(tickers)
    if not tickers:
        raise ValueError("At least one ticker is required.")

    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance is required for portfolio downloads.") from exc

    raw = yf.download(
        " ".join(tickers),
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw.empty:
        raise RuntimeError("No price data returned from Yahoo Finance.")

    close = _extract_close(raw, tickers)
    close = close.dropna(how="all")
    if close.empty:
        raise RuntimeError("No adjusted close prices were available.")
    return close


def build_portfolio_report(
    positions: pd.DataFrame,
    close_prices: pd.DataFrame,
    risk_free_rate: float = 0.0,
) -> PortfolioReport:
    """Value holdings and compute portfolio performance from close prices."""

    positions = normalize_portfolio(positions)
    close_prices = close_prices.copy().sort_index()
    close_prices.columns = [str(column).upper() for column in close_prices.columns]
    tickers = [ticker for ticker in positions["ticker"] if ticker in close_prices.columns]
    if not tickers:
        raise ValueError("None of the portfolio tickers are present in the price data.")

    positions = positions[positions["ticker"].isin(tickers)].copy()
    close_prices = close_prices[tickers].dropna(how="all")
    latest_prices = close_prices.ffill().iloc[-1]

    holdings = positions.set_index("ticker")
    holdings["last_price"] = latest_prices.reindex(holdings.index)
    if holdings["quantity"].fillna(0.0).sum() > 0:
        holdings["market_value"] = holdings["quantity"].fillna(0.0) * holdings["last_price"]
        weights = holdings["market_value"] / holdings["market_value"].sum()
    else:
        weights = holdings["weight"].fillna(0.0)
        weights = weights / weights.sum()
        holdings["market_value"] = weights

    holdings["weight"] = weights
    holdings = holdings.reset_index()

    asset_returns = close_prices.ffill().pct_change().dropna(how="all")
    asset_returns = asset_returns.reindex(columns=weights.index).fillna(0.0)
    portfolio_returns = asset_returns.mul(weights, axis=1).sum(axis=1)
    portfolio_returns.name = "portfolio_return"
    cumulative = (1.0 + portfolio_returns).cumprod()
    cumulative.name = "growth_of_one"
    drawdown = cumulative.div(cumulative.cummax()).sub(1.0)
    drawdown.name = "drawdown"
    summary = performance_summary(portfolio_returns, risk_free_rate=risk_free_rate)
    correlation = asset_returns.corr()

    return PortfolioReport(
        holdings=holdings,
        weights=weights,
        asset_returns=asset_returns,
        returns=portfolio_returns,
        cumulative_returns=cumulative,
        drawdown=drawdown,
        summary=summary,
        correlation=correlation,
    )


def rolling_portfolio_volatility(
    returns: pd.Series,
    window: int = 21,
    periods_per_year: int = 252,
) -> pd.Series:
    """Compute annualized rolling portfolio volatility."""

    if window < 2:
        raise ValueError("window must be at least 2.")

    rolling = returns.dropna().rolling(window=window, min_periods=max(2, window // 2)).std(ddof=0)
    rolling_volatility = rolling * np.sqrt(periods_per_year)
    rolling_volatility.name = f"rolling_{window}d_volatility"
    return rolling_volatility.dropna()


def rolling_average_correlation(
    asset_returns: pd.DataFrame,
    window: int = 60,
) -> pd.Series:
    """Average off-diagonal pairwise correlations through time."""

    if window < 3:
        raise ValueError("window must be at least 3.")

    returns = asset_returns.dropna(how="all")
    if returns.shape[1] < 2:
        return pd.Series(dtype=float, name=f"rolling_{window}d_average_correlation")

    values = []
    dates = []
    min_periods = max(3, window // 2)
    for end in range(min_periods, len(returns) + 1):
        sample = returns.iloc[max(0, end - window) : end]
        corr = sample.corr()
        if corr.shape[0] < 2:
            continue
        mask = ~np.eye(corr.shape[0], dtype=bool)
        values.append(float(corr.to_numpy()[mask].mean()))
        dates.append(returns.index[end - 1])

    series = pd.Series(values, index=pd.Index(dates, name=returns.index.name))
    series.name = f"rolling_{window}d_average_correlation"
    return series.dropna()


def stress_test_portfolio(
    holdings: pd.DataFrame,
    shocks: pd.Series | dict[str, float],
) -> pd.DataFrame:
    """Apply user-supplied price shocks to current holdings."""

    required_columns = {"ticker", "market_value", "weight"}
    missing = required_columns.difference(holdings.columns)
    if missing:
        raise ValueError(f"holdings is missing required columns: {sorted(missing)}")

    frame = holdings[["ticker", "market_value", "weight"]].copy()
    shock_series = pd.Series(shocks, dtype=float)
    shock_series.index = shock_series.index.astype(str).str.upper()
    frame["shock"] = frame["ticker"].map(shock_series).fillna(0.0)
    frame["stressed_market_value"] = frame["market_value"] * (1.0 + frame["shock"])
    frame["stress_pnl"] = frame["stressed_market_value"] - frame["market_value"]
    total_market_value = frame["market_value"].sum()
    if total_market_value <= 0:
        raise ValueError("total market value must be positive.")
    frame["portfolio_impact"] = frame["stress_pnl"] / total_market_value
    return frame


def performance_summary(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> pd.Series:
    """Summarize daily portfolio returns."""

    returns = returns.dropna()
    if returns.empty:
        raise ValueError("Return series is empty.")

    cumulative = (1.0 + returns).cumprod()
    total_return = cumulative.iloc[-1] - 1.0
    annual_return = (1.0 + total_return) ** (periods_per_year / len(returns)) - 1.0
    annual_volatility = returns.std(ddof=0) * np.sqrt(periods_per_year)
    excess_daily = returns - risk_free_rate / periods_per_year
    sharpe = np.nan
    if excess_daily.std(ddof=0) > 0:
        sharpe = excess_daily.mean() / excess_daily.std(ddof=0) * np.sqrt(periods_per_year)
    drawdown = cumulative.div(cumulative.cummax()).sub(1.0)

    return pd.Series(
        {
            "total_return": total_return,
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe": sharpe,
            "max_drawdown": drawdown.min(),
            "best_day": returns.max(),
            "worst_day": returns.min(),
        }
    )


def _extract_close(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        level_zero = [str(value).lower() for value in raw.columns.get_level_values(0)]
        level_one = [str(value).lower() for value in raw.columns.get_level_values(1)]
        if "close" in level_zero:
            close = raw.xs("Close", axis=1, level=0)
        elif "close" in level_one:
            close = raw.xs("Close", axis=1, level=1)
        else:
            raise RuntimeError("Could not find close prices in Yahoo Finance output.")
    else:
        if "Close" not in raw.columns:
            raise RuntimeError("Could not find close prices in Yahoo Finance output.")
        close = raw[["Close"]].rename(columns={"Close": tickers[0]})

    close = close.copy()
    close.columns = [str(column).upper() for column in close.columns]
    close = close.reindex(columns=tickers)
    close.index = pd.to_datetime(close.index).tz_localize(None)
    return close


def _normalize_column_name(column: object) -> str:
    return str(column).strip().lower().replace(" ", "_").replace("-", "_")
