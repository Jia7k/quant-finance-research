from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from quant_factor_research.backtest import next_close_returns, run_backtest
from quant_factor_research.data import DEFAULT_TICKERS, download_yfinance, make_synthetic_ohlcv
from quant_factor_research.factors import build_composite_signal, compute_factors
from quant_factor_research.metrics import ic_summary, information_coefficient, performance_summary
from quant_factor_research.portfolio import make_long_only_weights, make_long_short_weights


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a reproducible cross-sectional factor research backtest."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download Yahoo Finance data instead of using deterministic demo data.",
    )
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS)
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--periods", type=int, default=756)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n-long", type=int, default=3)
    parser.add_argument("--n-short", type=int, default=3)
    parser.add_argument("--long-only", action="store_true")
    parser.add_argument("--cost-bps", type=float, default=5.0)
    parser.add_argument("--min-factors", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("reports/demo"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.download:
        data = download_yfinance(args.tickers, start=args.start, end=args.end)
        data_source = "yfinance"
    else:
        data = make_synthetic_ohlcv(args.tickers, periods=args.periods, seed=args.seed)
        data_source = "synthetic"

    factors = compute_factors(data)
    signal = build_composite_signal(factors, min_factors=args.min_factors)

    if args.long_only:
        weights = make_long_only_weights(signal, n_long=args.n_long)
    else:
        weights = make_long_short_weights(signal, n_long=args.n_long, n_short=args.n_short)

    result = run_backtest(data.close, weights, cost_bps=args.cost_bps)
    forward_returns = next_close_returns(data.close)
    composite_ic = information_coefficient(signal, forward_returns)
    factor_ic = pd.DataFrame(
        {
            name: information_coefficient(factor, forward_returns)
            for name, factor in factors.items()
        }
    )

    summary = performance_summary(result.returns, result.turnover)
    summary = pd.concat(
        [
            pd.Series(
                {
                    "data_source": data_source,
                    "tickers": " ".join(data.tickers),
                    "observations": len(result.returns),
                    "cost_bps": args.cost_bps,
                }
            ),
            summary,
            ic_summary(composite_ic).add_prefix("composite_"),
        ]
    )

    summary.to_frame("value").to_csv(output_dir / "summary.csv")
    result.returns.to_csv(output_dir / "returns.csv")
    result.equity_curve.to_csv(output_dir / "equity_curve.csv")
    result.turnover.to_csv(output_dir / "turnover.csv")
    weights.to_csv(output_dir / "weights.csv")
    signal.to_csv(output_dir / "composite_signal.csv")
    factor_ic.to_csv(output_dir / "factor_ic.csv")

    _plot_equity_curve(result.equity_curve, output_dir / "equity_curve.png")

    printable = summary.copy()
    numeric = pd.to_numeric(printable, errors="coerce")
    for key, value in numeric.dropna().items():
        printable.loc[key] = f"{value:.4f}"

    print(printable.to_string())
    print(f"\nWrote report files to: {output_dir}")
    return 0


def _plot_equity_curve(equity_curve: pd.Series, path: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 5))
    equity_curve.plot(ax=ax, color="#0f766e", linewidth=2)
    ax.set_title("Composite Factor Strategy Equity Curve")
    ax.set_xlabel("")
    ax.set_ylabel("Growth of $1")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
