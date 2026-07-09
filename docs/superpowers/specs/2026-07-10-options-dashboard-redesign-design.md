# Options Dashboard Professional Redesign

## Context

The project contains a Streamlit dashboard at `app/options_dashboard.py` for options pricing, portfolio analytics, risk views, and chart interpretation. The current implementation is functionally rich, but the visual language is warm and notebook-like. The redesign should make the app feel like a polished quant research workstation while preserving all pricing, portfolio, and educational workflows.

## Goal

Redesign the existing Streamlit dashboard with a darker professional trading/research terminal aesthetic:

- Make the first impression more serious, dense, and portfolio-ready.
- Improve visual hierarchy for headline metrics, tabs, controls, tables, and charts.
- Keep the app usable for repeated analysis rather than turning it into a marketing page.
- Preserve all current business logic, model calculations, user inputs, and chart interpretation behavior.

## Non-Goals

- Do not replace Streamlit with a React, Tailwind, or custom frontend stack.
- Do not change pricing model formulas, simulation behavior, portfolio analytics, or Yahoo Finance data flow.
- Do not remove educational chart explanations; make them visually quieter and better integrated.
- Do not introduce external visual assets or network-loaded fonts.

## Considered Approaches

### Dark Trading/Research Terminal

Use charcoal and navy surfaces, precise grid lines, cyan/blue quantitative accents, amber highlights, and red/green risk cues. Emphasize compact controls, metric tiles, and native-looking Plotly charts.

This is the selected approach because it best matches an options pricing and portfolio risk lab.

### Light Institutional Analytics

Use off-white backgrounds, gray-blue accents, and subdued cards similar to enterprise BI tools. This would be approachable but less distinctive and less aligned with the analytical trading context.

### Editorial Portfolio Showcase

Use large typography, narrative sections, and a portfolio-style first viewport. This would be visually polished, but it would weaken the app's repeated-use analytics ergonomics.

## Approved Design

### Visual System

The dashboard will use a dark layered palette:

- App background: near-black navy.
- Primary surfaces: dark blue-gray panels.
- Secondary surfaces: slightly lighter cards and controls.
- Borders: low-contrast slate lines.
- Primary accent: cyan/blue for analytical focus.
- Secondary accent: amber for model or warning emphasis.
- Risk colors: green for positive values, red for losses and stress.

Typography will use the existing system font stack with tighter weights and spacing. Text remains ASCII-only in source. Headings should be compact and dashboard-like, not oversized hero text.

### Layout

The top of the app will become a command-center header:

- Product name: `Quant Finance Lab`.
- Short subtitle describing pricing, hedging, and portfolio risk research.
- Small status pills for Streamlit, pricing models, and portfolio risk.

The existing tabs remain the main navigation because they map well to the dashboard modules. Tabs will be styled as a compact segmented control with a clear active state.

Inputs remain on the `Inputs & Greeks` tab to avoid reworking the application state model. Within that tab, control groups will look like coherent panels through Streamlit-compatible CSS.

### Components

- Metric tiles: stronger contrast, subtle top accent line, clear label/value hierarchy, and no oversized shadows.
- Dataframes and data editors: dark surfaces, bordered containers, readable headers, and preserved column formatting.
- Chart guides: compact dark guide chips that support interpretation without competing with charts.
- Buttons and upload controls: professional dark controls with clear hover and focus states.
- Dialogs: dark modal styling aligned with the rest of the app.

### Plotly Theme

Charts will be rethemed to match the app:

- Dark paper and plot backgrounds.
- Slate grid lines and axis lines.
- Cyan, blue, amber, green, red, and violet chart colorway.
- Dark hover labels.
- Horizontal legends with compact typography.
- Heatmaps updated to professional diverging or sequential scales.

Existing chart types, selected-point dialogs, and click behavior remain unchanged.

### Data Flow

No data flow changes are planned. User inputs continue to create an `inputs` dictionary, which is passed to existing render functions. Portfolio data still flows through `normalize_portfolio`, `cached_adjusted_close`, and `build_portfolio_report`. Chart selection events still flow through `render_explainable_chart`, `extract_selected_points`, and `chart_explanation_dialog`.

### Error Handling

Existing error handling remains:

- Invalid portfolio inputs show `st.info`.
- Invalid date ranges show `st.warning`.
- Yahoo Finance/report failures show `st.error`.
- Empty rolling windows show `st.info`.

The redesign should ensure these Streamlit status messages are readable in the dark theme.

### Testing And Verification

Verification should include:

- Run the existing pytest suite or the focused tests affected by dashboard imports.
- Run `python -m py_compile app/options_dashboard.py`.
- Start the Streamlit app locally and inspect the rendered dashboard.
- If browser tooling is available, capture at least one screenshot at desktop width and confirm the page is nonblank, readable, and not visually broken.

## Implementation Notes

The implementation should stay scoped mainly to `app/options_dashboard.py`:

- Replace the warm `PALETTE` values with dark professional tokens.
- Update `CHART_COLORS`.
- Replace `st.title` with a custom header renderer.
- Extend or replace `apply_theme` CSS.
- Update chart color references where semantic risk coloring matters.
- Keep computational functions and tests untouched unless a test import reveals a real issue.

