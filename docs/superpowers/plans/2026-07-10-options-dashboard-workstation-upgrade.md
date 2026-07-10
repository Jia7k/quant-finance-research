# Options Dashboard Workstation Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build lazy page navigation, a multi-leg options strategy builder, portfolio risk attribution, and downloadable report mode for Quant Finance Lab.

**Architecture:** Add testable pure analytics helpers in `src/options_pricing_research/strategies.py`, extend portfolio attribution logic in `src/options_pricing_research/portfolio_lab.py`, and keep Streamlit-specific rendering inside `app/options_dashboard.py`. Use session state only as UI glue: current inputs, latest strategy summary, and latest portfolio summary.

**Tech Stack:** Python 3.13, Streamlit, pandas, numpy, Plotly, pytest.

## Global Constraints

- Preserve existing pricing, path, hedge, and portfolio formulas.
- Do not replace Streamlit or add external frontend assets.
- Keep source text ASCII-only.
- Use TDD for new pure behavior.
- Push only after full verification passes.

---

### Task 1: Strategy Engine

**Files:**
- Create: `src/options_pricing_research/strategies.py`
- Create: `tests/test_strategies.py`

**Interfaces:**
- Produces `OptionLeg`, `StrategySummary`, `payoff_table`, `summarize_strategy`, `strategy_presets`, and `aggregate_strategy_greeks`.

- [ ] Write failing tests for a bull call spread payoff, long straddle breakevens, unbounded short-call risk, and Greek aggregation.
- [ ] Run `.venv/bin/python -m pytest tests/test_strategies.py -q` and confirm expected failure.
- [ ] Implement the strategy module.
- [ ] Rerun focused tests and confirm pass.

### Task 2: Portfolio Attribution

**Files:**
- Modify: `src/options_pricing_research/portfolio_lab.py`
- Modify: `tests/test_portfolio_lab.py`

**Interfaces:**
- Produces `risk_contribution(asset_returns, weights, periods_per_year=252)` and `worst_day_contribution(asset_returns, weights, portfolio_returns)`.

- [ ] Write failing tests for volatility contribution percentages summing near 1.0 and worst-day contribution using weighted asset returns.
- [ ] Run `.venv/bin/python -m pytest tests/test_portfolio_lab.py -q` and confirm expected failure.
- [ ] Implement attribution helpers.
- [ ] Rerun focused tests and confirm pass.

### Task 3: Report and Navigation Helpers

**Files:**
- Modify: `app/options_dashboard.py`
- Modify: `tests/test_options_dashboard_app.py`

**Interfaces:**
- Produces `DASHBOARD_PAGES`, `get_default_inputs`, `build_research_memo`, and stable page metadata.

- [ ] Write failing tests for page labels, default inputs, and report Markdown degradation when portfolio/strategy data is missing.
- [ ] Run `.venv/bin/python -m pytest tests/test_options_dashboard_app.py -q` and confirm expected failure.
- [ ] Implement helpers without changing Streamlit rendering yet.
- [ ] Rerun focused tests and confirm pass.

### Task 4: Streamlit Integration

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes strategy, attribution, report, and navigation helpers.
- Produces lazy page selector, Strategy Builder page, portfolio attribution panels, and Report page.

- [ ] Replace `st.tabs` with a page selector that renders only the active heavy view.
- [ ] Store current inputs in `st.session_state`.
- [ ] Add `render_strategy_builder(inputs)`.
- [ ] Add risk attribution panels to `render_portfolio_lab`.
- [ ] Add `render_report_mode(inputs)`.
- [ ] Run focused dashboard tests.

### Task 5: Verification, Commit, Push

**Files:**
- All changed files.

- [ ] Run `.venv/bin/python -m py_compile app/options_dashboard.py src/options_pricing_research/strategies.py src/options_pricing_research/portfolio_lab.py`.
- [ ] Run `.venv/bin/python -m pytest -q`.
- [ ] Confirm local Streamlit server responds with `curl -I -s http://localhost:8501 | sed -n '1,12p'`.
- [ ] Commit the implementation.
- [ ] Push `main` to `origin`.
