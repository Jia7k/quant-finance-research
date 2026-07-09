# Options Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the existing Streamlit options dashboard into a darker, denser, professional quant research workstation while preserving all current analytics behavior.

**Architecture:** Keep the app as a Streamlit dashboard in `app/options_dashboard.py`. The redesign is implemented through theme tokens, CSS injected by `apply_theme()`, a custom header renderer, and Plotly layout/color updates. Computational modules in `src/options_pricing_research/` remain unchanged.

**Tech Stack:** Python 3.10+, Streamlit, Plotly, pandas, numpy, existing `options_pricing_research` package.

## Global Constraints

- Do not replace Streamlit with a React, Tailwind, or custom frontend stack.
- Do not change pricing model formulas, simulation behavior, portfolio analytics, or Yahoo Finance data flow.
- Do not remove educational chart explanations; make them visually quieter and better integrated.
- Do not introduce external visual assets or network-loaded fonts.
- Use UI/UX Pro Max as the design QA checklist for density, contrast, chart semantics, loading states, and responsive behavior.
- Use 21st.dev outputs as visual reference only; do not add a React/shadcn/Tailwind stack to this Streamlit project.

---

## File Structure

- Modify `app/options_dashboard.py`: update palette constants, chart colors, CSS theme, header rendering, Plotly theme, and semantic chart color references.
- Create `docs/superpowers/plans/2026-07-10-options-dashboard-redesign.md`: implementation plan and task checklist.

---

### Task 1: Dark Theme Tokens And Header

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes: existing `main()`, `apply_theme()`, `PALETTE`, and `CHART_COLORS`.
- Produces: new `render_app_header() -> None`; updated palette keys consumed by all existing render functions.

- [x] **Step 1: Replace warm palette with dark dashboard tokens**

Update the top-level constants so all existing `PALETTE[...]` lookups still work:

```python
PALETTE = {
    "cream": "#020617",
    "cream_deep": "#050B18",
    "surface": "#0F172A",
    "surface_warm": "#111C31",
    "border": "#334155",
    "border_soft": "#1E293B",
    "charcoal": "#F8FAFC",
    "secondary": "#CBD5E1",
    "muted": "#94A3B8",
    "sage": "#22C55E",
    "sage_dark": "#14B8A6",
    "terracotta": "#F59E0B",
    "terracotta_dark": "#EF4444",
    "taupe": "#64748B",
    "slate": "#38BDF8",
    "olive": "#A78BFA",
    "clay": "#FB7185",
}
```

- [x] **Step 2: Update chart colorway**

Use an accessible dark-dashboard colorway:

```python
CHART_COLORS = [
    PALETTE["slate"],
    PALETTE["sage"],
    PALETTE["terracotta"],
    PALETTE["olive"],
    PALETTE["clay"],
    PALETTE["sage_dark"],
]
```

- [x] **Step 3: Replace `st.title(...)` with custom header**

In `main()`, replace:

```python
st.title("Quant Finance Lab")
```

with:

```python
render_app_header()
```

Add this function near `main()`:

```python
def render_app_header() -> None:
    st.markdown(
        """
        <section class="app-header">
            <div>
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
```

- [x] **Step 4: Run syntax check**

Run: `python -m py_compile app/options_dashboard.py`

Expected: command exits with status `0` and prints no Python syntax error.

---

### Task 2: Streamlit CSS Redesign

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes: existing `apply_theme() -> None`.
- Produces: dark professional styling for page background, tabs, controls, metrics, dataframes, dialogs, chart guides, and status messages.

- [x] **Step 1: Replace the CSS inside `apply_theme()`**

Replace the current warm CSS block with a dark theme that defines:

```css
:root {
    --bg: #020617;
    --bg-elevated: #050B18;
    --surface: #0F172A;
    --surface-2: #111C31;
    --surface-3: #172238;
    --border: #334155;
    --border-soft: #1E293B;
    --text: #F8FAFC;
    --text-soft: #CBD5E1;
    --muted: #94A3B8;
    --accent: #38BDF8;
    --accent-2: #F59E0B;
    --success: #22C55E;
    --danger: #EF4444;
    --focus: rgba(56, 189, 248, 0.38);
}
```

