from decimal import Decimal
from pathlib import Path

from hl_asset_catalog.models import BenchmarkResult, Instrument, MarketAnalytics
from hl_asset_catalog.reporting import benchmark_quality, generate_medium_article


def test_quality_score_and_medium_generation(tmp_path: Path) -> None:
    benchmark = BenchmarkResult(
        benchmark_id="tech",
        name="Tech",
        status="sufficient",
        requested_symbols=["A", "B", "C", "D", "E"],
        available_symbols=["A", "B", "C", "D", "E"],
        missing_symbols=[],
        unique_constituents=5,
        coverage_ratio=1,
        total_volume_24h_usd=Decimal("1000000"),
        total_open_interest_usd=Decimal("2000000"),
        countries=["United States"],
        constituents=[],
    )
    analytics = [
        MarketAnalytics(
            instrument_id=f"xyz:{symbol}",
            symbol=symbol,
            dex="xyz",
            asset_class="equity",
            observations=90,
            annualized_volatility_pct=20,
            max_drawdown_pct=-10,
            historical_var_95_pct=-2,
            liquidity_score=80,
            data_quality_score=100,
            retrieved_at="2026-01-01T00:00:00Z",
        )
        for symbol in "ABCDE"
    ]
    rows = benchmark_quality([benchmark], analytics)
    assert rows[0]["quality_score"] > 70
    path = tmp_path / "medium.md"
    assets = [
        Instrument(
            id=f"xyz:{symbol}",
            canonical_symbol=symbol,
            exchange_symbol=f"xyz:{symbol}",
            dex="xyz",
            market_type="perp",
            asset_class="equity",
            country="United States",
        )
        for symbol in "ABCDE"
    ]
    correlations = {
        symbol: {other: 1.0 if symbol == other else 0.5 for other in "ABCDE"} for symbol in "ABCDE"
    }
    generate_medium_article(
        rows,
        analytics,
        assets,
        correlations,
        total_non_crypto=5,
        lookback_days=90,
        output_path=path,
        git_commit="0123456789abcdef",
    )
    article = path.read_text()
    assert "# Hyperliquid Beyond Crypto" in article
    assert "**5 non-crypto contracts**" in article
    assert "commit `0123456789ab`" in article
