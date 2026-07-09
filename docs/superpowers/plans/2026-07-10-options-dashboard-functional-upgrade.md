# Options Dashboard Functional Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add scenario presets, research summaries, sanity checks, portfolio validation, richer stress presets, and exports to the Streamlit options dashboard.

**Architecture:** Keep the existing Streamlit single-file dashboard structure, but add pure helper functions near the top of `app/options_dashboard.py` so behavior is testable without rendering the app. UI render functions consume those helpers while preserving the existing `inputs` dictionary used by all model tabs.

**Tech Stack:** Python 3.13, Streamlit, pandas, numpy, Plotly, pytest.

## Global Constraints

- Preserve all current option pricing, path, hedge, and portfolio formulas.
- Do not replace Streamlit or add a React/custom frontend stack.
- Keep source text ASCII-only.
- Do not add network-loaded fonts, external assets, new services, or databases.
- Keep UI dense, professional, and readable on light Streamlit theme.

---

### Task 1: Functional Helper Tests

**Files:**
- Create: `tests/test_options_dashboard_app.py`
- Modify: none

**Interfaces:**
- Consumes: `RESEARCH_CASE_PRESETS`, `get_research_case_preset`, `build_research_snapshot`, `build_input_warnings`, `validate_portfolio_frame`, `build_stress_editor_frame`, `build_research_case_export`
- Produces: failing tests that define the helper API

- [ ] **Step 1: Write failing tests**

Create `tests/test_options_dashboard_app.py` with tests that import pure helpers from `app.options_dashboard`.

- [ ] **Step 2: Run tests to verify failure**

Run: `.venv/bin/python -m pytest tests/test_options_dashboard_app.py -q`
Expected: FAIL because the new helper names are missing or incomplete.

### Task 2: Presets, Snapshot, Warnings, Validation, Exports

**Files:**
- Modify: `app/options_dashboard.py`
- Test: `tests/test_options_dashboard_app.py`

**Interfaces:**
- Consumes: existing `option_metrics`, `normalize_portfolio`, and Streamlit render functions.
- Produces:
  - `RESEARCH_CASE_PRESETS: dict[str, dict[str, object]]`
  - `get_research_case_preset(name: str) -> dict[str, object]`
  - `build_research_snapshot(inputs: dict[str, object], price: float, greeks: pd.Series) -> dict[str, str]`
  - `build_input_warnings(inputs: dict[str, object]) -> list[str]`
  - `validate_portfolio_frame(raw: pd.DataFrame) -> list[str]`
  - `build_research_case_export(inputs: dict[str, object], warnings: list[str]) -> dict[str, object]`

- [ ] **Step 1: Implement pure helpers**

Add the helper functions near the top of `app/options_dashboard.py`.

- [ ] **Step 2: Run helper tests**

Run: `.venv/bin/python -m pytest tests/test_options_dashboard_app.py -q`
Expected: PASS.

### Task 3: Streamlit Workflow Integration

**Files:**
- Modify: `app/options_dashboard.py`
- Test: `tests/test_options_dashboard_app.py`

**Interfaces:**
- Consumes: helpers from Task 2.
- Produces: rendered preset selector, research summary, warning panel, CSV validation copy, export buttons, and richer stress presets.

- [ ] **Step 1: Integrate presets and summary into inputs tab**

Update `render_inputs_and_greeks()` to use preset defaults, render the summary panel, and provide JSON export.

- [ ] **Step 2: Integrate portfolio validation and exports**

Update `render_portfolio_lab()` to show CSV requirements, validate upload frames, and add downloads for normalized positions and holdings.

- [ ] **Step 3: Extend stress preset logic**

Update `build_stress_editor_frame()` and stress UI options with the new stress scenarios.

- [ ] **Step 4: Run focused tests**

Run: `.venv/bin/python -m pytest tests/test_options_dashboard_app.py tests/test_dashboard.py tests/test_portfolio_lab.py -q`
Expected: PASS.

### Task 4: Verification

**Files:**
- Modify: none
- Test: full repository tests and syntax compile

**Interfaces:**
- Consumes: all implemented changes.
- Produces: verification evidence.

- [ ] **Step 1: Compile dashboard**

Run: `.venv/bin/python -m py_compile app/options_dashboard.py`
Expected: exit code 0.

- [ ] **Step 2: Run full tests**

Run: `.venv/bin/python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 3: Confirm Streamlit server responds**

Run: `curl -I -s http://localhost:8501 | sed -n '1,12p'`
Expected: HTTP 200 if the running server is active.
