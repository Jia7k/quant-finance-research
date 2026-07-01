from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


DEFAULT_TICKERS = [
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "NVDA",
    "JPM",
    "XOM",
    "UNH",
    "PG",
]


@dataclass(frozen=True)
class PriceData:
    """Aligned OHLCV matrices with dates as rows and tickers as columns."""

    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame

    @property
    def tickers(self) -> list[str]:
        return list(self.close.columns)

    def align(self) -> "PriceData":
        frames = [self.open, self.high, self.low, self.close, self.volume]
        index = frames[0].index
        columns = frames[0].columns
        for frame in frames[1:]:
            index = index.intersection(frame.index)
            columns = columns.intersection(frame.columns)

        cleaned = []
        for frame in frames:
            aligned = frame.sort_index().loc[index, columns]
            aligned.index = pd.to_datetime(aligned.index)
            cleaned.append(aligned.astype(float))

        return PriceData(*cleaned)


def clean_tickers(tickers: Iterable[str]) -> list[str]:
    cleaned = []
    for ticker in tickers:
        normalized = ticker.strip().upper()
        if normalized:
            cleaned.append(normalized)
    if not cleaned:
        raise ValueError("At least one ticker is required.")
    return list(dict.fromkeys(cleaned))


def load_ohlcv_csv(path: str | Path) -> PriceData:
    """Load a long-form CSV with date, ticker, open, high, low, close, volume."""

    raw = pd.read_csv(path, parse_dates=["date"])
    required = {"date", "ticker", "open", "high", "low", "close", "volume"}
    missing = required.difference(raw.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

    raw["ticker"] = raw["ticker"].str.upper()

    def pivot(field: str) -> pd.DataFrame:
        return raw.pivot(index="date", columns="ticker", values=field)

    return PriceData(
        open=pivot("open"),
        high=pivot("high"),
        low=pivot("low"),
        close=pivot("close"),
        volume=pivot("volume"),
    ).align()


def download_yfinance(
    tickers: Iterable[str],
    start: str = "2018-01-01",
    end: str | None = None,
) -> PriceData:
    """Download adjusted daily OHLCV data from Yahoo Finance via yfinance."""

    tickers = clean_tickers(tickers)
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for downloads. Install with `pip install yfinance`."
        ) from exc

    raw = yf.download(
        " ".join(tickers),
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=True,
    )
    if raw.empty:
        raise RuntimeError("No data returned from yfinance.")

    return PriceData(
        open=_extract_yfinance_field(raw, "Open", tickers),
        high=_extract_yfinance_field(raw, "High", tickers),
        low=_extract_yfinance_field(raw, "Low", tickers),
        close=_extract_yfinance_field(raw, "Close", tickers),
        volume=_extract_yfinance_field(raw, "Volume", tickers),
    ).align()


def make_synthetic_ohlcv(
    tickers: Iterable[str] | None = None,
    periods: int = 756,
    seed: int = 7,
    start: str = "2021-01-01",
) -> PriceData:
    """Create deterministic demo data with market and idiosyncratic structure."""

    tickers = clean_tickers(tickers or DEFAULT_TICKERS)
    if periods < 80:
        raise ValueError("Synthetic data needs at least 80 periods for the factors.")

    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, periods=periods)
    market = rng.normal(0.00025, 0.009, size=periods)

    close = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    open_ = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    high = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    low = pd.DataFrame(index=dates, columns=tickers, dtype=float)
    volume = pd.DataFrame(index=dates, columns=tickers, dtype=float)

    for i, ticker in enumerate(tickers):
        beta = 0.65 + 0.08 * (i % 6)
        idio_vol = 0.009 + 0.0015 * (i % 5)
        idio = rng.normal(0.0, idio_vol, size=periods)
        slow_signal = np.sin(np.linspace(0, 8 * np.pi, periods) + i / 2) * 0.00045
        returns = beta * market + idio + slow_signal

        close_prices = 70 + 12 * i
        close_path = close_prices * np.exp(np.cumsum(returns))
        overnight = rng.normal(0.00005, 0.0035, size=periods)
        open_path = np.r_[close_path[0], close_path[:-1] * (1 + overnight[1:])]
        high_path = np.maximum(open_path, close_path) * (1 + np.abs(rng.normal(0.002, 0.002, periods)))
        low_path = np.minimum(open_path, close_path) * (1 - np.abs(rng.normal(0.002, 0.002, periods)))

        base_volume = 1_000_000 + 180_000 * i
        volume_path = base_volume * rng.lognormal(mean=0.0, sigma=0.25, size=periods)
        volume_path *= 1 + 8 * np.abs(returns)

        close[ticker] = close_path
        open_[ticker] = open_path
        high[ticker] = high_path
        low[ticker] = low_path
        volume[ticker] = volume_path

    return PriceData(open=open_, high=high, low=low, close=close, volume=volume).align()


def _extract_yfinance_field(
    raw: pd.DataFrame,
    field: str,
    tickers: list[str],
) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        level_zero = [str(value).lower() for value in raw.columns.get_level_values(0)]
        level_one = [str(value).lower() for value in raw.columns.get_level_values(1)]
        field_lower = field.lower()

        if field_lower in level_zero:
            out = raw.xs(field, axis=1, level=0)
        elif field_lower in level_one:
            out = raw.xs(field, axis=1, level=1)
        else:
            raise ValueError(f"Could not find field {field!r} in yfinance output.")
    else:
        if len(tickers) != 1:
            raise ValueError("Expected MultiIndex columns for multiple tickers.")
        if field not in raw.columns:
            raise ValueError(f"Could not find field {field!r} in yfinance output.")
        out = raw[[field]].rename(columns={field: tickers[0]})

    out = out.copy()
    out.columns = [str(column).upper() for column in out.columns]
    out = out.reindex(columns=tickers)
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out
