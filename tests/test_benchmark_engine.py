from decimal import Decimal
from pathlib import Path

import yaml

from hl_asset_catalog.benchmark_engine import build_sector_benchmarks, deduplicate_markets
from hl_asset_catalog.models import Instrument


def instrument(symbol: str, dex: str, volume: str) -> Instrument:
    return Instrument(
        id=f"{dex}:{symbol}",
        canonical_symbol=symbol,
        exchange_symbol=f"{dex}:{symbol}",
        dex=dex,
        market_type="perp",
        asset_class="equity",
        is_active=True,
        volume_24h_usd=Decimal(volume),
    )


def test_deduplication_selects_most_liquid_market() -> None:
    selected = deduplicate_markets(
        [instrument("NVDA", "xyz", "10"), instrument("NVDA", "flx", "20")]
    )
    assert selected["NVDA"].dex == "flx"


def test_benchmark_status_thresholds(tmp_path: Path) -> None:
    path = tmp_path / "benchmarks.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "sufficient_constituents": 5,
                "concentrated_constituents": 3,
                "benchmarks": {
                    "sector": {
                        "name": "Sector",
                        "symbols": ["A", "B", "C", "D", "E", "F"],
                    }
                },
            }
        )
    )
    assets = [instrument(symbol, "xyz", "1") for symbol in "ABCDE"]
    result = build_sector_benchmarks(assets, path)[0]
    assert result.status == "sufficient"
    assert result.unique_constituents == 5
    assert result.missing_symbols == ["F"]
    assert result.total_volume_24h_usd == Decimal("5")
