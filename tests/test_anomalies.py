from decimal import Decimal

from hl_asset_catalog.analytics import _market_anomalies
from hl_asset_catalog.models import Instrument
from hl_asset_catalog.statistics import order_book_metrics


def test_market_anomalies_detect_abnormal_state() -> None:
    asset = Instrument(
        id="xyz:X",
        canonical_symbol="X",
        exchange_symbol="xyz:X",
        dex="xyz",
        market_type="perp",
        mark_price=Decimal("110"),
        oracle_price=Decimal("100"),
    )
    book = {"levels": [[{"px": "101", "sz": "1"}], [{"px": "100", "sz": "1"}]]}
    divergence, anomalies = _market_anomalies(
        asset,
        [{"t": 1, "c": "100"}],
        book,
        order_book_metrics(book),
        now_ms=10_000_000,
        oracle_divergence_bps=100,
        abnormal_spread_bps=50,
        stale_candle_hours=1,
    )
    assert divergence == 1000
    assert {"mark_oracle_divergence", "crossed_order_book", "stale_candle_data"} <= set(anomalies)


def test_market_anomalies_detect_empty_book() -> None:
    asset = Instrument(
        id="xyz:X",
        canonical_symbol="X",
        exchange_symbol="xyz:X",
        dex="xyz",
        market_type="perp",
    )
    book = {"levels": [[], []]}
    _, anomalies = _market_anomalies(
        asset,
        [],
        book,
        order_book_metrics(book),
        now_ms=1,
        oracle_divergence_bps=100,
        abnormal_spread_bps=50,
        stale_candle_hours=1,
    )
    assert "empty_order_book" in anomalies
