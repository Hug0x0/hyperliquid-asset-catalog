from decimal import Decimal

import pytest

from hl_asset_catalog.statistics import (
    annualized_volatility,
    correlation,
    historical_var_95,
    max_drawdown,
    order_book_metrics,
    period_return,
    simple_returns,
)


def test_return_and_risk_statistics() -> None:
    prices = [100.0 + index for index in range(31)]
    returns = simple_returns(prices)
    assert period_return(prices, 30) == pytest.approx(30.0)
    assert annualized_volatility(returns) is not None
    assert max_drawdown(prices) == 0
    assert historical_var_95(returns) is not None
    assert correlation(returns, returns) == pytest.approx(1.0)


def test_order_book_liquidity_metrics() -> None:
    book = {
        "levels": [
            [{"px": "99.9", "sz": "200"}],
            [{"px": "100.1", "sz": "200"}],
        ]
    }
    metrics = order_book_metrics(book, target_notional=Decimal("10000"))
    assert metrics["spread_bps"] == pytest.approx(20.0)
    assert metrics["bid_depth_10bps_usd"] == Decimal("19980.0")
    assert metrics["ask_depth_10bps_usd"] == Decimal("20020.0")
    assert metrics["buy_slippage_10k_bps"] == pytest.approx(10.0)
