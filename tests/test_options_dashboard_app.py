import json

import pandas as pd

from app.options_dashboard import (
    RESEARCH_CASE_PRESETS,
    build_input_warnings,
    build_research_case_export,
    build_research_snapshot,
    build_stress_editor_frame,
    get_research_case_preset,
    validate_portfolio_frame,
)


REQUIRED_INPUT_KEYS = {
    "base",
    "binomial_steps",
    "mc_paths",
    "mc_steps",
    "seed",
    "barrier_kind",
    "barrier",
    "hedge_steps",
    "realized_volatility",
    "drift",
    "hedge_cost_bps",
}


def test_research_case_presets_have_complete_defaults():
    assert set(RESEARCH_CASE_PRESETS) >= {
        "Balanced ATM Call",
        "Defensive OTM Put",
        "High-Vol Earnings Call",
        "Near-Barrier Knock-Out",
        "Short-Dated Hedge Stress",
    }

    for preset_name in RESEARCH_CASE_PRESETS:
        preset = get_research_case_preset(preset_name)
        assert REQUIRED_INPUT_KEYS.issubset(preset)
        assert {
            "kind",
            "spot",
            "strike",
            "time_to_expiry",
            "risk_free_rate",
            "volatility",
            "dividend_yield",
        }.issubset(preset["base"])


def test_research_case_preset_returns_an_independent_copy():
    preset = get_research_case_preset("Balanced ATM Call")
    preset["base"]["spot"] = 999.0

    fresh = get_research_case_preset("Balanced ATM Call")

    assert fresh["base"]["spot"] == 100.0


def test_build_research_snapshot_classifies_moneyness_and_breakeven():
    inputs = get_research_case_preset("Balanced ATM Call")
    inputs["base"]["strike"] = 95.0
    greeks = pd.Series(
        {
            "delta": 0.65,
            "gamma": 0.02,
            "vega_per_1pct": 0.10,
            "theta_per_day": -0.02,
        }
    )

    snapshot = build_research_snapshot(inputs, price=8.0, greeks=greeks)

    assert snapshot["classification"] == "ITM call"
    assert snapshot["moneyness"] == "1.0526"
    assert snapshot["breakeven"] == "103.0000"
    assert snapshot["largest_greek"] == "Delta"


def test_build_input_warnings_flags_risky_contract_setup():
    inputs = get_research_case_preset("Near-Barrier Knock-Out")
    inputs["base"]["time_to_expiry"] = 0.03
    inputs["base"]["volatility"] = 0.85
    inputs["realized_volatility"] = 0.35
    inputs["mc_paths"] = 5_000
    inputs["barrier_kind"] = "down-and-out"
    inputs["barrier"] = 99.0

    warnings = build_input_warnings(inputs)

    assert any("Expiry is very short" in warning for warning in warnings)
    assert any("Volatility is high" in warning for warning in warnings)
    assert any("Barrier is within" in warning for warning in warnings)
    assert any("Monte Carlo paths" in warning for warning in warnings)
    assert any("Realized volatility differs" in warning for warning in warnings)


def test_validate_portfolio_frame_accepts_aliases_and_rejects_missing_exposure():
    valid = pd.DataFrame({"Symbol": ["AAPL"], "Shares": [3]})
    invalid = pd.DataFrame({"Symbol": ["AAPL"], "Name": ["Apple"]})

    assert validate_portfolio_frame(valid) == []
    assert "quantity or weight" in " ".join(validate_portfolio_frame(invalid))


def test_new_stress_presets_generate_expected_shocks():
    holdings = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT", "TLT"],
            "weight": [0.50, 0.30, 0.20],
        }
    )

    tech = build_stress_editor_frame(holdings, "Tech-led selloff (-8% growth)")
    rate = build_stress_editor_frame(holdings, "Rate shock proxy")

    assert tech.set_index("ticker").loc["AAPL", "shock_pct"] == -8.0
    assert tech.set_index("ticker").loc["MSFT", "shock_pct"] == -8.0
    assert tech.set_index("ticker").loc["TLT", "shock_pct"] == 0.0
    assert rate.set_index("ticker").loc["AAPL", "shock_pct"] == -4.0
    assert rate.set_index("ticker").loc["TLT", "shock_pct"] == 2.0


def test_research_case_export_is_json_serializable():
    inputs = get_research_case_preset("Short-Dated Hedge Stress")
    export = build_research_case_export(inputs, ["Example warning"])

    payload = json.dumps(export)

    assert "Short-Dated Hedge Stress" not in payload
    assert export["warnings"] == ["Example warning"]
    assert export["base"]["kind"] == "call"
