from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import json
from math import erf, log, sqrt
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from options_pricing_research.dashboard import (  # noqa: E402
    barrier_snapshot,
    black_scholes_surface,
    model_snapshot,
    option_metrics,
    recover_smile_prices,
    synthetic_smile,
)
from options_pricing_research.hedging import simulate_delta_hedge  # noqa: E402
from options_pricing_research.portfolio_lab import (  # noqa: E402
    build_portfolio_report,
    download_adjusted_close,
    normalize_portfolio,
    risk_contribution,
    rolling_average_correlation,
    rolling_portfolio_volatility,
    stress_test_portfolio,
    worst_day_contribution,
)
from options_pricing_research.strategies import (  # noqa: E402
    OptionLeg,
    aggregate_strategy_greeks,
    payoff_table,
    strategy_presets,
    summarize_strategy,
)

PALETTE = {
    "cream": "#F8FAFC",
    "cream_deep": "#EEF4FB",
    "surface": "#FFFFFF",
    "surface_warm": "#F6F9FD",
    "border": "#D8E2F0",
    "border_soft": "#E6EDF7",
    "charcoal": "#0F172A",
    "secondary": "#334155",
    "muted": "#64748B",
    "sage": "#059669",
    "sage_dark": "#1E40AF",
    "terracotta": "#D97706",
    "terracotta_dark": "#DC2626",
    "taupe": "#64748B",
    "slate": "#2563EB",
    "olive": "#475569",
    "clay": "#4F46E5",
}

CHART_COLORS = [
    PALETTE["slate"],
    PALETTE["clay"],
    PALETTE["terracotta"],
    PALETTE["olive"],
    PALETTE["sage"],
    PALETTE["terracotta_dark"],
]

DASHBOARD_PAGES = [
    {"key": "portfolio", "label": "Portfolio"},
    {"key": "strategy", "label": "Strategy Builder"},
    {"key": "scenario", "label": "Scenario Matrix"},
    {"key": "models", "label": "Model Comparison"},
    {"key": "surface", "label": "Price Surface"},
    {"key": "smile", "label": "IV Smile"},
    {"key": "paths", "label": "Path Models"},
    {"key": "hedge", "label": "Delta Hedge"},
    {"key": "inputs", "label": "Inputs & Greeks"},
    {"key": "report", "label": "Report"},
]

RESEARCH_CASE_PRESETS: dict[str, dict[str, object]] = {
    "Balanced ATM Call": {
        "base": {
            "kind": "call",
            "spot": 100.0,
            "strike": 100.0,
            "time_to_expiry": 1.0,
            "risk_free_rate": 0.05,
            "volatility": 0.20,
            "dividend_yield": 0.0,
        },
        "binomial_steps": 300,
        "mc_paths": 20_000,
        "mc_steps": 126,
        "seed": 42,
        "barrier_kind": "down-and-out",
        "barrier": 85.0,
        "hedge_steps": 84,
        "realized_volatility": 0.20,
        "drift": 0.05,
        "hedge_cost_bps": 1.0,
    },
    "Defensive OTM Put": {
        "base": {
            "kind": "put",
            "spot": 100.0,
            "strike": 92.0,
            "time_to_expiry": 0.75,
            "risk_free_rate": 0.04,
            "volatility": 0.28,
            "dividend_yield": 0.01,
        },
        "binomial_steps": 300,
        "mc_paths": 25_000,
        "mc_steps": 126,
        "seed": 21,
        "barrier_kind": "down-and-out",
        "barrier": 78.0,
        "hedge_steps": 63,
        "realized_volatility": 0.30,
        "drift": 0.02,
        "hedge_cost_bps": 1.5,
    },
    "High-Vol Earnings Call": {
        "base": {
            "kind": "call",
            "spot": 100.0,
            "strike": 105.0,
            "time_to_expiry": 0.18,
            "risk_free_rate": 0.05,
            "volatility": 0.55,
            "dividend_yield": 0.0,
        },
        "binomial_steps": 400,
        "mc_paths": 30_000,
        "mc_steps": 64,
        "seed": 7,
        "barrier_kind": "up-and-out",
        "barrier": 135.0,
        "hedge_steps": 36,
        "realized_volatility": 0.62,
        "drift": 0.08,
        "hedge_cost_bps": 3.0,
    },
    "Near-Barrier Knock-Out": {
        "base": {
            "kind": "call",
            "spot": 100.0,
            "strike": 100.0,
            "time_to_expiry": 0.5,
            "risk_free_rate": 0.05,
            "volatility": 0.24,
            "dividend_yield": 0.0,
        },
        "binomial_steps": 350,
        "mc_paths": 20_000,
        "mc_steps": 126,
        "seed": 11,
        "barrier_kind": "down-and-out",
        "barrier": 94.0,
        "hedge_steps": 60,
        "realized_volatility": 0.26,
        "drift": 0.04,
        "hedge_cost_bps": 2.0,
    },
    "Short-Dated Hedge Stress": {
        "base": {
            "kind": "call",
            "spot": 100.0,
            "strike": 98.0,
            "time_to_expiry": 0.12,
            "risk_free_rate": 0.05,
            "volatility": 0.36,
            "dividend_yield": 0.0,
        },
        "binomial_steps": 250,
        "mc_paths": 15_000,
        "mc_steps": 64,
        "seed": 99,
        "barrier_kind": "up-and-out",
        "barrier": 118.0,
        "hedge_steps": 24,
        "realized_volatility": 0.48,
        "drift": -0.04,
        "hedge_cost_bps": 5.0,
    },
}

GROWTH_STRESS_TICKERS = {
    "AAPL",
    "AMZN",
    "GOOGL",
    "GOOG",
    "META",
    "MSFT",
    "NFLX",
    "NVDA",
    "TSLA",
}

RATE_SHOCK_DEFENSIVE_TICKERS = {"BIL", "SHV", "SGOV", "TLT", "IEF", "GLD", "XLP", "XLU"}


def get_research_case_preset(name: str) -> dict[str, object]:
    """Return an independent copy of a named research-case preset."""

    fallback = "Balanced ATM Call"
    preset = RESEARCH_CASE_PRESETS.get(name, RESEARCH_CASE_PRESETS[fallback])
    return deepcopy(preset)


def get_default_inputs() -> dict[str, object]:
    """Return the default active research case."""

    return get_research_case_preset("Balanced ATM Call")


def build_research_snapshot(
    inputs: dict[str, object],
    price: float,
    greeks: pd.Series,
) -> dict[str, str]:
    """Build display-ready facts for the active option setup."""

    base = inputs["base"]
    kind = str(base["kind"])
    spot = float(base["spot"])
    strike = float(base["strike"])
    maturity = float(base["time_to_expiry"])
    moneyness = spot / strike
    premium_pct_spot = price / spot
    breakeven = strike + price if kind == "call" else strike - price

    if abs(moneyness - 1.0) <= 0.01:
        classification = f"ATM {kind}"
    elif (kind == "call" and spot > strike) or (kind == "put" and spot < strike):
        classification = f"ITM {kind}"
    else:
        classification = f"OTM {kind}"

    greek_labels = {
        "delta": "Delta",
        "gamma": "Gamma",
        "vega_per_1pct": "Vega / 1%",
        "theta_per_day": "Theta / day",
    }
    available_greeks = {
        key: abs(float(greeks[key]))
        for key in greek_labels
        if key in greeks.index and pd.notna(greeks[key])
    }
    largest_greek_key = max(available_greeks, key=available_greeks.get)
    trading_days = max(1.0, maturity * 252.0)
    hedge_cadence = trading_days / max(1, int(inputs["hedge_steps"]))

    return {
        "classification": classification,
        "moneyness": f"{moneyness:.4f}",
        "breakeven": f"{breakeven:.4f}",
        "premium_pct_spot": f"{premium_pct_spot:.2%}",
        "largest_greek": greek_labels[largest_greek_key],
        "largest_greek_value": f"{greeks[largest_greek_key]:,.4f}",
        "hedge_cadence": f"{hedge_cadence:.1f} trading days",
    }


def build_probability_snapshot(
    inputs: dict[str, object],
    option_price: float,
) -> dict[str, float]:
    """Estimate expected move and risk-neutral finishing probabilities."""

    base = inputs["base"]
    kind = str(base["kind"])
    spot = float(base["spot"])
    strike = float(base["strike"])
    maturity = float(base["time_to_expiry"])
    rate = float(base["risk_free_rate"])
    volatility = float(base["volatility"])
    dividend_yield = float(base["dividend_yield"])
    expected_move = spot * volatility * sqrt(maturity)
    breakeven = strike + option_price if kind == "call" else strike - option_price

    probability_itm = _risk_neutral_probability_above(
        spot,
        strike,
        maturity,
        rate,
        volatility,
        dividend_yield,
    )
    probability_profit = _risk_neutral_probability_above(
        spot,
        breakeven,
        maturity,
        rate,
        volatility,
        dividend_yield,
    )
    if kind == "put":
        probability_itm = 1.0 - probability_itm
        probability_profit = 1.0 - probability_profit

    return {
        "expected_move": expected_move,
        "expected_move_pct": expected_move / spot,
        "lower_one_sigma": max(0.0, spot - expected_move),
        "upper_one_sigma": spot + expected_move,
        "breakeven": breakeven,
        "probability_itm": probability_itm,
        "probability_profit": probability_profit,
    }


def build_option_scenario_grid(
    inputs: dict[str, object],
    spot_shocks: list[float],
    vol_shocks: list[float],
) -> pd.DataFrame:
    """Reprice the active option across spot and volatility shocks."""

    base = inputs["base"]
    rows = []
    for spot_shock in spot_shocks:
        shocked_spot = float(base["spot"]) * (1.0 + spot_shock)
        for vol_shock in vol_shocks:
            shocked_volatility = max(0.01, float(base["volatility"]) + vol_shock)
            shocked_base = dict(base)
            shocked_base["spot"] = shocked_spot
            shocked_base["volatility"] = shocked_volatility
            price, greeks = option_metrics(**shocked_base)
            rows.append(
                {
                    "spot_shock": spot_shock,
                    "vol_shock": vol_shock,
                    "spot": shocked_spot,
                    "volatility": shocked_volatility,
                    "price": price,
                    "delta": float(greeks["delta"]),
                    "gamma": float(greeks["gamma"]),
                    "vega_per_1pct": float(greeks["vega_per_1pct"]),
                }
            )
    return pd.DataFrame(rows)


def _risk_neutral_probability_above(
    spot: float,
    threshold: float,
    maturity: float,
    risk_free_rate: float,
    volatility: float,
    dividend_yield: float,
) -> float:
    if threshold <= 0:
        return 1.0
    denominator = volatility * sqrt(maturity)
    d2 = (
        log(spot / threshold)
        + (risk_free_rate - dividend_yield - 0.5 * volatility**2) * maturity
    ) / denominator
    return _normal_cdf(d2)


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def build_input_warnings(inputs: dict[str, object]) -> list[str]:
    """Return non-blocking warnings for suspicious research-case inputs."""

    base = inputs["base"]
    spot = float(base["spot"])
    maturity = float(base["time_to_expiry"])
    pricing_volatility = float(base["volatility"])
    realized_volatility = float(inputs["realized_volatility"])
    barrier = float(inputs["barrier"])
    barrier_kind = str(inputs["barrier_kind"])
    mc_paths = int(inputs["mc_paths"])
    warnings: list[str] = []

    if maturity < 0.08:
        warnings.append("Expiry is very short; Greeks and hedge error can change quickly.")
    if pricing_volatility > 0.75:
        warnings.append("Volatility is high; compare model prices against a wider scenario range.")
    elif pricing_volatility < 0.06:
        warnings.append("Volatility is low; small volatility changes may dominate the premium.")

    barrier_distance = abs(barrier / spot - 1.0)
    if barrier_distance <= 0.05:
        warnings.append(f"Barrier is within {barrier_distance:.1%} of spot; path risk can dominate value.")
    if barrier_kind == "down-and-out" and barrier >= spot:
        warnings.append("Down-and-out barrier is already at or above spot; check the barrier direction.")
    if barrier_kind == "up-and-out" and barrier <= spot:
        warnings.append("Up-and-out barrier is already at or below spot; check the barrier direction.")
    if mc_paths < 10_000:
        warnings.append("Monte Carlo paths are low; path-dependent estimates may be noisy.")
    if abs(pricing_volatility - realized_volatility) >= 0.20:
        warnings.append("Realized volatility differs materially from pricing volatility; hedge P&L may be dominated by vol mismatch.")

    return warnings


def validate_portfolio_frame(raw: pd.DataFrame) -> list[str]:
    """Validate uploaded portfolio-like data before normalization."""

    if raw.empty:
        return ["Portfolio CSV is empty."]

    normalized_columns = [_normalize_dashboard_column(column) for column in raw.columns]
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
    columns = {aliases.get(column, column) for column in normalized_columns}
    warnings: list[str] = []
    if "ticker" not in columns:
        warnings.append("Portfolio CSV must include a ticker or symbol column.")
    if "quantity" not in columns and "weight" not in columns:
        warnings.append("Portfolio CSV must include quantity or weight exposure.")
    return warnings


def build_research_case_export(
    inputs: dict[str, object],
    warnings: list[str],
) -> dict[str, object]:
    """Build JSON-serializable export data for the active research case."""

    base = inputs["base"]
    return {
        "base": {
            "kind": str(base["kind"]),
            "spot": float(base["spot"]),
            "strike": float(base["strike"]),
            "time_to_expiry": float(base["time_to_expiry"]),
            "risk_free_rate": float(base["risk_free_rate"]),
            "volatility": float(base["volatility"]),
            "dividend_yield": float(base["dividend_yield"]),
        },
        "model": {
            "binomial_steps": int(inputs["binomial_steps"]),
            "mc_paths": int(inputs["mc_paths"]),
            "mc_steps": int(inputs["mc_steps"]),
            "seed": int(inputs["seed"]),
        },
        "barrier": {
            "kind": str(inputs["barrier_kind"]),
            "level": float(inputs["barrier"]),
        },
        "hedge": {
            "rebalances": int(inputs["hedge_steps"]),
            "realized_volatility": float(inputs["realized_volatility"]),
            "drift": float(inputs["drift"]),
            "cost_bps": float(inputs["hedge_cost_bps"]),
        },
        "warnings": list(warnings),
    }


