from __future__ import annotations

import pandas as pd


def make_long_short_weights(
    signal: pd.DataFrame,
    n_long: int = 3,
    n_short: int = 3,
    gross_exposure: float = 1.0,
) -> pd.DataFrame:
    """Convert cross-sectional scores into dollar-neutral daily weights."""

    if n_long < 1 or n_short < 1:
        raise ValueError("n_long and n_short must both be positive.")
    if gross_exposure <= 0:
        raise ValueError("gross_exposure must be positive.")

    weights = pd.DataFrame(0.0, index=signal.index, columns=signal.columns)
    long_budget = gross_exposure / 2.0
    short_budget = gross_exposure / 2.0

    for date, scores in signal.iterrows():
        clean = scores.dropna()
        side_size = min(n_long, n_short, len(clean) // 2)
        if side_size < 1:
            continue

        longs = clean.nlargest(side_size).index
        shorts = clean.nsmallest(side_size).index
        weights.loc[date, longs] = long_budget / side_size
        weights.loc[date, shorts] = -short_budget / side_size

    return weights


def make_long_only_weights(
    signal: pd.DataFrame,
    n_long: int = 5,
    gross_exposure: float = 1.0,
) -> pd.DataFrame:
    """Convert scores into equal-weight top-bucket long-only weights."""

    if n_long < 1:
        raise ValueError("n_long must be positive.")
    if gross_exposure <= 0:
        raise ValueError("gross_exposure must be positive.")

    weights = pd.DataFrame(0.0, index=signal.index, columns=signal.columns)
    for date, scores in signal.iterrows():
        clean = scores.dropna()
        size = min(n_long, len(clean))
        if size < 1:
            continue

        longs = clean.nlargest(size).index
        weights.loc[date, longs] = gross_exposure / size

    return weights
