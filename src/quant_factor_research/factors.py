from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from quant_factor_research.data import PriceData


def compute_factors(data: PriceData) -> dict[str, pd.DataFrame]:
    """Build point-in-time daily factors, shifted to avoid same-day lookahead."""

    data = data.align()
    close = data.close
    returns = close.pct_change()
    overnight = data.open.div(close.shift(1)).sub(1.0)
    average_volume = data.volume.rolling(20, min_periods=15).mean()

    return {
        "momentum_21": close.pct_change(21).shift(1),
        "momentum_63": close.pct_change(63).shift(1),
        "short_reversal_5": -close.pct_change(5).shift(1),
        "low_volatility_21": -returns.rolling(21, min_periods=15).std().shift(1),
        "volume_surprise_20": data.volume.div(average_volume).sub(1.0).shift(1),
        "overnight_mean_5": overnight.rolling(5, min_periods=3).mean().shift(1),
    }


def cross_sectional_zscore(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize each date across the tradable universe."""

    clean = frame.replace([np.inf, -np.inf], np.nan)
    mean = clean.mean(axis=1)
    std = clean.std(axis=1).replace(0.0, np.nan)
    return clean.sub(mean, axis=0).div(std, axis=0)


def build_composite_signal(
    factors: Mapping[str, pd.DataFrame],
    weights: Mapping[str, float] | None = None,
    min_factors: int = 3,
) -> pd.DataFrame:
    """Combine factor z-scores into one cross-sectional ranking signal."""

    if not factors:
        raise ValueError("At least one factor is required.")
    if min_factors < 1:
        raise ValueError("min_factors must be positive.")

    weights = dict(weights or {name: 1.0 for name in factors})
    total: pd.DataFrame | None = None
    denominator: pd.DataFrame | None = None
    available_count: pd.DataFrame | None = None

    for name, factor in factors.items():
        weight = weights.get(name, 0.0)
        if weight == 0:
            continue

        zscore = cross_sectional_zscore(factor)
        contribution = zscore * weight
        present = zscore.notna()
        weighted_presence = present.astype(float) * abs(weight)

        total = contribution if total is None else total.add(contribution, fill_value=0.0)
        denominator = (
            weighted_presence
            if denominator is None
            else denominator.add(weighted_presence, fill_value=0.0)
        )
        available_count = (
            present.astype(int)
            if available_count is None
            else available_count.add(present.astype(int), fill_value=0)
        )

    if total is None or denominator is None or available_count is None:
        raise ValueError("At least one factor must have a non-zero weight.")

    signal = total.div(denominator.replace(0.0, np.nan))
    signal = signal.where(available_count >= min_factors)
    return signal.replace([np.inf, -np.inf], np.nan)