def build_research_memo(
    inputs: dict[str, object],
    snapshot: dict[str, str],
    warnings: list[str],
    model_prices: pd.DataFrame,
    strategy_summary: object | None = None,
    portfolio_summary: dict[str, object] | None = None,
) -> str:
    """Build a downloadable Markdown memo for the current research state."""

    base = inputs["base"]
    lines = [
        "# Quant Finance Lab Research Memo",
        "",
        "## Option Case",
        "",
        f"- Option: {base['kind']}",
        f"- Spot: {float(base['spot']):.4f}",
        f"- Strike: {float(base['strike']):.4f}",
        f"- Maturity: {float(base['time_to_expiry']):.4f} years",
        f"- Volatility: {float(base['volatility']):.2%}",
        f"- Risk-free rate: {float(base['risk_free_rate']):.2%}",
        f"- Dividend yield: {float(base['dividend_yield']):.2%}",
        "",
        "## Snapshot",
        "",
        f"- Classification: {snapshot['classification']}",
        f"- Moneyness: {snapshot['moneyness']}",
        f"- Breakeven: {snapshot['breakeven']}",
        f"- Premium / spot: {snapshot['premium_pct_spot']}",
        f"- Largest Greek: {snapshot['largest_greek']} ({snapshot['largest_greek_value']})",
        f"- Hedge cadence: {snapshot['hedge_cadence']}",
        "",
        "## Assumption Checks",
        "",
    ]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No input warnings.")

    lines.extend(["", "## Model Prices", "", _markdown_table(model_prices), "", "## Strategy", ""])
    if strategy_summary is None:
        lines.append("No strategy has been built in this session.")
    else:
        lines.extend(
            [
                f"- Entry cost: {_format_optional_number(getattr(strategy_summary, 'entry_cost', None))}",
                f"- Max profit: {_format_optional_number(getattr(strategy_summary, 'max_profit', None))}",
                f"- Max loss: {_format_optional_number(getattr(strategy_summary, 'max_loss', None))}",
                f"- Risk: {getattr(strategy_summary, 'risk_label', 'Unavailable')}",
                f"- Profit: {getattr(strategy_summary, 'profit_label', 'Unavailable')}",
            ]
        )

    lines.extend(["", "## Portfolio", ""])
    if portfolio_summary is None:
        lines.append("No portfolio analysis has been run in this session.")
    else:
        for key, value in portfolio_summary.items():
            lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows available._"

    display = frame.copy()
    display.columns = [str(column) for column in display.columns]
    rows = [
        "| " + " | ".join(display.columns) + " |",
        "| " + " | ".join("---" for _ in display.columns) + " |",
    ]
    for row in display.itertuples(index=False):
        values = [_format_markdown_cell(value) for value in row]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def _format_markdown_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|")


def _format_optional_number(value: object | None) -> str:
    if value is None:
        return "Unbounded"
    if isinstance(value, (float, int)):
        return f"{value:,.4f}"
    return str(value)


def _normalize_dashboard_column(column: object) -> str:
    return str(column).strip().lower().replace(" ", "_").replace("-", "_")


