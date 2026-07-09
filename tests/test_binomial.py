from options_pricing_research.binomial import cox_ross_rubinstein_price
from options_pricing_research.black_scholes import black_scholes_price


def test_crr_european_call_converges_to_black_scholes():
    tree_price = cox_ross_rubinstein_price(
        "call",
        spot=100.0,
        strike=100.0,
        time_to_expiry=1.0,
        risk_free_rate=0.05,
        volatility=0.20,
        steps=1_000,
    )
    closed_form = black_scholes_price("call", 100.0, 100.0, 1.0, 0.05, 0.20)

    assert abs(tree_price - closed_form) < 0.01


def test_american_put_is_worth_at_least_european_put():
    european = cox_ross_rubinstein_price(
        "put",
        100.0,
        100.0,
        1.0,
        0.05,
        0.20,
        steps=500,
        exercise_style="european",
    )
    american = cox_ross_rubinstein_price(
        "put",
        100.0,
        100.0,
        1.0,
        0.05,
        0.20,
        steps=500,
        exercise_style="american",
    )

    assert american >= european