The CSS must include selector blocks for:

```css
.app-header
.header-pills
[data-testid="stMetric"]
.stTabs [data-baseweb="tab-list"]
.stTabs [data-baseweb="tab"]
.stTabs [aria-selected="true"]
.chart-guide
.chart-guide-item
@media (max-width: 760px)
@media (prefers-reduced-motion: reduce)
```

- [x] **Step 2: Preserve Streamlit control usability**

Ensure the CSS styles these selectors without hiding labels or breaking controls:

```css
input, textarea, [data-baseweb="select"] > div
[data-testid="stFileUploader"] section
[data-testid="stDataFrame"]
[data-testid="stDataEditor"]
[data-testid="stAlert"]
.stButton button
```

- [x] **Step 3: Run syntax check**

Run: `python -m py_compile app/options_dashboard.py`

Expected: command exits with status `0`.

---

### Task 3: Plotly And Semantic Chart Polish

**Files:**
- Modify: `app/options_dashboard.py`

**Interfaces:**
- Consumes: existing `apply_plotly_theme(fig: go.Figure, title: str, height: int = 430) -> go.Figure`.
- Produces: dark Plotly charts with readable axes, hover labels, legends, heatmaps, and semantic risk colors.

- [x] **Step 1: Update Plotly theme layout**

In `apply_plotly_theme()`, set:

```python
paper_bgcolor=PALETTE["surface"],
plot_bgcolor=PALETTE["surface"],
font={
    "family": 'Inter, "Source Sans 3", "Source Sans Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    "color": PALETTE["charcoal"],
    "size": 13,
},
hoverlabel={
    "bgcolor": PALETTE["surface_warm"],
    "bordercolor": PALETTE["border"],
    "font_color": PALETTE["charcoal"],
},
```

Keep `clickmode="event+select"` and `dragmode="select"` unchanged.

- [x] **Step 2: Update axes**

Use darker-dashboard grid and axis colors:

```python
fig.update_xaxes(
    gridcolor=PALETTE["border_soft"],
    linecolor=PALETTE["border"],
    zerolinecolor=PALETTE["border"],
    tickfont={"color": PALETTE["secondary"]},
    title_font={"color": PALETTE["secondary"]},
)
```

Apply the same values to `fig.update_yaxes(...)`.

- [x] **Step 3: Update heatmap colors**

For correlation heatmaps, use danger-to-neutral-to-success:

```python
colorscale=[
    [0.0, PALETTE["terracotta_dark"]],
    [0.5, PALETTE["surface_warm"]],
    [1.0, PALETTE["sage"]],
]
```

For price surface heatmaps, use dark-to-cyan-to-green:

```python
colorscale=[
    [0.0, PALETTE["surface_warm"]],
    [0.55, PALETTE["slate"]],
    [1.0, PALETTE["sage"]],
]
```

- [x] **Step 4: Run focused tests**

Run: `pytest tests/test_dashboard.py -q`

Expected: all tests in `tests/test_dashboard.py` pass.

---

### Task 4: Verification And Local Preview

**Files:**
- Modify: no source changes unless verification reveals a real issue.

**Interfaces:**
- Consumes: completed `app/options_dashboard.py`.
- Produces: verified redesigned dashboard and local preview URL.

- [x] **Step 1: Run full test suite**

Run: `pytest -q`

Expected: all tests pass.

- [x] **Step 2: Run py_compile**

Run: `python -m py_compile app/options_dashboard.py`

Expected: command exits with status `0`.

- [x] **Step 3: Start Streamlit**

Run:

```bash
streamlit run app/options_dashboard.py --server.headless true --server.port 8501
```

Expected: Streamlit serves the app at `http://localhost:8501`.

- [x] **Step 4: Browser or HTTP smoke check**

If browser tooling is available, open `http://localhost:8501` and capture a screenshot. If browser tooling is unavailable, run:

```bash
curl -I http://localhost:8501
```

Expected: HTTP response includes `200 OK` or a successful Streamlit response.
