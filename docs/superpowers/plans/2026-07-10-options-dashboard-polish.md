# Options Dashboard Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the Streamlit dashboard so it reads as a clean institutional analytics app, with native-light widgets, a compact header, better table/control layout, and consistent chart styling.

**Architecture:** Keep the current Streamlit app and calculations intact. Use `.streamlit/config.toml` for native Streamlit theming, use targeted CSS only for page framing and polish, and adjust `app/options_dashboard.py` layout and chart colors without changing pricing or portfolio logic.

**Tech Stack:** Python 3.10+, Streamlit, Plotly, pandas, numpy, existing `options_pricing_research` package.

## Global Constraints

- Do not replace Streamlit with a React, Tailwind, or custom frontend stack.
- Do not change pricing model formulas, simulation behavior, portfolio analytics, or Yahoo Finance data flow.
- Use Streamlit native theming as the source of truth for widgets and tables.
- Keep custom CSS restrained and avoid dark widget overrides.
- Keep green/red reserved for actual positive/negative outcome semantics.
- Verify with `python -m py_compile`, `pytest`, and a local Streamlit HTTP smoke check.

---

## File Structure

- Modify `.streamlit/config.toml`: make Streamlit use the light institutional theme and minimize the toolbar.
- Modify `app/options_dashboard.py`: tighten header, CSS, portfolio input/table layout, and chart colors.
- Create `docs/superpowers/plans/2026-07-10-options-dashboard-polish.md`: track implementation steps.

---

### Task 1: Streamlit Native Theme And Chrome

**Files:**
- Modify: `.streamlit/config.toml`

**Interfaces:**
- Consumes: Streamlit config loaded at app startup.
- Produces: native-light widgets, native-light `st.data_editor`, and reduced toolbar chrome.

- [x] **Step 1: Add toolbar mode to config**

Use this config:

```toml
[theme]
base = "light"
primaryColor = "#1E40AF"
backgroundColor = "#F8FAFC"
secondaryBackgroundColor = "#EEF4FB"
textColor = "#0F172A"
font = "sans serif"

[client]
toolbarMode = "minimal"
```

- [x] **Step 2: Verify Streamlit config command accepts the file**

Run: `.venv/bin/streamlit config show | rg -n "toolbarMode|primaryColor|backgroundColor"`

Expected: command exits `0` and prints the configured keys or Streamlit's resolved defaults.

---

### Task 2: Header And Page Shell Polish

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes: `render_app_header() -> None`, `apply_theme() -> None`.
- Produces: compact masthead, less dead space, neutral page shell, and no dark widget overrides.

- [x] **Step 1: Compact the header**

Update `.app-header` padding, shadow, H1 size, and paragraph spacing so the header feels like a dashboard masthead, not a landing hero.

- [x] **Step 2: Remove broad dark-control overrides**

Keep light, minimal selectors for `input`, `textarea`, and `[data-baseweb="select"] > div`; do not force dark backgrounds or global text color into every child widget.

- [x] **Step 3: Hide/minimize deploy chrome where Streamlit permits**

Add CSS for Streamlit deploy/status chrome:

```css
[data-testid="stToolbar"] {
    right: 0.75rem;
}
```

Do not hide critical app content or interaction controls.

- [x] **Step 4: Run syntax check**

Run: `.venv/bin/python -m py_compile app/options_dashboard.py`

Expected: command exits `0`.

---

### Task 3: Portfolio Input And Table Layout

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes: `render_portfolio_lab(inputs: dict[str, object]) -> None`.
- Produces: readable portfolio entry table and right-side controls with consistent panel styling.

- [x] **Step 1: Use native bordered containers**

In `render_portfolio_lab()`, use native Streamlit containers in each column:

```python
with st.container(border=True):
    st.markdown("#### Positions")
```

- [x] **Step 2: Wrap portfolio entry and settings controls**

In `render_portfolio_lab()`, wrap manual/CSV controls in `with st.container(border=True):` under `#### Positions`, and date/rate inputs in `with st.container(border=True):` under `#### History and assumptions`.

- [x] **Step 3: Improve the editable positions table**

For the manual `st.data_editor`, set:

```python
height=210,
column_config={
    "ticker": st.column_config.TextColumn("Ticker", width="medium"),
    "quantity": st.column_config.NumberColumn("Quantity", min_value=0.0, width="small"),
},
```

- [x] **Step 4: Add panel CSS**

Add light styling for bordered Streamlit containers:

```css
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface);
    border-color: var(--border);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}
```

- [x] **Step 5: Run syntax check**

Run: `.venv/bin/python -m py_compile app/options_dashboard.py`

Expected: command exits `0`.

---

### Task 4: Chart And Data Visual Consistency

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes: `apply_plotly_theme(fig: go.Figure, title: str, height: int = 430) -> go.Figure`, chart render functions.
- Produces: white chart panels, pale gridlines, restrained chart colorway, and semantic risk colors.

- [x] **Step 1: Keep Plotly on the same light palette**

Ensure `paper_bgcolor` and `plot_bgcolor` use `PALETTE["surface"]`; hover labels use `PALETTE["surface_warm"]`; axes use `PALETTE["border_soft"]`.

- [x] **Step 2: Keep chart colorway restrained**

Use blue, indigo, amber, slate, green, red in that order:

```python
CHART_COLORS = [
    PALETTE["slate"],
    PALETTE["clay"],
    PALETTE["terracotta"],
    PALETTE["olive"],
    PALETTE["sage"],
    PALETTE["terracotta_dark"],
]
```

- [x] **Step 3: Run focused dashboard tests**

Run: `.venv/bin/python -m pytest tests/test_dashboard.py -q`

Expected: all dashboard tests pass.

---

### Task 5: Verification And Restart

**Files:**
- Modify: no source changes unless verification reveals a real issue.

**Interfaces:**
- Consumes: completed app/config changes.
- Produces: locally running, verified dashboard.

- [x] **Step 1: Run full tests**

Run: `.venv/bin/python -m pytest -q`

Expected: `31 passed`.

- [x] **Step 2: Run compile check**

Run: `.venv/bin/python -m py_compile app/options_dashboard.py`

Expected: command exits `0`.

- [x] **Step 3: Restart Streamlit**

Stop the existing Streamlit session and run:

```bash
.venv/bin/streamlit run app/options_dashboard.py --server.headless true --server.port 8501
```

Expected: app serves at `http://localhost:8501`.

- [x] **Step 4: Smoke check**

Run: `curl -I http://localhost:8501`

Expected: `HTTP/1.1 200 OK`.
