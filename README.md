# Quant Finance Research

A reproducible quant finance research portfolio with Python notebooks and tested source code. The repo currently covers cross-sectional equity factor research and student-style options pricing papers.

This is built as a portfolio project for quant research / quant trading applications. It emphasizes point-in-time signal construction, walk-forward testing, transaction costs, and clear research reporting rather than a black-box "stock predictor."

## Interactive Options Pricing Dashboard

The repo includes a Streamlit dashboard that turns the options pricing code into an interactive app:

- Black-Scholes price and Greeks
- Model comparison across Black-Scholes, CRR binomial, and Heston Monte Carlo
- Strike/volatility price heatmap
- Synthetic implied-volatility smile
- Knock-out barrier option comparison
- Delta-hedging simulator for a dynamically hedged short option
- Portfolio analytics from manual Yahoo Finance tickers or CSV upload
- Allocation, cumulative return, drawdown, and correlation charts
- Rolling portfolio volatility and rolling average correlation
- Scenario stress testing with editable per-ticker price shocks

Run it locally:

```bash
pip install -e ".[dashboard]"
streamlit run app/options_dashboard.py
```

Portfolio CSVs can use columns like:

```csv
ticker,quantity
AAPL,5
MSFT,3
D05.SI,100
```

## Options Pricing Paper Notebooks

The repo includes semi-learning options pricing notebooks written in a student research-note style:

- `notebooks/black_scholes_pricing_paper.ipynb`
- `notebooks/binomial_tree_learning_paper.ipynb`
- `notebooks/barrier_options_learning_paper.ipynb`
- `notebooks/heston_model_learning_paper.ipynb`
- `src/options_pricing_research/black_scholes.py`
- `src/options_pricing_research/binomial.py`
- `src/options_pricing_research/monte_carlo.py`
- `src/options_pricing_research/heston.py`

The notebooks cover Black-Scholes-Merton pricing, Greeks, put-call parity, implied volatility, binomial trees, American exercise, barrier options, Monte Carlo path dependency, and a first look at stochastic volatility through the Heston model.

To open it locally:

```bash
pip install -e ".[paper]"
jupyter lab
```

## Research Question

Do momentum, short-term reversal, volatility, volume surprise, and overnight return features predict next-day relative returns across a liquid equity universe?

The default strategy:

- Computes daily factor values for each ticker.
- Shifts all factors by one day to reduce lookahead bias.
- Cross-sectionally z-scores each factor.
- Combines the factor z-scores into one ranking signal.
- Buys the top-ranked names and shorts the bottom-ranked names.
- Applies turnover-based transaction costs.
- Reports performance and information coefficient statistics.

## Quick Start

Create an environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the deterministic demo backtest:

```bash
python -m quant_factor_research --output reports/demo
```

Run on Yahoo Finance data:

```bash
python -m quant_factor_research \
  --download \
  --tickers AAPL MSFT AMZN GOOGL META NVDA JPM XOM UNH PG \
  --start 2018-01-01 \
  --cost-bps 5 \
  --output reports/live
```

Run tests:

```bash
pytest
```

## Outputs

Each run writes:

- `summary.csv`: return, risk, turnover, and information coefficient summary.
- `returns.csv`: daily net strategy returns.
- `equity_curve.csv`: cumulative growth of one dollar.
- `turnover.csv`: daily portfolio turnover.
- `weights.csv`: daily position weights.
- `composite_signal.csv`: final ranking signal.
- `factor_ic.csv`: daily information coefficient by raw factor.
- `equity_curve.png`: chart of cumulative strategy performance.

## Project Structure

```text
src/quant_factor_research/
  data.py        # Synthetic data, CSV loader, Yahoo Finance downloader
  factors.py     # Point-in-time factor construction and signal blending
  portfolio.py   # Long/short and long-only portfolio construction
  backtest.py    # Forward-return backtester with transaction costs
  metrics.py     # Performance and information coefficient analytics
  cli.py         # Reproducible command-line research runner
src/options_pricing_research/
  black_scholes.py
  binomial.py
  monte_carlo.py
  heston.py
  hedging.py
  portfolio_lab.py
  dashboard.py
app/
  options_dashboard.py
notebooks/
  black_scholes_pricing_paper.ipynb
  binomial_tree_learning_paper.ipynb
  barrier_options_learning_paper.ipynb
  heston_model_learning_paper.ipynb
tests/
  test_factors.py
  test_backtest.py
  test_black_scholes.py
  test_binomial.py
  test_dashboard.py
  test_hedging.py
  test_portfolio_lab.py
  test_monte_carlo_models.py
```

## Bias Controls

This repo is intentionally conservative about common beginner quant mistakes:

- Factors are shifted before being used for next-period returns.
- The backtester uses forward close-to-close returns indexed by the signal date.
- Transaction costs are based on actual portfolio turnover.
- The demo path uses deterministic synthetic data so tests and smoke runs are reproducible.
- The Yahoo Finance path is optional, making external data availability separate from project correctness.

## Next Research Extensions

Good additions for future commits:

- Sector-neutral ranking.
- Rolling train/test windows for factor weights.
- Risk model constraints.
- Borrow-cost assumptions for short positions.
- Bootstrap confidence intervals for performance metrics.
- A notebook that turns `factor_ic.csv` and `summary.csv` into a polished research memo.

## Disclaimer

This project is for research and education. It is not investment advice and should not be used as a live trading system without substantially more data validation, risk controls, and execution modeling.
