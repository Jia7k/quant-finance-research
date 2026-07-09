import pandas as pd

from options_pricing_research.portfolio_lab import (
    build_portfolio_report,
    normalize_portfolio,
    performance_summary,
    rolling_average_correlation,
    rolling_portfolio_volatility,
    stress_test_portfolio,
)


def test_normalize_portfolio_accepts_common_csv_aliases_and_groups_tickers():
    raw = pd.DataFrame(
        {
            "Symbol": ["aapl", "AAPL", "msft"],
            "Shares": [2, 3, 4],
            "Average Cost": [100.0, 110.0, 200.0],
        }
    )

    normalized = normalize_portfolio(raw)

    assert normalized.loc[normalized["ticker"] == "AAPL", "quantity"].iloc[0] == 5
    assert normalized.loc[normalized["ticker"] == "MSFT", "quantity"].iloc[0] == 4


def test_build_portfolio_report_uses_latest_prices_for_weights():
    positions = pd.DataFrame({"ticker": ["AAA", "BBB"], "quantity": [2.0, 1.0]})
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 110.0, 121.0],
            "BBB": [50.0, 50.0, 55.0],
        },
        index=pd.bdate_range("2024-01-01", periods=3),
    )

    report = build_portfolio_report(positions, prices)

    aaa_weight = report.holdings.set_index("ticker").loc["AAA", "weight"]
    assert round(aaa_weight, 6) == round(242.0 / 297.0, 6)
    assert len(report.returns) == 2
    assert list(report.asset_returns.columns) == ["AAA", "BBB"]
    assert report.summary["annual_volatility"] >= 0.0


def test_build_portfolio_report_supports_weight_only_portfolios():
    positions = pd.DataFrame({"ticker": ["AAA", "BBB"], "weight": [0.75, 0.25]})
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 101.0, 102.0],
            "BBB": [100.0, 99.0, 98.0],
        },
        index=pd.bdate_range("2024-01-01", periods=3),
    )

    report = build_portfolio_report(positions, prices)

    assert round(report.weights.sum(), 12) == 1.0
    assert round(report.weights.loc["AAA"], 6) == 0.75


def test_performance_summary_reports_drawdown_and_sharpe():
    returns = pd.Series([0.02, -0.01, 0.03, -0.04])

    summary = performance_summary(returns)

    assert "sharpe" in summary.index
    assert summary["max_drawdown"] < 0.0
    assert summary["best_day"] == 0.03
    assert summary["worst_day"] == -0.04


def test_rolling_portfolio_volatility_is_annualized():
    returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01], index=pd.bdate_range("2024-01-01", periods=5))

    rolling = rolling_portfolio_volatility(returns, window=3)

    assert rolling.name == "rolling_3d_volatility"
    assert len(rolling) == 4
    assert rolling.iloc[-1] > 0.0


def test_rolling_average_correlation_uses_off_diagonal_pairs():
    asset_returns = pd.DataFrame(
        {
            "AAA": [0.01, 0.02, -0.01, -0.02, 0.03],
            "BBB": [0.02, 0.04, -0.02, -0.04, 0.06],
            "CCC": [-0.01, -0.02, 0.01, 0.02, -0.03],
        },
        index=pd.bdate_range("2024-01-01", periods=5),
    )

    rolling = rolling_average_correlation(asset_returns, window=3)

    assert rolling.name == "rolling_3d_average_correlation"
    assert len(rolling) == 3
    assert -1.0 <= rolling.iloc[-1] <= 1.0


def test_stress_test_portfolio_applies_ticker_shocks():
    holdings = pd.DataFrame(
        {
            "ticker": ["AAA", "BBB"],
            "market_value": [600.0, 400.0],
            "weight": [0.6, 0.4],
        }
    )

    stress = stress_test_portfolio(holdings, {"AAA": -0.10, "BBB": 0.05})

    assert stress.loc[stress["ticker"] == "AAA", "stress_pnl"].iloc[0] == -60.0
    assert stress.loc[stress["ticker"] == "BBB", "stress_pnl"].iloc[0] == 20.0
    assert round(stress["portfolio_impact"].sum(), 6) == -0.04
