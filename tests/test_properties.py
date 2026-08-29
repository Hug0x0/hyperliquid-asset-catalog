import math
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hl_asset_catalog.basket_engine import _weights
from hl_asset_catalog.models import Instrument
from hl_asset_catalog.statistics import (
    annualized_volatility,
    historical_var_95,
    max_drawdown,
    order_book_metrics,
)


def instrument(index: int, volume: Decimal) -> Instrument:
    return Instrument(
        id=str(index),
        canonical_symbol=str(index),
        exchange_symbol=str(index),
        dex="native",
        market_type="perp",
        volume_24h_usd=volume,
    )


@given(st.lists(st.decimals(min_value=0, max_value=1_000_000, places=4), min_size=1, max_size=30))
def test_liquidity_weights_always_sum_to_one(volumes: list[Decimal]) -> None:
    weights, _ = _weights(
        [instrument(index, value) for index, value in enumerate(volumes)], "liquidity"
    )
    assert math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12)
    assert all(math.isfinite(value) and value >= 0 for value in weights.values())


@given(
    st.lists(
        st.floats(min_value=0.01, max_value=1_000_000, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=200,
    )
)
def test_risk_statistics_never_emit_non_finite_values(prices: list[float]) -> None:
    returns = [prices[index] / prices[index - 1] - 1 for index in range(1, len(prices))]
    for result in (
        annualized_volatility(returns),
        historical_var_95(returns),
        max_drawdown(prices),
    ):
        assert result is None or math.isfinite(result)
    drawdown = max_drawdown(prices)
    assert drawdown is None or drawdown <= 0


@given(
    bid_prices=st.lists(st.integers(min_value=90, max_value=99), min_size=1, max_size=20),
    ask_prices=st.lists(st.integers(min_value=101, max_value=110), min_size=1, max_size=20),
)
def test_unordered_and_duplicate_books_preserve_best_prices(
    bid_prices: list[int], ask_prices: list[int]
) -> None:
    book = {
        "levels": [
            [{"px": str(price), "sz": "1000"} for price in bid_prices],
            [{"px": str(price), "sz": "1000"} for price in ask_prices],
        ]
    }
    metrics = order_book_metrics(book)
    expected_mid = (max(bid_prices) + min(ask_prices)) / 2
    expected_spread = (min(ask_prices) - max(bid_prices)) / expected_mid * 10_000
    assert metrics["spread_bps"] == pytest.approx(expected_spread)
    assert metrics["buy_slippage_10k_bps"] is not None
    assert metrics["sell_slippage_10k_bps"] is not None
