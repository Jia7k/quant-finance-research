# Options Dashboard Functional Upgrade

## Context

The dashboard now has a cleaner visual system, but the workflow still feels like a set of separate calculators. The next upgrade should make the app behave more like a compact options research workstation: users can start from useful scenarios, see a current research snapshot, get sanity checks, stress a portfolio faster, and export their assumptions/results.

## Goal

Add practical workflow features that improve the dashboard without changing pricing formulas or replacing Streamlit:

- Scenario presets for common option research cases.
- A research summary panel that explains the active option setup.
- Input and numerical sanity checks for suspicious cases.
- Portfolio CSV validation and clearer status around usable positions.
- Better stress presets and compact export actions.

## Non-Goals

- Do not add multi-leg options strategies in this pass.
- Do not alter the Black-Scholes, CRR, Heston, barrier, hedging, or portfolio math.
- Do not add external services, databases, authentication, or a new frontend stack.
- Do not add network-loaded fonts or assets.

## Functional Design

### Scenario Presets

The `Inputs & Greeks` tab will start with a scenario selector. Presets update the default values for contract, model, barrier, and hedge inputs. The initial preset is `Balanced ATM Call`, with additional choices for a defensive put, high-volatility earnings case, near-barrier knock-out case, and short-dated hedge stress case.

The preset values are pure dictionaries so they can be tested and exported. Streamlit widgets will use preset values as defaults; no separate state engine is needed.

### Research Snapshot

After option metrics are calculated, the app will render a compact panel with:

- Moneyness and option classification.
- Breakeven price.
- Premium as a percentage of spot.
- Largest absolute Greek among Delta, Gamma, Vega per 1%, and Theta per day.
- Hedge rebalancing cadence.

This gives users a readable "what am I looking at" summary before jumping into deeper tabs.

### Sanity Checks

The app will compute deterministic input checks:

- Very short expiries.
- Very high or very low volatility.
- Barrier too close to spot.
- Barrier direction that is already breached.
- Low Monte Carlo path counts for path-dependent pricing.
- Large realized/pricing volatility mismatch.

Warnings will render as a compact review panel. They are informational and do not block calculations.

### Portfolio Workflow

CSV uploads will show required columns before users upload. Uploaded data will be validated for ticker and quantity/weight availability before normalization runs. After normalization, the app will show accepted ticker count and dropped invalid-row messaging where possible.

The stress tool will gain more useful presets:

- Market selloff (-5% all).
- Relief rally (+5% all).
- Largest holding shock (-10%).
- Concentration stress (-10% top two).
- Tech-led selloff (-8% large growth names).
- Rate shock proxy (-4% duration/growth, +2% cashlike/defensive tickers).

### Export Actions

The app will add download buttons for:

- Current option research case as JSON.
- Normalized positions as CSV.
- Holdings and stress results as CSV when available.

The JSON export will be generated from pure Python data so it is deterministic and testable.

## Data Flow

`render_inputs_and_greeks()` produces the same `inputs` dictionary shape used by the rest of the app. Presets only change widget defaults. `build_research_case_export()` receives `inputs` and optional risk checks and returns JSON-serializable data. Portfolio export buttons consume normalized `positions`, `holdings`, and stress result frames already produced by existing functions.

## Error Handling

Invalid presets should not be possible through the UI. Invalid CSV uploads show an info message before portfolio calculations run. Sanity checks render as warnings but do not block calculations. Existing `st.error`, `st.warning`, and `st.info` behavior remains.

## Testing

Add focused tests for pure helper behavior:

- Presets produce complete input defaults.
- Research snapshot classifies moneyness and breakeven correctly.
- Sanity checks catch near barriers and volatility mismatch.
- CSV validation accepts aliases and rejects missing ticker/exposure columns.
- Stress presets generate expected shock vectors.
- Research-case export is JSON serializable.
