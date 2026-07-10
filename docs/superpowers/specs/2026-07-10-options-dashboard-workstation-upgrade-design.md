# Options Dashboard Workstation Upgrade

## Context

Quant Finance Lab now has a polished visual system and a stronger research-case workflow. The next improvement should make it feel more like a serious options workstation: faster navigation, multi-leg strategy analysis, portfolio risk attribution, and a report mode that packages the research.

## Goal

Implement the next functional upgrade and push it when verified:

- Replace always-executed Streamlit tabs with page-style navigation so heavy views run only when active.
- Add an options strategy builder with multi-leg payoff, breakeven, max profit/loss classification, and combined Greeks.
- Add portfolio risk attribution for volatility contribution and worst-day return contribution.
- Add report mode with a downloadable Markdown memo for the current option case, strategy, and latest portfolio analysis when available.
- Keep the app professional, dense, accessible, and light-theme consistent.

## Non-Goals

- Do not replace Streamlit with another frontend stack.
- Do not add live brokerage, order execution, authentication, databases, or persistent cloud storage.
- Do not change existing option-pricing, Heston, Monte Carlo, hedging, or portfolio performance formulas.
- Do not add network-loaded fonts or assets.

## Approved Design

### Navigation

The top-level dashboard will use a page selector instead of `st.tabs`. The app will always have a current research case stored in session state. The `Inputs & Greeks` page updates that case. Other pages read the current case and render only their own heavy calculations.

Pages:

- Portfolio
- Strategy Builder
- Model Comparison
- Price Surface
- IV Smile
- Path Models
- Delta Hedge
- Inputs & Greeks
- Report

This preserves the existing mental model while reducing rerun cost for pages that do not need Heston Monte Carlo, Yahoo Finance, barrier simulations, or hedge paths.

### Strategy Builder

The strategy engine will live in `src/options_pricing_research/strategies.py` as testable pure logic. It will support option legs with:

- kind: `call` or `put`
- side: `long` or `short`
- strike
- premium
- quantity

It will compute payoff tables, total entry debit/credit, approximate breakevens, finite-grid max profit/loss values, unbounded-risk/profit labels where obvious, and combined Black-Scholes Greeks. Strategy presets will include long call, bull call spread, bear put spread, long straddle, long strangle, and collar-like option overlay.

### Portfolio Risk Attribution

Risk attribution will be added to `src/options_pricing_research/portfolio_lab.py`:

- Volatility contribution by ticker using the return covariance matrix and current weights.
- Worst-day contribution by ticker based on the worst portfolio return day.

The UI will show metrics, tables, and bar charts for top contributors. This makes the portfolio page more useful than aggregate return/volatility alone.

### Report Mode

Report mode will generate a Markdown memo containing:

- Research-case assumptions.
- Snapshot and warnings.
- Model comparison table.
- Strategy summary if a strategy was built during the session.
- Portfolio summary and top risk contributors if portfolio analysis was run during the session.

The report should be downloadable as `.md`. It should degrade gracefully when strategy or portfolio data is unavailable.

### UI/UX Requirements

- Use page selector active states with clear labels.
- Keep tables readable and downloadable.
- Keep charts accessible by also showing table fallbacks.
- Avoid decorative motion; Streamlit reruns should feel stable.
- Preserve focus visibility, readable contrast, and responsive table behavior.

## Testing

Add tests for:

- Strategy payoff and breakeven behavior.
- Strategy Greek aggregation.
- Risk contribution and worst-day contribution behavior.
- Report Markdown generation.
- Page metadata helpers so navigation labels remain stable.

Verification must include `pytest`, `py_compile`, and a local Streamlit response check before pushing.
