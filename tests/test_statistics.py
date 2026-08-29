from datetime import UTC, datetime
from decimal import Decimal

import pytest

from hl_asset_catalog.statistics import (
    annualized_volatility,
    correlation,
    dated_correlation,
    dated_returns,
    historical_var_95,
    max_drawdown,
    order_book_metrics,
    period_return,
    session_returns,
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


def test_dated_correlation_uses_only_shared_candle_timestamps() -> None:
    left_candles = [{"t": day, "c": str(100 + day)} for day in range(22)]
    right_candles = [{"t": day, "c": str(200 + day * 2)} for day in range(1, 23)]
    left = dated_returns(left_candles)
    right = dated_returns(right_candles)

    value, observations = dated_correlation(left, right)

    assert observations == 20
    assert value == pytest.approx(1.0)


def test_dated_correlation_rejects_insufficient_overlap() -> None:
    value, observations = dated_correlation({1: 0.1, 2: 0.2}, {2: 0.2, 3: 0.3})
    assert value is None
    assert observations == 1


def timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp() * 1_000)


def test_session_returns_use_reference_market_dates() -> None:
    candles = [
        {"t": timestamp("2026-01-02T01:00:00"), "c": "100"},
        {"t": timestamp("2026-01-03T01:00:00"), "c": "101"},
    ]
    crypto = session_returns(candles, is_24_7=True, country=None)
    us_equity = session_returns(candles, is_24_7=False, country="United States")
    assert list(crypto) == ["2026-01-03"]
    assert list(us_equity) == ["2026-01-02"]


def test_us_and_asia_sessions_do_not_pair_different_local_dates() -> None:
    candles = [
        {"t": timestamp("2026-01-02T01:00:00"), "c": "100"},
        {"t": timestamp("2026-01-03T01:00:00"), "c": "101"},
    ]
    us = session_returns(candles, is_24_7=False, country="United States")
    japan = session_returns(candles, is_24_7=False, country="Japan")
    _, observations = dated_correlation(us, japan, minimum_observations=1)
    assert observations == 0


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