st.set_page_config(
    page_title="Options Pricing Lab",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main() -> None:
    apply_theme()
    render_app_header()
    ensure_session_defaults()

    page_labels = [page["label"] for page in DASHBOARD_PAGES]
    selected_page = st.segmented_control(
        "Workspace",
        page_labels,
        default=st.session_state.get("dashboard_page", "Portfolio"),
        key="dashboard_page",
    )
    inputs = st.session_state["active_inputs"]

    if selected_page == "Inputs & Greeks":
        inputs = render_inputs_and_greeks()
    elif selected_page == "Portfolio":
        render_current_case_strip(inputs)
        render_portfolio_lab(inputs)
    elif selected_page == "Strategy Builder":
        render_current_case_strip(inputs)
        render_strategy_builder(inputs)
    elif selected_page == "Scenario Matrix":
        render_current_case_strip(inputs)
        render_scenario_matrix(inputs)
    elif selected_page == "Model Comparison":
        render_current_case_strip(inputs)
        render_model_comparison(inputs)
    elif selected_page == "Price Surface":
        render_current_case_strip(inputs)
        render_surface(inputs)
    elif selected_page == "IV Smile":
        render_current_case_strip(inputs)
        render_smile(inputs)
    elif selected_page == "Path Models":
        render_current_case_strip(inputs)
        render_path_models(inputs)
    elif selected_page == "Delta Hedge":
        render_current_case_strip(inputs)
        render_delta_hedge(inputs)
    elif selected_page == "Report":
        render_current_case_strip(inputs)
        render_report_mode(inputs)


def ensure_session_defaults() -> None:
    if "active_inputs" not in st.session_state:
        st.session_state["active_inputs"] = get_default_inputs()
    if "latest_strategy_summary" not in st.session_state:
        st.session_state["latest_strategy_summary"] = None
    if "latest_portfolio_summary" not in st.session_state:
        st.session_state["latest_portfolio_summary"] = None


def render_current_case_strip(inputs: dict[str, object]) -> None:
    base = inputs["base"]
    st.caption(
        "Current case: "
        f"{str(base['kind']).upper()} K {float(base['strike']):.2f}, "
        f"spot {float(base['spot']):.2f}, "
        f"vol {float(base['volatility']):.1%}, "
        f"expiry {float(base['time_to_expiry']):.2f}y. "
        "Use Inputs & Greeks to edit assumptions."
    )


def render_app_header() -> None:
    st.markdown(
        """
        <section class="app-header">
            <div class="header-copy">
                <span class="eyebrow">Options research workstation</span>
                <h1>Quant Finance Lab</h1>
                <p>
                    Price options, inspect Greeks, stress portfolios, and test hedge behavior
                    in one compact research surface.
                </p>
            </div>
            <div class="header-pills" aria-label="Dashboard capabilities">
                <span>Streamlit app</span>
                <span>BSM / CRR / Heston</span>
                <span>Portfolio risk</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_inputs_and_greeks() -> dict[str, object]:
    st.subheader("Option Inputs and Greeks")
    preset_name = st.selectbox("Research case", list(RESEARCH_CASE_PRESETS), index=0)
    preset = get_research_case_preset(preset_name)
    base_defaults = preset["base"]
    preset_widget_key = _normalize_dashboard_column(preset_name)
    st.caption("Preset values load as defaults. Adjust any input to turn the case into your own scenario.")

    option_col, numerics_col, path_col = st.columns(3)
    with option_col:
        st.markdown("#### Contract")
        kind = st.segmented_control(
            "Option",
            ["call", "put"],
            default=str(base_defaults["kind"]),
            key=f"{preset_widget_key}_kind",
        )
        spot = st.number_input(
            "Spot",
            min_value=1.0,
            value=float(base_defaults["spot"]),
            step=1.0,
            key=f"{preset_widget_key}_spot",
        )
        strike = st.number_input(
            "Strike",
            min_value=1.0,
            value=float(base_defaults["strike"]),
            step=1.0,
            key=f"{preset_widget_key}_strike",
        )
        maturity = st.slider(
            "Maturity, years",
            0.05,
            3.0,
            float(base_defaults["time_to_expiry"]),
            0.05,
            key=f"{preset_widget_key}_maturity",
        )
        volatility_pct = st.slider(
            "Volatility",
            1.0,
            100.0,
            float(base_defaults["volatility"]) * 100.0,
            1.0,
            key=f"{preset_widget_key}_volatility",
        )
        rate_pct = st.slider(
            "Risk-free rate",
            -2.0,
            12.0,
            float(base_defaults["risk_free_rate"]) * 100.0,
            0.25,
            key=f"{preset_widget_key}_rate",
        )
        dividend_pct = st.slider(
            "Dividend yield",
            0.0,
            8.0,
            float(base_defaults["dividend_yield"]) * 100.0,
            0.25,
            key=f"{preset_widget_key}_dividend",
        )

    with numerics_col:
        st.markdown("#### Model Settings")
        binomial_steps = st.slider(
            "Binomial steps",
            25,
            1_000,
            int(preset["binomial_steps"]),
            25,
            key=f"{preset_widget_key}_binomial_steps",
        )
        mc_paths = st.slider(
            "Monte Carlo paths",
            5_000,
            60_000,
            int(preset["mc_paths"]),
            5_000,
            key=f"{preset_widget_key}_mc_paths",
        )
        mc_steps = st.slider(
            "Path steps",
            32,
            252,
            int(preset["mc_steps"]),
            16,
            key=f"{preset_widget_key}_mc_steps",
        )
        seed = st.number_input(
            "Seed",
            min_value=1,
            value=int(preset["seed"]),
            step=1,
            key=f"{preset_widget_key}_seed",
        )

        st.markdown("#### Barrier")
        barrier_options = ["down-and-out", "up-and-out"]
        barrier_kind = st.selectbox(
            "Barrier type",
            barrier_options,
            index=barrier_options.index(str(preset["barrier_kind"])),
            key=f"{preset_widget_key}_barrier_kind",
        )
        barrier = st.number_input(
            "Barrier",
            min_value=1.0,
            value=float(preset["barrier"]),
            step=1.0,
            key=f"{preset_widget_key}_barrier",
        )

    with path_col:
        st.markdown("#### Delta Hedge")
        hedge_steps = st.slider(
            "Hedge rebalances",
            12,
            252,
            int(preset["hedge_steps"]),
            12,
            key=f"{preset_widget_key}_hedge_steps",
        )
        realized_vol_pct = st.slider(
            "Realized volatility",
            1.0,
            100.0,
            float(preset["realized_volatility"]) * 100.0,
            1.0,
            key=f"{preset_widget_key}_realized_volatility",
        )
        drift_pct = st.slider(
            "Realized drift",
            -20.0,
            30.0,
            float(preset["drift"]) * 100.0,
            0.5,
            key=f"{preset_widget_key}_drift",
        )
        hedge_cost_bps = st.slider(
            "Hedge cost, bps",
            0.0,
            25.0,
            float(preset["hedge_cost_bps"]),
            0.5,
            key=f"{preset_widget_key}_hedge_cost_bps",
        )

    base = {
        "kind": kind,
        "spot": spot,
        "strike": strike,
        "time_to_expiry": maturity,
        "risk_free_rate": rate_pct / 100.0,
        "volatility": volatility_pct / 100.0,
        "dividend_yield": dividend_pct / 100.0,
    }
    inputs = {
        "base": base,
        "binomial_steps": binomial_steps,
        "mc_paths": mc_paths,
        "mc_steps": mc_steps,
        "seed": int(seed),
        "barrier_kind": barrier_kind,
        "barrier": barrier,
        "hedge_steps": hedge_steps,
        "realized_volatility": realized_vol_pct / 100.0,
        "drift": drift_pct / 100.0,
        "hedge_cost_bps": hedge_cost_bps,
    }
    st.session_state["active_inputs"] = deepcopy(inputs)
    price, greeks = render_greek_metrics(inputs)
    warnings = build_input_warnings(inputs)
    render_research_snapshot(build_research_snapshot(inputs, price, greeks))
    render_input_warnings(warnings)
    st.download_button(
        "Download research case JSON",
        data=json.dumps(build_research_case_export(inputs, warnings), indent=2),
        file_name="research_case.json",
        mime="application/json",
        width="stretch",
    )
    return inputs


def render_greek_metrics(inputs: dict[str, object]) -> tuple[float, pd.Series]:
    price, greeks = option_metrics(**inputs["base"])
    metric_cols = st.columns(5)
    metric_cols[0].metric("Black-Scholes price", f"{price:,.4f}")
    metric_cols[1].metric("Delta", f"{greeks['delta']:,.4f}")
    metric_cols[2].metric("Gamma", f"{greeks['gamma']:,.4f}")
    metric_cols[3].metric("Vega / 1%", f"{greeks['vega_per_1pct']:,.4f}")
    metric_cols[4].metric("Theta / day", f"{greeks['theta_per_day']:,.4f}")
    return price, greeks


def render_research_snapshot(snapshot: dict[str, str]) -> None:
    st.markdown(
        f"""
        <section class="research-panel">
            <div>
                <span class="panel-eyebrow">Research snapshot</span>
                <strong>{snapshot["classification"]}</strong>
                <small>Moneyness {snapshot["moneyness"]}</small>
            </div>
            <div>
                <span>Breakeven</span>
                <strong>{snapshot["breakeven"]}</strong>
            </div>
            <div>
                <span>Premium / spot</span>
                <strong>{snapshot["premium_pct_spot"]}</strong>
            </div>
            <div>
                <span>Largest Greek</span>
                <strong>{snapshot["largest_greek"]}</strong>
                <small>{snapshot["largest_greek_value"]}</small>
            </div>
            <div>
                <span>Hedge cadence</span>
                <strong>{snapshot["hedge_cadence"]}</strong>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_input_warnings(warnings: list[str]) -> None:
    if not warnings:
        st.markdown(
            """
            <section class="check-panel check-panel-good">
                <strong>Input checks passed.</strong>
                <span>No obvious contract, barrier, or hedge setup warnings.</span>
            </section>
            """,
            unsafe_allow_html=True,
        )
        return

    warning_items = "".join(f"<li>{warning}</li>" for warning in warnings)
    st.markdown(
        f"""
        <section class="check-panel">
            <strong>Review these assumptions</strong>
            <ul>{warning_items}</ul>
        </section>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False, ttl=60 * 60)
def cached_adjusted_close(
    tickers: tuple[str, ...],
    start: str,
    end: str,
) -> pd.DataFrame:
    return download_adjusted_close(tickers, start=start, end=end)


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #F8FAFC;
            --bg-elevated: #EEF4FB;
            --surface: #FFFFFF;
            --surface-2: #F6F9FD;
            --surface-3: #EAF1FA;
            --border: #D8E2F0;
            --border-soft: #E6EDF7;
            --text: #0F172A;
            --text-soft: #334155;
            --muted: #64748B;
            --accent: #1E40AF;
            --accent-hover: #1D4ED8;
            --accent-2: #D97706;
            --success: #059669;
            --danger: #DC2626;
            --focus: rgba(30, 64, 175, 0.18);
        }
        html, body, [class*="css"] {
            font-family: Inter, "Source Sans 3", "Source Sans Pro", -apple-system,
                BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--text);
        }
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(180deg, var(--bg) 0%, #EFF5FC 100%);
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stToolbar"] {
            right: 0.75rem;
        }
        #MainMenu,
        footer {
            visibility: hidden;
        }
        section[data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none;
        }
        .block-container {
            max-width: 1420px;
            padding-top: 0.85rem;
            padding-bottom: 3.2rem;
        }
        .app-header {
            align-items: flex-end;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
            display: grid;
            gap: 0.9rem;
            grid-template-columns: minmax(0, 1fr) auto;
            margin-bottom: 0.85rem;
            overflow: hidden;
            padding: 0.88rem 1.05rem;
            position: relative;
        }
        .app-header::before {
            background: var(--accent);
            content: "";
            height: 3px;
            inset: 0 0 auto;
            position: absolute;
        }
        .header-copy {
            min-width: 0;
        }
        .eyebrow {
            color: var(--accent);
            display: block;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 0.26rem;
            text-transform: uppercase;
        }
        .app-header h1 {
            color: var(--text);
            font-size: clamp(1.65rem, 2.4vw, 2.35rem);
            font-weight: 780;
            letter-spacing: 0;
            line-height: 1.04;
            margin: 0;
        }
        .app-header p {
            color: var(--text-soft);
            font-size: 0.92rem;
            line-height: 1.55;
            margin: 0.44rem 0 0;
            max-width: 760px;
        }
        .header-pills {
            align-content: end;
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            justify-content: flex-end;
            max-width: 360px;
        }
        .header-pills span {
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: 999px;
            color: var(--text-soft);
            font-size: 0.72rem;
            font-weight: 720;
            line-height: 1;
            padding: 0.42rem 0.58rem;
            white-space: nowrap;
        }
        h1, h2, h3, h4 {
            color: var(--text);
            letter-spacing: 0;
        }
        h2, h3, h4 {
            font-weight: 720;
        }
        h3 {
            margin-top: 0.8rem;
        }
        p, label, span, div {
            letter-spacing: 0;
        }
        label, [data-testid="stWidgetLabel"] p {
            color: var(--text-soft);
            font-weight: 650;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stCaptionContainer"] {
            color: var(--text-soft);
        }
        [data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
            min-height: 104px;
            overflow: hidden;
            padding: 0.9rem 0.95rem;
            position: relative;
        }
        [data-testid="stMetric"]::before {
            background: var(--accent);
            content: "";
            height: 2px;
            inset: 0 0 auto;
            position: absolute;
        }
        [data-testid="stMetricLabel"] p {
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 750;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--text);
            font-variant-numeric: tabular-nums;
            font-weight: 780;
        }
        .research-panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
            display: grid;
            gap: 0;
            grid-template-columns: 1.2fr repeat(4, minmax(0, 1fr));
            margin: 0.95rem 0 0.75rem;
            overflow: hidden;
        }
        .research-panel > div {
            border-right: 1px solid var(--border-soft);
            min-width: 0;
            padding: 0.78rem 0.88rem;
        }
        .research-panel > div:last-child {
            border-right: 0;
        }
        .research-panel span,
        .research-panel small {
            color: var(--muted);
            display: block;
            font-size: 0.72rem;
            font-weight: 680;
            line-height: 1.35;
        }
        .research-panel strong {
            color: var(--text);
            display: block;
            font-size: 0.94rem;
            font-variant-numeric: tabular-nums;
            line-height: 1.3;
            margin-top: 0.16rem;
        }
        .research-panel .panel-eyebrow {
            color: var(--accent);
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
        }
        .check-panel {
            background: #FFFBEB;
            border: 1px solid #FED7AA;
            border-radius: 8px;
            color: #7C2D12;
            margin: 0.55rem 0 0.75rem;
            padding: 0.78rem 0.9rem;
        }
        .check-panel strong {
            color: #7C2D12;
            display: block;
            font-size: 0.86rem;
            margin-bottom: 0.25rem;
        }
        .check-panel ul {
            margin: 0.25rem 0 0;
            padding-left: 1.1rem;
        }
        .check-panel li {
            font-size: 0.82rem;
            line-height: 1.45;
            margin: 0.12rem 0;
        }
        .check-panel-good {
            background: #ECFDF5;
            border-color: #A7F3D0;
            color: #065F46;
        }
        .check-panel-good strong,
        .check-panel-good span {
            color: #065F46;
        }
        [data-testid="stDataFrame"],
        [data-testid="stDataEditor"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
            overflow: hidden;
            margin: 0.35rem 0 1rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border-color: var(--border);
            border-radius: 8px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }
        [data-testid="stVerticalBlockBorderWrapper"] h4 {
            color: var(--text);
            font-size: 0.9rem;
            font-weight: 760;
            margin-bottom: 0.55rem;
        }
        [data-testid="stDataFrame"] [role="columnheader"] {
            color: var(--text);
            font-weight: 720;
        }
        [data-testid="stDataFrame"] [role="gridcell"] {
            color: var(--text-soft);
        }
        .stTabs [data-baseweb="tab-list"] {
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: 8px;
            gap: 0.28rem;
            margin-bottom: 0.9rem;
            padding: 0.28rem;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 7px;
            color: var(--muted);
            font-weight: 720;
            min-height: 2.35rem;
            padding: 0.55rem 0.8rem;
            transition: background 160ms ease, border-color 160ms ease, color 160ms ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(30, 64, 175, 0.06);
            color: var(--accent);
        }
        .stTabs [aria-selected="true"] {
            background: var(--surface);
            border-color: #BFDBFE;
            box-shadow: 0 4px 14px rgba(30, 64, 175, 0.10);
            color: var(--accent);
        }
        section[data-testid="stSidebar"] {
            background: var(--surface);
            border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--text);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: var(--text-soft);
        }
        .stButton button {
            background: var(--accent);
            border: 1px solid var(--accent);
            border-radius: 8px;
            color: #FFFFFF;
            font-weight: 700;
            min-height: 2.45rem;
            transition: background 160ms ease, border-color 160ms ease;
        }
        .stButton button:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
            color: #FFFFFF;
        }
        .stButton button:focus {
            box-shadow: 0 0 0 3px var(--focus);
        }
        input, textarea, [data-baseweb="select"] > div {
            background-color: var(--surface);
            border-color: var(--border);
            border-radius: 8px;
            color: var(--text);
        }
        input:focus, textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--focus);
        }
        [data-baseweb="popover"],
        [data-baseweb="menu"] {
            background: var(--surface);
            color: var(--text);
        }
        [data-testid="stFileUploader"] section {
            background: var(--surface-2);
            border-color: var(--border);
            border-radius: 8px;
        }
        [data-testid="stAlert"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-soft);
        }
        code {
            background: #EEF4FF;
            border-radius: 6px;
            color: var(--accent);
        }
        hr {
            border-color: var(--border-soft);
        }
        div[data-testid="stDialog"] div[role="dialog"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 28px 90px rgba(15, 23, 42, 0.18);
        }
        div[data-testid="stDialog"] h3 {
            color: var(--text);
        }
        .chart-guide {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.5rem;
            margin: 0.35rem 0 0.75rem;
        }
        .chart-guide-item {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
            padding: 0.6rem 0.68rem;
        }
        .chart-guide-value {
            color: var(--text);
            display: block;
            font-size: 0.88rem;
            font-weight: 760;
            line-height: 1.2;
        }
        .chart-guide-label {
            color: var(--accent);
            display: block;
            font-size: 0.76rem;
            font-weight: 720;
            margin-top: 0.18rem;
        }
        .chart-guide-note {
            color: var(--text-soft);
            display: block;
            font-size: 0.72rem;
            line-height: 1.35;
            margin-top: 0.22rem;
        }
        .chart-guide-footnote {
            color: var(--muted);
            font-size: 0.75rem;
            line-height: 1.45;
            margin: -0.35rem 0 0.65rem;
        }
        .chart-click-note {
            color: var(--muted);
            font-size: 0.74rem;
            line-height: 1.35;
            margin: -0.45rem 0 0.9rem;
        }
        [data-testid="stExpander"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
        }
        @media (max-width: 760px) {
            .block-container {
                padding-left: 0.9rem;
                padding-right: 0.9rem;
                padding-top: 0.9rem;
            }
            .app-header {
                grid-template-columns: 1fr;
                padding: 1rem;
            }
            .header-pills {
                justify-content: flex-start;
                max-width: none;
            }
            .chart-guide {
                grid-template-columns: 1fr;
            }
            .research-panel {
                grid-template-columns: 1fr;
            }
            .research-panel > div {
                border-bottom: 1px solid var(--border-soft);
                border-right: 0;
            }
            .research-panel > div:last-child {
                border-bottom: 0;
            }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.001ms !important;
                animation-iteration-count: 1 !important;
                scroll-behavior: auto !important;
                transition-duration: 0.001ms !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def earth_colors(count: int) -> list[str]:
    return [CHART_COLORS[index % len(CHART_COLORS)] for index in range(count)]


CHART_READING_GUIDES = {
    "model_comparison": {
        "items": [
            ("Higher bar", "Higher model premium", "The model assigns more value to the same option payoff."),
            ("Close bars", "Models agree", "Similar prices suggest assumptions are not changing the result much."),
            ("Wide gap", "Assumption risk", "Differences point to exercise, volatility, or simulation assumptions."),
        ],
        "footnote": "Use this as a model sanity check. It does not say whether the option is cheap or expensive versus the real market.",
    },
    "allocation": {
        "items": [
            ("30%+", "High concentration", "One holding can dominate portfolio return and drawdown."),
            ("10-30%", "Meaningful weight", "The position matters, but may not control the whole portfolio."),
            ("<10%", "Smaller exposure", "The position usually has less impact unless it is very volatile."),
        ],
        "footnote": "Weights are based on current market value: latest price multiplied by quantity.",
    },
    "portfolio_growth": {
        "items": [
            ("1.20", "+20% return", "One starting dollar has grown to 1.20 dollars."),
            ("1.00", "No net change", "The portfolio is back near its starting value."),
            ("0.85", "-15% return", "One starting dollar has fallen to 0.85 dollars."),
        ],
        "footnote": "This is historical growth from the selected window, not a forecast.",
    },
    "portfolio_drawdown": {
        "items": [
            ("0%", "At a high", "The portfolio is at or near its previous peak."),
            ("-10%", "Below peak", "The portfolio is 10% below its prior high-water mark."),
            ("-25%", "Deep drawdown", "Losses from the previous peak are large and painful."),
        ],
        "footnote": "Drawdown measures the path of losses, which can be hidden by final return alone.",
    },
    "rolling_volatility": {
        "items": [
            ("Higher line", "More unstable", "Daily returns have been swinging more inside the window."),
            ("Lower line", "Calmer period", "Recent returns have been smaller and more stable."),
            ("Annualized", "Yearly scale", "The daily rolling standard deviation is scaled by sqrt(252)."),
        ],
        "footnote": "Rolling volatility is backward-looking. It helps identify risk regimes, not guaranteed future risk.",
    },
    "rolling_correlation": {
        "items": [
            ("+1.0", "Move together", "Portfolio holdings are behaving more like one shared bet."),
            ("0.0", "Mixed drivers", "Average co-movement is weak across holdings."),
            ("Rising line", "Less diversification", "Correlations are clustering higher in the recent window."),
        ],
        "footnote": "This averages the off-diagonal correlations, so self-correlation cells are excluded.",
    },
    "risk_contribution": {
        "items": [
            ("Largest bar", "Main risk driver", "This ticker contributes the biggest share of portfolio volatility."),
            ("Weight vs risk", "Not the same", "A smaller holding can dominate risk if it is volatile or highly correlated."),
            ("Share sums", "Portfolio split", "Contribution percentages sum to the portfolio's volatility mix."),
        ],
        "footnote": "Volatility contribution uses the selected historical return window and current portfolio weights.",
    },
    "worst_day_contribution": {
        "items": [
            ("Most negative", "Largest drag", "This holding hurt the portfolio most on the worst return day."),
            ("Positive bar", "Offset", "This holding helped cushion losses during that same day."),
            ("Sum bars", "Worst-day return", "The weighted ticker contributions add back to the portfolio return."),
        ],
        "footnote": "Worst-day contribution explains one historical day, not every drawdown in the window.",
    },
    "correlation": {
        "items": [
            ("+1.0", "Move together", "Both tickers' returns usually rise and fall in the same direction."),
            ("0.0", "Weak / no link", "Returns do not show a clear linear relationship in this window."),
            ("-1.0", "Move opposite", "One ticker's return tends to rise when the other's return falls."),
        ],
        "footnote": "Correlation uses daily percentage returns, not prices. The diagonal is always 1.0 because each ticker is compared with itself.",
    },
    "hedge_path": {
        "items": [
            ("Spot", "Underlying path", "The simulated stock price that drives option value."),
            ("Delta 0.60", "Hedge ratio", "The hedge holds about 0.60 shares per short option."),
            ("Fast change", "Gamma pressure", "Rapid Delta moves mean the hedge needs more rebalancing."),
        ],
        "footnote": "This chart is about how the hedge adjusts as spot and time change.",
    },
    "hedge_pnl": {
        "items": [
            ("0", "Ideal center", "A perfect continuous hedge would stay close to zero."),
            ("Positive", "Hedge surplus", "The hedge is ahead at that point in the simulation."),
            ("Costs", "Rebalancing drag", "Transaction costs accumulate each time the hedge trades."),
        ],
        "footnote": "Large moves away from zero highlight discrete hedging, transaction costs, and model mismatch.",
    },
    "price_surface": {
        "items": [
            ("Higher cell", "Higher premium", "The model price is larger for that strike-volatility pair."),
            ("Higher vol", "More uncertainty", "More volatility usually increases option value."),
            ("Strike", "Moneyness", "Strike changes how far the option is in or out of the money."),
        ],
        "footnote": "Each cell holds spot, maturity, rate, and dividend yield fixed while strike and volatility change.",
    },
    "iv_smile": {
        "items": [
            ("Higher IV", "Richer option", "Black-Scholes needs more volatility to match that price."),
            ("Flat line", "Constant vol", "This is close to the simple Black-Scholes assumption."),
            ("Skew / smile", "Different risk", "The market prices strikes with different implied volatility."),
        ],
        "footnote": "Implied volatility is backed out from prices; it is not a direct forecast of future volatility.",
    },
    "barrier": {
        "items": [
            ("Vanilla", "No barrier", "The option keeps value across more price paths."),
            ("Knock-out", "Path can cancel", "Touching the barrier can make the option worthless."),
            ("Gap", "Barrier discount", "The price difference is value lost to the barrier condition."),
        ],
        "footnote": "Barrier options are path-dependent, so the route taken by spot matters, not only the final price.",
    },
    "stress_test": {
        "items": [
            ("Negative bar", "Loss impact", "The shocked price move reduces portfolio value."),
            ("Positive bar", "Gain impact", "The shocked price move adds to portfolio value."),
            ("Total impact", "Scenario result", "Sum each holding's stressed P&L to estimate portfolio-level effect."),
        ],
        "footnote": "This is a simple first-order price shock. It does not model changing correlations, liquidity, or second-order option effects.",
    },
}


def render_chart_guide(chart_key: str) -> None:
    guide = CHART_READING_GUIDES.get(chart_key)
    if guide is None:
        return

    items = "\n".join(
        f"""
        <div class="chart-guide-item">
            <span class="chart-guide-value">{value}</span>
            <span class="chart-guide-label">{label}</span>
            <span class="chart-guide-note">{note}</span>
        </div>
        """
        for value, label, note in guide["items"]
    )
    st.markdown(
        f"""
        <div class="chart-guide">
            {items}
        </div>
        <div class="chart-guide-footnote">
            {guide["footnote"]}
        </div>
        """,
        unsafe_allow_html=True,
    )


CHART_GUIDES = {
    "model_comparison": {
        "title": "Model price comparison",
        "summary": (
            "This chart compares option prices generated by different models using the "
            "same headline inputs. Large gaps usually mean the model assumptions are "
            "materially different, not that one number is automatically correct."
        ),
        "technical": (
            "Black-Scholes assumes constant volatility and European exercise. The CRR "
            "binomial tree approximates the same process in discrete time. Heston Monte "
            "Carlo allows variance to move randomly, so the quoted price includes "
            "simulation error and stochastic-volatility assumptions."
        ),
        "recommendations": [
            "Use Black-Scholes as a fast benchmark.",
            "Use binomial trees when exercise rules or discrete monitoring matter.",
            "Use Heston-style models as exploratory tools unless parameters are calibrated.",
        ],
    },
    "allocation": {
        "title": "Portfolio allocation",
        "summary": (
            "This chart shows how much of the portfolio is allocated to each holding by "
            "current market value. Higher bars mean that ticker dominates portfolio risk "
            "and return more strongly."
        ),
        "technical": (
            "Weights are computed from latest price times quantity, then normalized by "
            "total market value. A 40% weight means roughly 40 cents of every portfolio "
            "dollar is exposed to that ticker before considering correlations."
        ),
        "recommendations": [
            "Watch for single-name concentration above 25-30%.",
            "Compare weights with correlation before assuming the portfolio is diversified.",
            "For Singapore tickers, use Yahoo suffixes such as D05.SI.",
        ],
    },
    "portfolio_growth": {
        "title": "Growth of one dollar",
        "summary": (
            "This line shows how one dollar invested in the current weighted portfolio "
            "would have grown over the selected historical window."
        ),
        "technical": (
            "Daily portfolio returns are built from each asset's daily return multiplied "
            "by its portfolio weight. The curve is the cumulative product of one plus "
            "those daily returns."
        ),
        "recommendations": [
            "Look for smoothness as well as final return.",
            "Compare this curve with drawdown to understand the path taken to earn returns.",
            "Do not treat a short historical window as a stable forecast.",
        ],
    },
    "portfolio_drawdown": {
        "title": "Portfolio drawdown",
        "summary": (
            "Drawdown measures how far the portfolio has fallen from its previous peak. "
            "The deeper the area below zero, the more painful the loss period."
        ),
        "technical": (
            "Drawdown is calculated as current cumulative value divided by the running "
            "maximum cumulative value, minus one. A -20% drawdown means the portfolio is "
            "20% below its prior high."
        ),
        "recommendations": [
            "Use max drawdown alongside volatility; they describe different risks.",
            "If drawdowns cluster, inspect portfolio concentration and correlations.",
            "Stress test position sizes before adding leverage.",
        ],
    },
    "rolling_volatility": {
        "title": "Rolling portfolio volatility",
        "summary": (
            "This chart shows how unstable portfolio returns have been over a moving "
            "historical window. Higher values mean the portfolio has recently been "
            "swinging more day to day."
        ),
        "technical": (
            "The chart calculates the rolling standard deviation of daily portfolio "
            "returns and annualizes it by multiplying by the square root of 252 trading "
            "days. It is a realized-risk measure, not an implied or forecast volatility."
        ),
        "recommendations": [
            "Compare spikes with drawdowns to see whether risk rose during losses.",
            "If volatility trends up, reduce concentration before adding leverage.",
            "Use a longer window for smoother regimes and a shorter window for faster alerts.",
        ],
    },
    "rolling_correlation": {
        "title": "Rolling average correlation",
        "summary": (
            "This chart tracks whether holdings have recently been moving more together "
            "or more independently. A rising line can mean diversification is weakening."
        ),
        "technical": (
            "For each rolling window, the app calculates the pairwise return correlation "
            "matrix and averages only the off-diagonal entries. Self-correlations are "
            "excluded because they are always 1.0."
        ),
        "recommendations": [
            "Watch for rising correlation during selloffs; diversification can disappear when needed most.",
            "Pair this with allocation weights to find hidden concentration.",
            "Consider adding exposures with different return drivers if correlation remains high.",
        ],
    },
    "risk_contribution": {
        "title": "Volatility contribution",
        "summary": (
            "This chart decomposes portfolio volatility by holding. It helps identify "
            "which names are driving risk after accounting for position weight and "
            "historical co-movement."
        ),
        "technical": (
            "The calculation uses the asset return covariance matrix and current weights. "
            "Each component is weight multiplied by marginal contribution to portfolio "
            "variance, scaled back to volatility units."
        ),
        "recommendations": [
            "Compare contribution share against portfolio weight to find hidden risk concentration.",
            "Reduce or hedge names whose risk contribution is much larger than intended.",
            "Use this alongside correlation because high co-movement can amplify contribution.",
        ],
    },
    "worst_day_contribution": {
        "title": "Worst-day contribution",
        "summary": (
            "This chart breaks the portfolio's worst historical return day into ticker-level "
            "weighted contributions. It shows which holdings caused the most damage on that date."
        ),
        "technical": (
            "For the worst portfolio return date, each ticker contribution equals its daily "
            "return multiplied by its portfolio weight. The sum equals the portfolio return "
            "for that day."
        ),
        "recommendations": [
            "Inspect whether the worst day came from one name or broad portfolio beta.",
            "If one holding dominates, stress it separately before increasing size.",
            "If many holdings lose together, correlation risk may matter more than weight alone.",
        ],
    },
    "correlation": {
        "title": "Return correlation heatmap",
        "summary": (
            "This heatmap shows how closely holdings move together. Strong positive "
            "correlations mean the portfolio may be less diversified than it appears."
        ),
        "technical": (
            "Values range from -1 to +1. A value near +1 means two assets historically "
            "moved in the same direction. Near 0 means weak linear relationship. Near -1 "
            "means they tended to move opposite each other."
        ),
        "recommendations": [
            "Diversify across return drivers, not just ticker count.",
            "High correlations during stress periods can reduce the benefit of diversification.",
            "Use correlation with allocation weights to identify hidden concentration.",
        ],
    },
    "hedge_path": {
        "title": "Spot path and hedge Delta",
        "summary": (
            "This chart compares the simulated underlying price path with the hedge "
            "Delta used to offset a short option position."
        ),
        "technical": (
            "Delta is the local sensitivity of option value to the underlying. For a "
            "short option, holding Delta shares is the standard Black-Scholes hedge. "
            "Delta changes as spot, time, and volatility change."
        ),
        "recommendations": [
            "Large Delta swings usually mean Gamma risk is important.",
            "More frequent hedging can reduce model error but increases transaction costs.",
            "Compare realized volatility with pricing volatility to understand hedge error.",
        ],
    },
    "hedge_pnl": {
        "title": "Hedging error",
        "summary": (
            "This chart tracks the value of the dynamically hedged short option and the "
            "costs accumulated from rebalancing."
        ),
        "technical": (
            "In continuous-time Black-Scholes with correct assumptions, delta hedging can "
            "replicate the option. In discrete time, hedging error remains because the "
            "hedge is only updated periodically and transaction costs reduce P&L."
        ),
        "recommendations": [
            "Do not judge a hedge by final P&L alone; inspect the path.",
            "Increase rebalancing frequency only if the transaction cost tradeoff is acceptable.",
            "Use this simulator to test what happens when realized volatility differs from priced volatility.",
        ],
    },
    "price_surface": {
        "title": "Black-Scholes price heatmap",
        "summary": (
            "The heatmap shows how option price changes across strike and volatility. "
            "Darker or stronger cells represent higher model prices."
        ),
        "technical": (
            "Each cell is a Black-Scholes price for a specific strike-volatility pair, "
            "holding maturity, rate, dividend yield, and spot fixed. Calls usually get "
            "cheaper as strike rises and more expensive as volatility rises."
        ),
        "recommendations": [
            "Use this to build intuition before reading an option chain.",
            "Watch where price changes fastest; that is often near the money.",
            "Pair this with Greeks to understand local sensitivity.",
        ],
    },
    "iv_smile": {
        "title": "Implied volatility smile",
        "summary": (
            "This chart shows synthetic implied volatility across strikes. A smile or "
            "skew means the market is not using one constant volatility for all options."
        ),
        "technical": (
            "Implied volatility is the volatility input that makes Black-Scholes match a "
            "given market price. It is not a direct forecast; it can include risk premia, "
            "event risk, liquidity, and demand/supply pressure."
        ),
        "recommendations": [
            "Study implied volatility by strike and expiry, not just one option.",
            "Do not compare option prices without adjusting for moneyness and maturity.",
            "A steep skew often deserves a separate risk explanation.",
        ],
    },
    "barrier": {
        "title": "Barrier option discount",
        "summary": (
            "This chart compares a vanilla option with a knock-out barrier option. The "
            "barrier option is usually cheaper because some paths become worthless."
        ),
        "technical": (
            "A barrier option depends on the path, not just the terminal price. Monte "
            "Carlo simulates the path and checks whether the barrier was touched before "
            "expiry."
        ),
        "recommendations": [
            "Inspect whether the barrier is close to spot; close barriers can dominate value.",
            "Use more simulation paths for cleaner estimates.",
            "Remember that discrete monitoring can differ from continuous monitoring.",
        ],
    },
    "stress_test": {
        "title": "Portfolio stress test",
        "summary": (
            "This chart estimates how much each holding would add or lose under the "
            "price shocks entered in the stress table."
        ),
        "technical": (
            "The stress test applies a simple percentage shock to each holding's current "
            "market value. Holding stress P&L equals market value times shock. Portfolio "
            "impact equals stress P&L divided by total current market value."
        ),
        "recommendations": [
            "Use it to understand position sizing before losses happen.",
            "Stress the largest holding and the most correlated holdings together.",
            "Treat this as a first-order scenario; real stress periods can also change liquidity and correlations.",
        ],
    },
}


NUMBER_GUIDES = {
    "model_comparison": (
        "The bar height is the option price produced by each model. A higher bar means "
        "the model assigns more value to the same payoff. When two prices are close, "
        "the simpler model may be enough for intuition; when they diverge, investigate "
        "exercise assumptions, volatility assumptions, and Monte Carlo error."
    ),
    "allocation": (
        "The x-axis is portfolio weight. A value of 0.30, or 30%, means that holding "
        "represents 30% of current portfolio market value. Bigger weights usually have "
        "more influence on portfolio return and drawdown."
    ),
    "portfolio_growth": (
        "The y-axis starts around 1.00. A value of 1.20 means the portfolio grew 20% "
        "from the starting point; 0.85 means it lost 15%. The shape of the line matters "
        "because two portfolios can finish at the same value with very different risk paths."
    ),
    "portfolio_drawdown": (
        "Drawdown values are percentages below the previous peak. A value of -0.12 means "
        "the portfolio is 12% below its prior high at that point in time. Values closer "
        "to zero mean the portfolio is near a high-water mark."
    ),
    "rolling_volatility": (
        "The y-axis is annualized realized volatility. A value of 0.30, or 30%, means "
        "the recent rolling window had daily return swings equivalent to roughly 30% "
        "annualized volatility."
    ),
    "rolling_correlation": (
        "The y-axis is the average off-diagonal pairwise correlation. A value of 0.70 "
        "means holdings tended to move strongly together in that rolling window; a value "
        "near 0 means weaker shared movement."
    ),
    "risk_contribution": (
        "The x-axis is each holding's share of portfolio volatility contribution. A value "
        "of 0.40 means that ticker explains roughly 40% of the portfolio volatility under "
        "the selected historical window and current weights."
    ),
    "worst_day_contribution": (
        "The x-axis is weighted return contribution on the portfolio's worst return day. "
        "Negative values pulled the portfolio down; positive values offset some of that "
        "loss. The bars sum to the portfolio return for that date."
    ),
    "correlation": (
        "Each cell ranges from -1 to +1. Near +1 means two assets historically moved "
        "together, near 0 means weak linear relationship, and below 0 means they often "
        "moved in opposite directions. High positive cells deserve attention when those "
        "tickers also have large portfolio weights."
    ),
    "hedge_path": (
        "Spot is the simulated underlying price. Delta is the hedge ratio. A Delta of "
        "0.60 means the hedge holds about 0.60 shares for each short option exposure in "
        "this simplified setup. Fast Delta changes imply more rebalancing pressure."
    ),
    "hedge_pnl": (
        "The P&L line tracks the hedged short option value over time. Transaction costs "
        "show the cumulative drag from rebalancing. A final P&L near zero is closer to "
        "the ideal Black-Scholes replication story; large deviations highlight model, "
        "discrete hedging, or realized-volatility risk."
    ),
    "price_surface": (
        "Each heatmap cell is a Black-Scholes price for one strike and one volatility. "
        "Higher volatility normally raises option value because the payoff benefits from "
        "larger potential moves. For calls, higher strikes usually reduce value; for puts, "
        "higher strikes usually increase value."
    ),
    "iv_smile": (
        "The y-axis is implied volatility. A value of 0.25 means the option price implies "
        "25% annualized volatility under Black-Scholes. Differences across strikes show "
        "skew or smile, which is evidence that a single constant-volatility input is too simple."
    ),
    "barrier": (
        "The bars are model prices. The knock-out option is usually lower because it can "
        "expire worthless if the barrier is touched before expiry. The gap between bars "
        "is the value lost because of that path-dependent barrier condition."
    ),
    "stress_test": (
        "The bar length is stressed P&L. A negative value means that holding loses value "
        "under the entered shock; a positive value means it gains value. The total stress "
        "return is the sum of stressed P&L divided by current portfolio market value."
    ),
}


def apply_plotly_theme(fig: go.Figure, title: str, height: int = 430) -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left"},
        title_font={"color": PALETTE["charcoal"], "size": 17},
        height=height,
        paper_bgcolor=PALETTE["surface"],
        plot_bgcolor=PALETTE["surface"],
        font={
            "family": 'Inter, "Source Sans 3", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
            "color": PALETTE["charcoal"],
            "size": 13,
        },
        colorway=CHART_COLORS,
        margin={"l": 58, "r": 34, "t": 68, "b": 54},
        hoverlabel={
            "bgcolor": PALETTE["surface_warm"],
            "bordercolor": PALETTE["border"],
            "font_color": PALETTE["charcoal"],
        },
        legend={
            "font": {"color": PALETTE["secondary"], "size": 12},
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        clickmode="event+select",
        dragmode="select",
    )
    fig.update_xaxes(
        gridcolor=PALETTE["border_soft"],
        linecolor=PALETTE["border"],
        zerolinecolor=PALETTE["border"],
        tickfont={"color": PALETTE["secondary"]},
        title_font={"color": PALETTE["secondary"]},
    )
    fig.update_yaxes(
        gridcolor=PALETTE["border_soft"],
        linecolor=PALETTE["border"],
        zerolinecolor=PALETTE["border"],
        tickfont={"color": PALETTE["secondary"]},
        title_font={"color": PALETTE["secondary"]},
    )
    return fig


def render_explainable_chart(
    fig: go.Figure,
    chart_key: str,
    title: str,
    height: int = 430,
) -> None:
    render_chart_guide(chart_key)
    themed = apply_plotly_theme(fig, title, height=height)
    event = st.plotly_chart(
        themed,
        key=f"{chart_key}_chart",
        width="stretch",
        on_select="rerun",
        selection_mode="points",
        config={
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d"],
        },
    )
    st.markdown(
        '<div class="chart-click-note">Click a mark or cell for a selected-value explanation.</div>',
        unsafe_allow_html=True,
    )
    selected_points = extract_selected_points(event)
    if selected_points:
        chart_explanation_dialog(chart_key, selected_points[0])


def extract_selected_points(event: object) -> list[dict[str, object]]:
    selection = None
    if isinstance(event, dict):
        selection = event.get("selection")
    else:
        selection = getattr(event, "selection", None)

    if selection is None:
        return []
    if isinstance(selection, dict):
        points = selection.get("points", [])
    else:
        points = getattr(selection, "points", [])
    return [dict(point) for point in points] if points else []


@st.dialog("Chart interpretation")
def chart_explanation_dialog(chart_key: str, selected_point: dict[str, object]) -> None:
    guide = CHART_GUIDES[chart_key]
    st.markdown(f"### {guide['title']}")
    st.markdown(guide["summary"])

    selected = format_selected_point(chart_key, selected_point)
    if selected:
        st.markdown("**Selected value**")
        st.markdown(selected)

    selected_interpretation = interpret_selected_point(chart_key, selected_point)
    if selected_interpretation:
        st.markdown("**What this clicked value means**")
        st.markdown(selected_interpretation)

    more_key = f"{chart_key}_show_more"
    if st.button("More in depth information", key=f"{chart_key}_more_button"):
        st.session_state[more_key] = True

    if st.session_state.get(more_key, False):
        st.markdown("**Technical interpretation**")
        st.markdown(guide["technical"])
        st.markdown("**How to read the numbers**")
        st.markdown(NUMBER_GUIDES[chart_key])
        st.markdown("**Recommendations**")
        for recommendation in guide["recommendations"]:
            st.markdown(f"- {recommendation}")


def format_selected_point(chart_key: str, point: dict[str, object]) -> str:
    parts = []
    for label, key in [("x", "x"), ("y", "y"), ("series", "legendgroup")]:
        value = point.get(key)
        if value is not None:
            parts.append(f"`{label}`: {format_point_value(value)}")
    value = point.get("z")
    if value is None and chart_key in {"correlation", "price_surface"}:
        value = point.get("customdata")
    if value is not None and not is_sequence_value(value):
        parts.append(f"`value`: {format_point_value(value)}")
    return "  \n".join(parts)


def interpret_selected_point(chart_key: str, point: dict[str, object]) -> str:
    x_value = point.get("x")
    y_value = point.get("y")
    z_value = get_point_value(point, "z", "customdata")
    x_number = to_float(x_value)
    y_number = to_float(y_value)
    z_number = to_float(z_value)
    curve_number = int(to_float(get_point_value(point, "curve_number", "curveNumber")) or 0)

    if chart_key == "correlation":
        correlation = z_number
        if correlation is None:
            return ""
        left = str(y_value)
        right = str(x_value)
        relationship = correlation_relationship(correlation)
        if left == right:
            return (
                f"`{left} / {right}` has correlation `{correlation:.3f}` because this is "
                "the asset compared with itself. The diagonal of a correlation heatmap "
                "will always be 1.000 by definition, so it is a reference point rather "
                "than a diversification signal."
            )
        return (
            f"`{left} / {right}` has correlation `{correlation:.3f}`, which means "
            f"{relationship} based on the historical return window. A value near `+1.000` "
            "means the two tickers moved almost perfectly together, near `0.000` means "
            "weak linear co-movement, and near `-1.000` means they tended to move in "
            "opposite directions."
        )

    if chart_key == "allocation" and x_number is not None:
        concentration = "small"
        if x_number >= 0.30:
            concentration = "high"
        elif x_number >= 0.15:
            concentration = "meaningful"
        return (
            f"`{y_value}` has a portfolio weight of `{format_percentage(x_number)}`. "
            f"That is a {concentration} allocation, so this holding will have a "
            "noticeable effect on portfolio returns and drawdowns."
        )

    if chart_key == "portfolio_growth" and y_number is not None:
        total_return = y_number - 1.0
        direction = "gain" if total_return >= 0 else "loss"
        return (
            f"On `{x_value}`, one starting dollar became `{y_number:.4f}`. That is a "
            f"`{format_percentage(abs(total_return))}` {direction} from the beginning "
            "of the selected history window."
        )

    if chart_key == "portfolio_drawdown" and y_number is not None:
        if y_number >= -0.01:
            severity = "near its previous high"
        elif y_number <= -0.20:
            severity = "in a deep drawdown"
        else:
            severity = "below its previous high"
        return (
            f"On `{x_value}`, the drawdown was `{format_percentage(y_number)}`. This "
            f"means the portfolio was {severity}; for example, `-10%` means the portfolio "
            "is 10% below its prior peak."
        )

    if chart_key == "rolling_volatility" and y_number is not None:
        risk_state = "elevated" if y_number >= 0.30 else "moderate" if y_number >= 0.15 else "calm"
        return (
            f"At `{x_value}`, rolling annualized volatility was `{format_percentage(y_number)}`. "
            f"That suggests a {risk_state} realized-risk period for this portfolio, based on "
            "the selected rolling window."
        )

    if chart_key == "rolling_correlation" and y_number is not None:
        relationship = correlation_relationship(y_number)
        return (
            f"At `{x_value}`, average rolling correlation was `{y_number:.3f}`, meaning "
            f"{relationship} across the portfolio's holdings in that window. Higher values "
            "usually mean less diversification."
        )

    if chart_key == "model_comparison" and y_number is not None:
        return (
            f"The `{x_value}` model priced the option at `{y_number:.4f}`. A higher "
            "model price means the model assigns more value to the same payoff under "
            "its assumptions, not that the option is automatically cheap or expensive."
        )

    if chart_key == "price_surface":
        price = z_number
        if price is None:
            return ""
        return (
            f"At strike `{x_value}` and volatility `{y_value}`, Black-Scholes gives a "
            f"model price of `{price:.4f}`. This is the theoretical premium for that "
            "specific strike-volatility combination while the other inputs stay fixed."
        )

    if chart_key == "iv_smile" and y_number is not None:
        return (
            f"At strike `{format_point_value(x_value)}`, the implied volatility is "
            f"`{format_percentage(y_number)}`. That means Black-Scholes needs about "
            f"{format_percentage(y_number)} annualized volatility to match that option "
            "price at this strike."
        )

    if chart_key == "barrier" and y_number is not None:
        if str(x_value).lower().startswith("knock"):
            return (
                f"The knock-out option is priced at `{y_number:.4f}`. It is usually "
                "cheaper than the vanilla option because touching the barrier can cancel "
                "the payoff before expiry."
            )
        return (
            f"The vanilla option is priced at `{y_number:.4f}`. This is the comparable "
            "option without the barrier condition, so it keeps value across more price paths."
        )

    if chart_key == "stress_test" and x_number is not None:
        result = "loss" if x_number < 0 else "gain"
        return (
            f"`{y_value}` contributes a stressed `{result}` of `{x_number:,.2f}` under "
            "the entered scenario. This is calculated from current market value multiplied "
            "by the ticker's price shock."
        )

    if chart_key == "hedge_path" and y_number is not None:
        if curve_number == 1:
            return (
                f"At time `{format_point_value(x_value)}`, hedge Delta is `{y_number:.4f}`. "
                "A Delta of `0.60` means the hedge holds about 0.60 shares per short option "
                "in this simplified simulator. Values closer to 1 behave more like the stock."
            )
        return (
            f"At time `{format_point_value(x_value)}`, simulated spot is `{y_number:.4f}`. "
            "This is the underlying price path that forces the Delta hedge to rebalance."
        )

    if chart_key == "hedge_pnl" and y_number is not None:
        if curve_number == 1:
            return (
                f"At time `{format_point_value(x_value)}`, cumulative transaction costs are "
                f"`{y_number:.4f}`. Higher costs mean rebalancing is eating more of the "
                "hedge result."
            )
        result = "positive" if y_number >= 0 else "negative"
        return (
            f"At time `{format_point_value(x_value)}`, hedged P&L is `{y_number:.4f}`, "
            f"which is {result}. Large moves away from zero show the effect of discrete "
            "hedging, transaction costs, and realized volatility differing from assumptions."
        )

    return ""


def correlation_relationship(correlation: float) -> str:
    if correlation >= 0.95:
        return "the two assets moved almost one-for-one in the same direction"
    if correlation >= 0.75:
        return "the two assets had a strong positive relationship"
    if correlation >= 0.35:
        return "the two assets had a moderate positive relationship"
    if correlation > -0.35:
        return "the two assets had a weak linear relationship"
    if correlation > -0.75:
        return "the two assets had a moderate negative relationship"
    return "the two assets had a strong negative relationship"


def get_point_value(point: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        value = point.get(key)
        if value is not None:
            return value
    return None


def is_sequence_value(value: object) -> bool:
    return isinstance(value, (list, tuple, np.ndarray))


def to_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        is_percentage = cleaned.endswith("%")
        if is_percentage:
            cleaned = cleaned[:-1]
        try:
            number = float(cleaned)
        except ValueError:
            return None
        return number / 100.0 if is_percentage else number
    return None


def format_percentage(value: float) -> str:
    return f"{value:.2%}"


def format_heatmap_text(values: np.ndarray, decimals: int = 2) -> np.ndarray:
    return np.array([[f"{value:.{decimals}f}" for value in row] for row in values])


def format_point_value(value: object) -> str:
    if isinstance(value, float):
        return f"{value:,.4f}"
    return str(value)


def render_model_snapshot_table(snapshot: pd.DataFrame) -> None:
    display = snapshot.copy()
    display["standard_error_display"] = display["standard_error"].map(
        lambda value: "n/a" if pd.isna(value) else f"{value:.4f}"
    )
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_order=["model", "price", "standard_error_display"],
        column_config={
            "model": st.column_config.TextColumn("Model", width="medium"),
            "price": st.column_config.NumberColumn("Price", format="%.4f"),
            "standard_error_display": st.column_config.TextColumn("MC std. error", width="small"),
        },
    )


def render_positions_table(positions: pd.DataFrame) -> None:
    display = positions.copy()
    display["weight_pct"] = display["weight"] * 100.0
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_order=["ticker", "quantity", "weight_pct", "cost_basis"],
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "quantity": st.column_config.NumberColumn("Quantity", format="%.4f"),
            "weight_pct": st.column_config.NumberColumn("Input weight", format="%.2f%%"),
            "cost_basis": st.column_config.NumberColumn("Cost basis", format="%.4f"),
        },
    )


def render_holdings_table(holdings: pd.DataFrame) -> None:
    display = holdings[
        ["ticker", "quantity", "last_price", "market_value", "weight", "cost_basis"]
    ].copy()
    display["weight_pct"] = display["weight"] * 100.0
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_order=[
            "ticker",
            "quantity",
            "last_price",
            "market_value",
            "weight_pct",
            "cost_basis",
        ],
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "quantity": st.column_config.NumberColumn("Quantity", format="%.4f"),
            "last_price": st.column_config.NumberColumn("Last price", format="%.2f"),
            "market_value": st.column_config.NumberColumn("Market value", format="%.2f"),
            "weight_pct": st.column_config.ProgressColumn(
                "Weight",
                format="%.2f%%",
                min_value=0.0,
                max_value=100.0,
            ),
            "cost_basis": st.column_config.NumberColumn("Cost basis", format="%.4f"),
        },
    )


def render_stress_table(stress: pd.DataFrame) -> None:
    display = stress.copy()
    display["weight_pct"] = display["weight"] * 100.0
    display["shock_pct"] = display["shock"] * 100.0
    display["impact_pct"] = display["portfolio_impact"] * 100.0
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_order=[
            "ticker",
            "weight_pct",
            "market_value",
            "shock_pct",
            "stressed_market_value",
            "stress_pnl",
            "impact_pct",
        ],
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "weight_pct": st.column_config.ProgressColumn(
                "Weight",
                format="%.2f%%",
                min_value=0.0,
                max_value=100.0,
            ),
            "market_value": st.column_config.NumberColumn("Market value", format="%.2f"),
            "shock_pct": st.column_config.NumberColumn("Shock", format="%.1f%%"),
            "stressed_market_value": st.column_config.NumberColumn("Stressed value", format="%.2f"),
            "stress_pnl": st.column_config.NumberColumn("Stress P&L", format="%.2f"),
            "impact_pct": st.column_config.NumberColumn("Portfolio impact", format="%.2f%%"),
        },
    )


def render_hedge_path_table(hedge_path: pd.DataFrame, columns: list[str]) -> None:
    display = hedge_path[columns].copy()
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=360,
        column_config={
            "step": st.column_config.NumberColumn("Step", format="%d"),
            "time": st.column_config.NumberColumn("Time", format="%.4f"),
            "spot": st.column_config.NumberColumn("Spot", format="%.4f"),
            "delta": st.column_config.NumberColumn("Delta", format="%.4f"),
            "stock_position": st.column_config.NumberColumn("Stock position", format="%.4f"),
            "cash": st.column_config.NumberColumn("Cash", format="%.4f"),
            "option_value": st.column_config.NumberColumn("Option value", format="%.4f"),
            "portfolio_value": st.column_config.NumberColumn("Hedged P&L", format="%.4f"),
            "cumulative_transaction_costs": st.column_config.NumberColumn(
                "Cum. costs",
                format="%.4f",
            ),
        },
    )


def render_surface_table(surface: pd.DataFrame) -> None:
    display = surface.copy()
    display.index = [f"{value:.0%}" for value in display.index]
    display.columns = [f"K {value:.0f}" for value in display.columns]
    display = display.rename_axis("Volatility").reset_index()
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        height=360,
        column_config={
            column: st.column_config.NumberColumn(column, format="%.4f")
            for column in display.columns
            if column != "Volatility"
        }
        | {"Volatility": st.column_config.TextColumn("Volatility", width="small")},
    )


def render_smile_table(smile_prices: pd.DataFrame) -> None:
    display = smile_prices.copy()
    display["moneyness_pct"] = display["moneyness"] * 100.0
    display["implied_volatility_pct"] = display["implied_volatility"] * 100.0
    display["recovered_implied_volatility_pct"] = (
        display["recovered_implied_volatility"] * 100.0
    )
    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_order=[
            "strike",
            "moneyness_pct",
            "market_price",
            "implied_volatility_pct",
            "recovered_implied_volatility_pct",
        ],
        column_config={
            "strike": st.column_config.NumberColumn("Strike", format="%.2f"),
            "moneyness_pct": st.column_config.NumberColumn("Moneyness", format="%.2f%%"),
            "market_price": st.column_config.NumberColumn("Market price", format="%.4f"),
            "implied_volatility_pct": st.column_config.NumberColumn("Input IV", format="%.2f%%"),
            "recovered_implied_volatility_pct": st.column_config.NumberColumn(
                "Recovered IV",
                format="%.2f%%",
            ),
        },
    )


def build_stress_editor_frame(holdings: pd.DataFrame, scenario: str) -> pd.DataFrame:
    frame = holdings[["ticker", "weight"]].copy()
    frame["weight_pct"] = frame["weight"] * 100.0
    frame["shock_pct"] = 0.0

    if scenario == "Market selloff (-5% all)":
        frame["shock_pct"] = -5.0
    elif scenario == "Relief rally (+5% all)":
        frame["shock_pct"] = 5.0
    elif scenario == "Largest holding shock (-10%)" and not frame.empty:
        largest_index = frame["weight"].idxmax()
        frame.loc[largest_index, "shock_pct"] = -10.0
    elif scenario == "Concentration stress (-10% top two)":
        top_indices = frame.nlargest(min(2, len(frame)), "weight").index
        frame.loc[top_indices, "shock_pct"] = -10.0
    elif scenario == "Tech-led selloff (-8% growth)":
        growth_mask = frame["ticker"].astype(str).str.upper().isin(GROWTH_STRESS_TICKERS)
        frame.loc[growth_mask, "shock_pct"] = -8.0
    elif scenario == "Rate shock proxy":
        defensive_mask = frame["ticker"].astype(str).str.upper().isin(RATE_SHOCK_DEFENSIVE_TICKERS)
        frame["shock_pct"] = -4.0
        frame.loc[defensive_mask, "shock_pct"] = 2.0

    return frame[["ticker", "weight_pct", "shock_pct"]]


def extract_stress_shocks(stress_inputs: pd.DataFrame) -> pd.Series:
    shocks = stress_inputs.copy()
    shocks["ticker"] = shocks["ticker"].astype(str).str.upper()
    shocks["shock_pct"] = pd.to_numeric(shocks["shock_pct"], errors="coerce").fillna(0.0)
    return shocks.set_index("ticker")["shock_pct"] / 100.0


def render_model_comparison(inputs: dict[str, object]) -> None:
    base = inputs["base"]
    snapshot = model_snapshot(
        **base,
        binomial_steps=inputs["binomial_steps"],
        heston_paths=inputs["mc_paths"],
        heston_steps=inputs["mc_steps"],
        seed=inputs["seed"],
    )
    render_model_snapshot_table(snapshot)

    fig = go.Figure(
        go.Bar(
            x=snapshot["model"],
            y=snapshot["price"],
            marker_color=earth_colors(len(snapshot)),
            customdata=snapshot[["standard_error"]].fillna("").to_numpy(),
            hovertemplate="Model: %{x}<br>Price: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_yaxes(title="Price")
    render_explainable_chart(fig, "model_comparison", "Model Price Comparison")


def render_strategy_builder(inputs: dict[str, object]) -> None:
    st.subheader("Strategy Builder")
    base = inputs["base"]
    spot = float(base["spot"])
    presets = strategy_presets(spot, float(base["volatility"]))
    preset_name = st.selectbox("Strategy preset", list(presets), index=1)
    default_legs = pd.DataFrame(
        [
            {
                "kind": leg.kind,
                "side": leg.side,
                "strike": leg.strike,
                "premium": leg.premium,
                "quantity": leg.quantity,
            }
            for leg in presets[preset_name]
        ]
    )
    edited_legs = st.data_editor(
        default_legs,
        key=f"strategy_legs_{_normalize_dashboard_column(preset_name)}",
        num_rows="dynamic",
        width="stretch",
        hide_index=True,
        column_config={
            "kind": st.column_config.SelectboxColumn("Kind", options=["call", "put"], required=True),
            "side": st.column_config.SelectboxColumn("Side", options=["long", "short"], required=True),
            "strike": st.column_config.NumberColumn("Strike", min_value=0.01, format="%.2f"),
            "premium": st.column_config.NumberColumn("Premium", min_value=0.0, format="%.2f"),
            "quantity": st.column_config.NumberColumn("Qty", min_value=0.01, format="%.2f"),
        },
    )
    legs = _strategy_legs_from_frame(edited_legs)
    if not legs:
        st.info("Add at least one valid strategy leg.")
        return

    lower_bound = max(0.01, spot * 0.5)
    upper_bound = spot * 1.5
    payoff_prices = np.linspace(lower_bound, upper_bound, 151)
    summary = summarize_strategy(legs, spot=spot, price_range=payoff_prices)
    greeks = aggregate_strategy_greeks(
        legs,
        spot=spot,
        time_to_expiry=float(base["time_to_expiry"]),
        risk_free_rate=float(base["risk_free_rate"]),
        volatility=float(base["volatility"]),
        dividend_yield=float(base["dividend_yield"]),
    )
    payoff = payoff_table(legs, payoff_prices)
    st.session_state["latest_strategy_summary"] = summary

    cols = st.columns(5)
    cols[0].metric("Entry cost", _format_optional_number(summary.entry_cost))
    cols[1].metric("Max profit", _format_optional_number(summary.max_profit))
    cols[2].metric("Max loss", _format_optional_number(summary.max_loss))
    cols[3].metric("Risk", summary.risk_label)
    cols[4].metric("Breakevens", ", ".join(f"{value:.2f}" for value in summary.breakevens) or "None")

    greek_cols = st.columns(5)
    greek_cols[0].metric("Net Delta", f"{greeks['delta']:,.4f}")
    greek_cols[1].metric("Net Gamma", f"{greeks['gamma']:,.4f}")
    greek_cols[2].metric("Net Vega", f"{greeks['vega'] / 100.0:,.4f} / 1%")
    greek_cols[3].metric("Net Theta", f"{greeks['theta'] / 365.0:,.4f} / day")
    greek_cols[4].metric("Net Rho", f"{greeks['rho'] / 100.0:,.4f} / 1%")

    fig = go.Figure(
        go.Scatter(
            x=payoff["underlying_price"],
            y=payoff["total_payoff"],
            mode="lines",
            line={"color": PALETTE["sage_dark"], "width": 3},
            hovertemplate="Underlying: %{x:.2f}<br>Payoff: %{y:.2f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color=PALETTE["taupe"], line_width=1)
    fig.add_vline(x=spot, line_color=PALETTE["terracotta"], line_width=1)
    fig.update_xaxes(title="Underlying at expiry")
    fig.update_yaxes(title="Net payoff")
    apply_plotly_theme(fig, "Strategy Payoff", height=430)
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        payoff.iloc[::10].round(4),
        width="stretch",
        hide_index=True,
        height=320,
    )
    st.download_button(
        "Download strategy payoff CSV",
        data=payoff.to_csv(index=False),
        file_name="strategy_payoff.csv",
        mime="text/csv",
        key="download_strategy_payoff",
        width="stretch",
    )


def _strategy_legs_from_frame(frame: pd.DataFrame) -> list[OptionLeg]:
    legs: list[OptionLeg] = []
    for row in frame.to_dict("records"):
        kind = str(row.get("kind", "")).strip().lower()
        side = str(row.get("side", "")).strip().lower()
        strike = pd.to_numeric(row.get("strike"), errors="coerce")
        premium = pd.to_numeric(row.get("premium"), errors="coerce")
        quantity = pd.to_numeric(row.get("quantity"), errors="coerce")
        if kind not in {"call", "put"} or side not in {"long", "short"}:
            continue
        if pd.isna(strike) or pd.isna(premium) or pd.isna(quantity):
            continue
        if float(strike) <= 0 or float(premium) < 0 or float(quantity) <= 0:
            continue
        legs.append(
            OptionLeg(
                kind=kind,
                side=side,
                strike=float(strike),
                premium=float(premium),
                quantity=float(quantity),
            )
        )
    return legs


def render_scenario_matrix(inputs: dict[str, object]) -> None:
    st.subheader("Scenario Matrix")
    price, greeks = option_metrics(**inputs["base"])
    probabilities = build_probability_snapshot(inputs, price)
    spot_shocks = [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20]
    vol_shocks = [-0.15, -0.10, -0.05, 0.0, 0.05, 0.10, 0.15]
    scenario_grid = build_option_scenario_grid(inputs, spot_shocks, vol_shocks)

    metric_cols = st.columns(5)
    metric_cols[0].metric("Base price", f"{price:,.4f}")
    metric_cols[1].metric("Expected move", f"{probabilities['expected_move']:,.2f}")
    metric_cols[2].metric("One-sigma band", f"{probabilities['lower_one_sigma']:,.2f} - {probabilities['upper_one_sigma']:,.2f}")
    metric_cols[3].metric("Prob. ITM", f"{probabilities['probability_itm']:.2%}")
    metric_cols[4].metric("Prob. profit", f"{probabilities['probability_profit']:.2%}")

    price_matrix = scenario_grid.pivot(index="vol_shock", columns="spot_shock", values="price")
    delta_matrix = scenario_grid.pivot(index="vol_shock", columns="spot_shock", values="delta")
    left, right = st.columns(2)
    with left:
        fig = go.Figure(
            go.Heatmap(
                z=price_matrix.values,
                x=[f"{value:+.0%}" for value in price_matrix.columns],
                y=[f"{value:+.0%}" for value in price_matrix.index],
                colorscale=[
                    [0.0, PALETTE["surface_warm"]],
                    [0.5, "#DBEAFE"],
                    [1.0, PALETTE["sage_dark"]],
                ],
                colorbar={"title": "Price"},
                text=format_heatmap_text(price_matrix.values, decimals=2),
                texttemplate="%{text}",
                textfont={"color": PALETTE["charcoal"], "size": 11},
                hovertemplate="Spot shock: %{x}<br>Vol shock: %{y}<br>Price: %{z:.4f}<extra></extra>",
            )
        )
        fig.update_xaxes(title="Spot shock")
        fig.update_yaxes(title="Vol shock")
        apply_plotly_theme(fig, "Option Price Shock Matrix", height=430)
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    with right:
        fig = go.Figure(
            go.Heatmap(
                z=delta_matrix.values,
                x=[f"{value:+.0%}" for value in delta_matrix.columns],
                y=[f"{value:+.0%}" for value in delta_matrix.index],
                zmin=-1,
                zmax=1,
                zmid=0,
                colorscale=[
                    [0.0, PALETTE["terracotta_dark"]],
                    [0.5, PALETTE["surface_warm"]],
                    [1.0, PALETTE["sage"]],
                ],
                colorbar={"title": "Delta"},
                text=format_heatmap_text(delta_matrix.values, decimals=2),
                texttemplate="%{text}",
                textfont={"color": PALETTE["charcoal"], "size": 11},
                hovertemplate="Spot shock: %{x}<br>Vol shock: %{y}<br>Delta: %{z:.4f}<extra></extra>",
            )
        )
        fig.update_xaxes(title="Spot shock")
        fig.update_yaxes(title="Vol shock")
        apply_plotly_theme(fig, "Delta Shock Matrix", height=430)
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})

    display = scenario_grid.copy()
    display["spot_shock_pct"] = display["spot_shock"] * 100.0
    display["vol_shock_pct"] = display["vol_shock"] * 100.0
    display["volatility_pct"] = display["volatility"] * 100.0
    st.dataframe(
        display[
            [
                "spot_shock_pct",
                "vol_shock_pct",
                "spot",
                "volatility_pct",
                "price",
                "delta",
                "gamma",
                "vega_per_1pct",
            ]
        ],
        width="stretch",
        hide_index=True,
        height=360,
        column_config={
            "spot_shock_pct": st.column_config.NumberColumn("Spot shock", format="%.0f%%"),
            "vol_shock_pct": st.column_config.NumberColumn("Vol shock", format="%.0f pts"),
            "spot": st.column_config.NumberColumn("Spot", format="%.2f"),
            "volatility_pct": st.column_config.NumberColumn("Volatility", format="%.2f%%"),
            "price": st.column_config.NumberColumn("Price", format="%.4f"),
            "delta": st.column_config.NumberColumn("Delta", format="%.4f"),
            "gamma": st.column_config.NumberColumn("Gamma", format="%.6f"),
            "vega_per_1pct": st.column_config.NumberColumn("Vega / 1%", format="%.4f"),
        },
    )
    st.download_button(
        "Download scenario matrix CSV",
        data=scenario_grid.to_csv(index=False),
        file_name="option_scenario_matrix.csv",
        mime="text/csv",
        key="download_option_scenario_matrix",
        width="stretch",
    )


def render_portfolio_lab(inputs: dict[str, object]) -> None:
    st.subheader("Portfolio Lab")

    portfolio_errors: list[str] = []
    left, right = st.columns([1.15, 0.85])
    with left:
        with st.container(border=True):
            st.markdown("#### Positions")
            source = st.segmented_control(
                "Portfolio source",
                ["Manual entry", "CSV upload"],
                default="Manual entry",
            )

            if source == "Manual entry":
                default_portfolio = pd.DataFrame(
                    {
                        "ticker": ["AAPL", "MSFT", "NVDA"],
                        "quantity": [5.0, 3.0, 2.0],
                    }
                )
                raw_positions = st.data_editor(
                    default_portfolio,
                    num_rows="dynamic",
                    width="stretch",
                    hide_index=True,
                    height=210,
                    column_config={
                        "ticker": st.column_config.TextColumn("Ticker", width="medium"),
                        "quantity": st.column_config.NumberColumn(
                            "Quantity",
                            min_value=0.0,
                            width="small",
                        ),
                    },
                )
            else:
                st.caption("CSV columns: ticker plus quantity or weight. Aliases like Symbol, Shares, Qty, and Target Weight are accepted.")
                uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
                if uploaded_file is None:
                    raw_positions = pd.DataFrame(columns=["ticker", "quantity"])
                else:
                    raw_positions = pd.read_csv(uploaded_file)
                    portfolio_errors = validate_portfolio_frame(raw_positions)
                st.code("ticker,quantity\nAAPL,5\nMSFT,3\nD05.SI,100", language="csv")

    with right:
        with st.container(border=True):
            st.markdown("#### History and assumptions")
            today = date.today()
            start_date = st.date_input("History start", today - timedelta(days=365 * 2))
            end_date = st.date_input("History end", today)
            risk_free_pct = st.number_input(
                "Sharpe risk-free rate",
                min_value=-5.0,
                max_value=15.0,
                value=float(inputs["base"]["risk_free_rate"] * 100.0),
                step=0.25,
            )

    if portfolio_errors:
        for message in portfolio_errors:
            st.info(message)
        return

    try:
        positions = normalize_portfolio(raw_positions)
    except ValueError as exc:
        st.info(str(exc))
        return

    if end_date <= start_date:
        st.warning("History end must be after history start.")
        return

    st.caption("Portfolio analytics update automatically. Yahoo Finance prices are cached for one hour.")
    st.caption(f"Accepted {len(positions)} normalized tickers: {', '.join(positions['ticker'].tolist())}.")
    render_positions_table(positions)
    st.download_button(
        "Download normalized positions CSV",
        data=positions.to_csv(index=False),
        file_name="normalized_positions.csv",
        mime="text/csv",
        key="download_normalized_positions",
        width="stretch",
    )

    tickers = tuple(positions["ticker"].tolist())
    try:
        with st.spinner("Fetching Yahoo Finance prices..."):
            close_prices = cached_adjusted_close(
                tickers,
                str(start_date),
                str(end_date + timedelta(days=1)),
            )
        report = build_portfolio_report(
            positions,
            close_prices,
            risk_free_rate=risk_free_pct / 100.0,
        )
    except Exception as exc:
        st.error(f"Could not build portfolio report: {exc}")
        return

    holdings = report.holdings.copy()
    total_market_value = holdings["market_value"].sum()
    metric_cols = st.columns(5)
    metric_cols[0].metric("Market value", f"{total_market_value:,.2f}")
    metric_cols[1].metric("Holdings", f"{len(holdings)}")
    metric_cols[2].metric("Annual return", f"{report.summary['annual_return']:.2%}")
    metric_cols[3].metric("Volatility", f"{report.summary['annual_volatility']:.2%}")
    metric_cols[4].metric("Max drawdown", f"{report.summary['max_drawdown']:.2%}")

    render_holdings_table(holdings)
    st.download_button(
        "Download holdings CSV",
        data=holdings.to_csv(index=False),
        file_name="portfolio_holdings.csv",
        mime="text/csv",
        key="download_portfolio_holdings",
        width="stretch",
    )
    render_portfolio_attribution(report)

    chart_left, chart_right = st.columns([0.95, 1.05])
    with chart_left:
        allocation = holdings.sort_values("weight", ascending=True)
        fig = go.Figure(
            go.Bar(
                x=allocation["weight"],
                y=allocation["ticker"],
                orientation="h",
                marker_color=PALETTE["slate"],
                hovertemplate="Ticker: %{y}<br>Weight: %{x:.2%}<extra></extra>",
            )
        )
        fig.update_xaxes(title="Weight", tickformat=".0%")
        render_explainable_chart(fig, "allocation", "Allocation by Market Value")

    with chart_right:
        fig = go.Figure(
            go.Scatter(
                x=report.cumulative_returns.index,
                y=report.cumulative_returns.values,
                mode="lines",
                line={"color": PALETTE["sage_dark"], "width": 3},
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Growth: %{y:.4f}<extra></extra>",
            )
        )
        fig.update_yaxes(title="Growth")
        render_explainable_chart(fig, "portfolio_growth", "Growth of One Dollar")

    risk_left, risk_right = st.columns(2)
    with risk_left:
        fig = go.Figure(
            go.Scatter(
                x=report.drawdown.index,
                y=report.drawdown.values,
                mode="lines",
                fill="tozeroy",
                line={"color": PALETTE["terracotta_dark"], "width": 2},
                fillcolor="rgba(220,38,38,0.14)",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Drawdown: %{y:.2%}<extra></extra>",
            )
        )
        fig.update_yaxes(title="Drawdown", tickformat=".0%")
        render_explainable_chart(fig, "portfolio_drawdown", "Portfolio Drawdown")

    with risk_right:
        show_cell_text = len(report.correlation.columns) <= 8
        fig = go.Figure(
            go.Heatmap(
                z=report.correlation.values,
                customdata=report.correlation.values,
                x=report.correlation.columns,
                y=report.correlation.index,
                zmin=-1,
                zmax=1,
                zmid=0,
                colorscale=[
                    [0.0, PALETTE["terracotta_dark"]],
                    [0.5, PALETTE["surface_warm"]],
                    [1.0, PALETTE["sage_dark"]],
                ],
                colorbar={
                    "title": {"text": "Correlation", "font": {"color": PALETTE["secondary"]}},
                    "outlinecolor": PALETTE["border"],
                    "tickmode": "array",
                    "tickvals": [-1, 0, 1],
                    "ticktext": ["-1", "0", "+1"],
                    "tickfont": {"color": PALETTE["secondary"], "size": 11},
                },
                text=format_heatmap_text(report.correlation.values) if show_cell_text else None,
                texttemplate="%{text}" if show_cell_text else None,
                textfont={"color": PALETTE["charcoal"], "size": 12},
                hovertemplate="%{y} / %{x}<br>Correlation: %{z:.3f}<extra></extra>",
            )
        )
        render_explainable_chart(fig, "correlation", "Return Correlation", height=480)

    render_rolling_risk_and_stress(report, holdings)


def render_portfolio_attribution(report: object) -> None:
    st.subheader("Risk Attribution")
    try:
        volatility_contribution = risk_contribution(report.asset_returns, report.weights)
        drawdown_contribution = worst_day_contribution(
            report.asset_returns,
            report.weights,
            report.returns,
        )
    except ValueError as exc:
        st.info(str(exc))
        return

    top_risk = volatility_contribution.iloc[0]
    worst_day = drawdown_contribution["date"].iloc[0]
    st.session_state["latest_portfolio_summary"] = {
        "Annual return": f"{report.summary['annual_return']:.2%}",
        "Annual volatility": f"{report.summary['annual_volatility']:.2%}",
        "Max drawdown": f"{report.summary['max_drawdown']:.2%}",
        "Top volatility contributor": (
            f"{top_risk['ticker']} ({float(top_risk['contribution_pct']):.2%})"
        ),
        "Worst day": str(pd.Timestamp(worst_day).date()),
    }

    left, right = st.columns(2)
    with left:
        fig = go.Figure(
            go.Bar(
                x=volatility_contribution["contribution_pct"],
                y=volatility_contribution["ticker"],
                orientation="h",
                marker_color=PALETTE["clay"],
                hovertemplate="Ticker: %{y}<br>Vol contribution: %{x:.2%}<extra></extra>",
            )
        )
        fig.update_xaxes(title="Contribution", tickformat=".0%")
        render_explainable_chart(fig, "risk_contribution", "Volatility Contribution", height=390)
        st.dataframe(
            volatility_contribution,
            width="stretch",
            hide_index=True,
            height=260,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "weight": st.column_config.NumberColumn("Weight", format="%.2%"),
                "annualized_volatility": st.column_config.NumberColumn("Asset vol", format="%.2%"),
                "volatility_contribution": st.column_config.NumberColumn("Vol contribution", format="%.2%"),
                "contribution_pct": st.column_config.NumberColumn("Share", format="%.2%"),
            },
        )

    with right:
        fig = go.Figure(
            go.Bar(
                x=drawdown_contribution["return_contribution"],
                y=drawdown_contribution["ticker"],
                orientation="h",
                marker_color=[
                    PALETTE["terracotta_dark"] if value < 0 else PALETTE["sage"]
                    for value in drawdown_contribution["return_contribution"]
                ],
                hovertemplate="Ticker: %{y}<br>Contribution: %{x:.2%}<extra></extra>",
            )
        )
        fig.add_vline(x=0, line_color=PALETTE["taupe"], line_width=1)
        fig.update_xaxes(title="Worst-day return contribution", tickformat=".0%")
        render_explainable_chart(fig, "worst_day_contribution", "Worst-Day Contribution", height=390)
        st.dataframe(
            drawdown_contribution,
            width="stretch",
            hide_index=True,
            height=260,
            column_config={
                "date": st.column_config.DateColumn("Date"),
                "ticker": st.column_config.TextColumn("Ticker"),
                "asset_return": st.column_config.NumberColumn("Asset return", format="%.2%"),
                "weight": st.column_config.NumberColumn("Weight", format="%.2%"),
                "return_contribution": st.column_config.NumberColumn("Contribution", format="%.2%"),
            },
        )


def render_rolling_risk_and_stress(report: object, holdings: pd.DataFrame) -> None:
    st.subheader("Rolling Risk and Stress Test")

    if len(report.returns) >= 5:
        max_window = min(126, len(report.returns))
        default_window = min(60, max_window)
        rolling_window = st.slider(
            "Rolling risk window, trading days",
            min_value=5,
            max_value=max_window,
            value=default_window,
            step=1,
        )

        rolling_left, rolling_right = st.columns(2)
        with rolling_left:
            rolling_volatility = rolling_portfolio_volatility(
                report.returns,
                window=rolling_window,
            )
            if rolling_volatility.empty:
                st.info("Not enough return history to calculate rolling volatility.")
            else:
                fig = go.Figure(
                    go.Scatter(
                        x=rolling_volatility.index,
                        y=rolling_volatility.values,
                        mode="lines",
                        line={"color": PALETTE["slate"], "width": 3},
                        hovertemplate="Date: %{x|%Y-%m-%d}<br>Volatility: %{y:.2%}<extra></extra>",
                    )
                )
                fig.update_yaxes(title="Annualized volatility", tickformat=".0%")
                render_explainable_chart(fig, "rolling_volatility", "Rolling Annualized Volatility")

        with rolling_right:
            rolling_correlation = rolling_average_correlation(
                report.asset_returns,
                window=rolling_window,
            )
            if rolling_correlation.empty:
                st.info("Need at least two holdings with enough return history for rolling correlation.")
            else:
                fig = go.Figure(
                    go.Scatter(
                        x=rolling_correlation.index,
                        y=rolling_correlation.values,
                        mode="lines",
                        line={"color": PALETTE["terracotta"], "width": 3},
                        hovertemplate="Date: %{x|%Y-%m-%d}<br>Average correlation: %{y:.3f}<extra></extra>",
                    )
                )
                fig.update_yaxes(title="Average correlation", range=[-1, 1])
                render_explainable_chart(fig, "rolling_correlation", "Rolling Average Correlation")
    else:
        st.info("Add more price history to unlock rolling volatility and rolling correlation.")

    stress_left, stress_right = st.columns([0.9, 1.1])
    with stress_left:
        scenario = st.selectbox(
            "Stress scenario",
            [
                "Custom",
                "Market selloff (-5% all)",
                "Largest holding shock (-10%)",
                "Concentration stress (-10% top two)",
                "Tech-led selloff (-8% growth)",
                "Rate shock proxy",
                "Relief rally (+5% all)",
            ],
        )
        stress_inputs = st.data_editor(
            build_stress_editor_frame(holdings, scenario),
            key=f"stress_inputs_{scenario}",
            width="stretch",
            hide_index=True,
            disabled=["ticker", "weight_pct"],
            column_config={
                "ticker": st.column_config.TextColumn("Ticker"),
                "weight_pct": st.column_config.ProgressColumn(
                    "Weight",
                    format="%.2f%%",
                    min_value=0.0,
                    max_value=100.0,
                ),
                "shock_pct": st.column_config.NumberColumn(
                    "Shock %",
                    min_value=-100.0,
                    max_value=100.0,
                    step=1.0,
                    format="%.1f",
                ),
            },
        )

    stress = stress_test_portfolio(holdings, extract_stress_shocks(stress_inputs))
    total_pnl = stress["stress_pnl"].sum()
    total_market_value = stress["market_value"].sum()
    stressed_value = stress["stressed_market_value"].sum()
    stressed_return = total_pnl / total_market_value

    with stress_right:
        metric_cols = st.columns(3)
        metric_cols[0].metric("Stress P&L", f"{total_pnl:,.2f}")
        metric_cols[1].metric("Stress return", f"{stressed_return:.2%}")
        metric_cols[2].metric("Stressed value", f"{stressed_value:,.2f}")
        st.download_button(
            "Download stress results CSV",
            data=stress.to_csv(index=False),
            file_name="stress_results.csv",
            mime="text/csv",
            key="download_stress_results",
            width="stretch",
        )

        stress_sorted = stress.sort_values("stress_pnl", ascending=True)
        fig = go.Figure(
            go.Bar(
                x=stress_sorted["stress_pnl"],
                y=stress_sorted["ticker"],
                orientation="h",
                marker_color=[
                    PALETTE["terracotta_dark"] if value < 0 else PALETTE["sage"]
                    for value in stress_sorted["stress_pnl"]
                ],
                hovertemplate=(
                    "Ticker: %{y}<br>Stress P&L: %{x:,.2f}"
                    "<br>Shock: %{customdata[0]:.1%}<br>Portfolio impact: %{customdata[1]:.2%}<extra></extra>"
                ),
                customdata=stress_sorted[["shock", "portfolio_impact"]].to_numpy(),
            )
        )
        fig.add_vline(x=0, line_color=PALETTE["taupe"], line_width=1)
        fig.update_xaxes(title="Stress P&L")
        render_explainable_chart(fig, "stress_test", "Scenario Stress Impact", height=420)

    render_stress_table(stress)


def render_report_mode(inputs: dict[str, object]) -> None:
    st.subheader("Report Mode")
    price, greeks = option_metrics(**inputs["base"])
    snapshot = build_research_snapshot(inputs, price, greeks)
    warnings = build_input_warnings(inputs)

    with st.spinner("Building model comparison for report..."):
        models = model_snapshot(
            **inputs["base"],
            binomial_steps=inputs["binomial_steps"],
            heston_paths=inputs["mc_paths"],
            heston_steps=inputs["mc_steps"],
            seed=inputs["seed"],
        )

    memo = build_research_memo(
        inputs,
        snapshot=snapshot,
        warnings=warnings,
        model_prices=models,
        strategy_summary=st.session_state.get("latest_strategy_summary"),
        portfolio_summary=st.session_state.get("latest_portfolio_summary"),
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Report price", f"{price:,.4f}")
    metric_cols[1].metric("Warnings", f"{len(warnings)}")
    metric_cols[2].metric(
        "Strategy",
        "Included" if st.session_state.get("latest_strategy_summary") is not None else "Not run",
    )
    metric_cols[3].metric(
        "Portfolio",
        "Included" if st.session_state.get("latest_portfolio_summary") is not None else "Not run",
    )

    st.download_button(
        "Download research memo",
        data=memo,
        file_name="quant_finance_lab_memo.md",
        mime="text/markdown",
        key="download_research_memo",
        width="stretch",
    )
    st.markdown(memo)


def render_delta_hedge(inputs: dict[str, object]) -> None:
    base = inputs["base"]
    hedge_path, summary = simulate_delta_hedge(
        base["kind"],
        base["spot"],
        base["strike"],
        base["time_to_expiry"],
        base["risk_free_rate"],
        base["volatility"],
        realized_volatility=inputs["realized_volatility"],
        drift=inputs["drift"],
        dividend_yield=base["dividend_yield"],
        steps=inputs["hedge_steps"],
        transaction_cost_bps=inputs["hedge_cost_bps"],
        seed=inputs["seed"],
    )

    cols = st.columns(5)
    cols[0].metric("Option premium", f"{summary.option_premium:,.4f}")
    cols[1].metric("Terminal spot", f"{summary.terminal_spot:,.4f}")
    cols[2].metric("Payoff", f"{summary.payoff:,.4f}")
    cols[3].metric("Final hedge P&L", f"{summary.final_hedge_pnl:,.4f}")
    cols[4].metric("Transaction costs", f"{summary.total_transaction_costs:,.4f}")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hedge_path["time"],
            y=hedge_path["spot"],
            mode="lines",
            name="Spot",
            line={"color": PALETTE["slate"], "width": 3},
            hovertemplate="Time: %{x:.3f}<br>Spot: %{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hedge_path["time"],
            y=hedge_path["delta"].ffill(),
            mode="lines",
            name="Delta",
            yaxis="y2",
            line={"color": PALETTE["terracotta"], "width": 2.4, "dash": "dash"},
            hovertemplate="Time: %{x:.3f}<br>Delta: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        yaxis={"title": "Spot"},
        yaxis2={
            "title": "Hedge delta",
            "overlaying": "y",
            "side": "right",
            "gridcolor": "rgba(0,0,0,0)",
        },
    )
    render_explainable_chart(fig, "hedge_path", "Simulated Spot Path and Hedge Delta")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hedge_path["time"],
            y=hedge_path["portfolio_value"],
            mode="lines",
            name="Hedged short option P&L",
            line={"color": PALETTE["sage_dark"], "width": 3},
            hovertemplate="Time: %{x:.3f}<br>P&L: %{y:.4f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=hedge_path["time"],
            y=hedge_path["cumulative_transaction_costs"],
            mode="lines",
            name="Transaction costs",
            line={"color": PALETTE["terracotta"], "width": 2.5},
            hovertemplate="Time: %{x:.3f}<br>Costs: %{y:.4f}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_color=PALETTE["taupe"], line_width=1)
    fig.update_xaxes(title="Years")
    fig.update_yaxes(title="Value")
    render_explainable_chart(fig, "hedge_pnl", "Hedging Error Through Time")

    display_columns = [
        "step",
        "time",
        "spot",
        "delta",
        "stock_position",
        "cash",
        "option_value",
        "portfolio_value",
        "cumulative_transaction_costs",
    ]
    render_hedge_path_table(hedge_path, display_columns)


def render_surface(inputs: dict[str, object]) -> None:
    base = inputs["base"]
    spot = base["spot"]
    strikes = np.linspace(max(1.0, spot * 0.65), spot * 1.35, 17)
    vols = np.linspace(0.05, 0.60, 12)
    surface = black_scholes_surface(
        base["kind"],
        spot,
        strikes,
        vols,
        base["time_to_expiry"],
        base["risk_free_rate"],
        base["dividend_yield"],
    )

    fig = go.Figure(
        go.Heatmap(
            z=surface.values,
            customdata=surface.values,
            x=[f"{value:.0f}" for value in surface.columns],
            y=[f"{value:.0%}" for value in surface.index],
            colorscale=[
                [0.0, PALETTE["surface_warm"]],
                [0.55, "#DBEAFE"],
                [1.0, PALETTE["sage_dark"]],
            ],
            colorbar={
                "title": {"text": "Price", "font": {"color": PALETTE["secondary"]}},
                "outlinecolor": PALETTE["border"],
                "tickfont": {"color": PALETTE["secondary"]},
            },
            hovertemplate="Strike: %{x}<br>Volatility: %{y}<br>Price: %{z:.4f}<extra></extra>",
        )
    )
    fig.update_xaxes(title="Strike")
    fig.update_yaxes(title="Volatility")
    render_explainable_chart(fig, "price_surface", "Black-Scholes Price Heatmap", height=470)
    render_surface_table(surface)


def render_smile(inputs: dict[str, object]) -> None:
    base = inputs["base"]
    spot = base["spot"]
    strikes = np.linspace(max(1.0, spot * 0.7), spot * 1.3, 21)
    smile = synthetic_smile(spot, strikes, base["volatility"])
    smile_prices = recover_smile_prices(
        base["kind"],
        spot,
        smile,
        base["time_to_expiry"],
        base["risk_free_rate"],
        base["dividend_yield"],
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=smile_prices["strike"],
            y=smile_prices["implied_volatility"],
            mode="lines+markers",
            name="Synthetic market IV",
            line={"color": PALETTE["sage_dark"], "width": 3},
            marker={"size": 7},
            hovertemplate="Strike: %{x:.2f}<br>IV: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=smile_prices["strike"],
            y=smile_prices["recovered_implied_volatility"],
            mode="lines",
            name="Recovered IV",
            line={"color": PALETTE["terracotta"], "width": 2.5, "dash": "dash"},
            hovertemplate="Strike: %{x:.2f}<br>Recovered IV: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_vline(x=base["strike"], line_color=PALETTE["taupe"], line_dash="dot")
    fig.update_xaxes(title="Strike")
    fig.update_yaxes(title="Implied volatility", tickformat=".0%")
    render_explainable_chart(fig, "iv_smile", "Synthetic Implied Volatility Smile")
    render_smile_table(smile_prices)


def render_path_models(inputs: dict[str, object]) -> None:
    base = inputs["base"]
    barrier = barrier_snapshot(
        base["kind"],
        inputs["barrier_kind"],
        base["spot"],
        base["strike"],
        inputs["barrier"],
        base["time_to_expiry"],
        base["risk_free_rate"],
        base["volatility"],
        base["dividend_yield"],
        paths=inputs["mc_paths"],
        steps=inputs["mc_steps"],
        seed=inputs["seed"],
    )

    cols = st.columns(4)
    cols[0].metric("Vanilla price", f"{barrier['vanilla_price']:,.4f}")
    cols[1].metric("Barrier price", f"{barrier['barrier_price']:,.4f}")
    cols[2].metric("Knock-out discount", f"{barrier['knock_out_discount']:,.4f}")
    cols[3].metric("MC standard error", f"{barrier['standard_error']:,.4f}")

    fig = go.Figure(
        go.Bar(
            x=["Vanilla", "Knock-out"],
            y=[barrier["vanilla_price"], barrier["barrier_price"]],
            marker_color=[PALETTE["slate"], PALETTE["terracotta"]],
            hovertemplate="Type: %{x}<br>Price: %{y:.4f}<extra></extra>",
        )
    )
    fig.update_yaxes(title="Price")
    render_explainable_chart(fig, "barrier", "Barrier Option Discount", height=400)


if __name__ == "__main__":
    main()
