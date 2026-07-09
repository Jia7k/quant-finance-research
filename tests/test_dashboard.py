import numpy as np

from options_pricing_research.dashboard import (
    black_scholes_surface,
    model_snapshot,
    option_metrics,
    recover_smile_prices,
    synthetic_smile,
)


def test_black_scholes_surface_has_expected_shape_and_monotonicity():
    strikes = np.array([90.0, 100.0, 110.0])
    vols = np.array([0.10, 0.20, 0.30])

    surface = black_scholes_surface("call", 100.0, strikes, vols, 1.0, 0.05)

    assert surface.shape == (3, 3)
    assert surface.loc[0.20, 90.0] > surface.loc[0.20, 100.0] > surface.loc[0.20, 110.0]
    assert surface.loc[0.30, 100.0] > surface.loc[0.10, 100.0]


def test_synthetic_smile_can_be_recovered_by_implied_volatility_solver():
    strikes = np.array([85.0, 100.0, 115.0])
    smile = synthetic_smile(100.0, strikes, base_volatility=0.20)

    recovered = recover_smile_prices("call", 100.0, smile, 0.5, 0.03)

    max_error = (
        recovered["implied_volatility"] - recovered["recovered_implied_volatility"]
    ).abs().max()
    assert max_error < 1e-6


def test_option_metrics_include_display_scaled_greeks():
    price, greeks = option_metrics("call", 100.0, 100.0, 1.0, 0.05, 0.20)

    assert price > 0.0
    assert "vega_per_1pct" in greeks.index
    assert "theta_per_day" in greeks.index


def test_model_snapshot_returns_expected_models():
    snapshot = model_snapshot(
        "call",
        100.0,
        100.0,
        1.0,
        0.05,
        0.20,
        binomial_steps=100,
        heston_paths=5_000,
        heston_steps=64,
        seed=3,
    )

    assert set(snapshot["model"]) == {"Black-Scholes", "CRR binomial", "Heston MC"}
    assert (snapshot["price"] > 0).all()
