from __future__ import annotations

import csv
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from .config import load_yaml
from .models import BenchmarkResult, Instrument
from .utils import atomic_json

NON_CRYPTO_CLASSES = {
    "equity",
    "equity_index",
    "commodity",
    "forex",
    "interest_rate",
    "volatility_index",
    "pre_ipo",
}


def _market_score(asset: Instrument) -> tuple[Decimal, Decimal, int]:
    """Rank duplicate markets by volume, then OI, then XYZ preference."""
    return (
        asset.volume_24h_usd or Decimal(0),
        asset.open_interest_usd or Decimal(0),
        int(asset.dex == "xyz"),
    )


def deduplicate_markets(assets: Iterable[Instrument]) -> dict[str, Instrument]:
    selected: dict[str, Instrument] = {}
    for asset in assets:
        if not asset.is_active or asset.asset_class not in NON_CRYPTO_CLASSES:
            continue
        symbol = asset.canonical_symbol.upper()
        current = selected.get(symbol)
        if current is None or _market_score(asset) > _market_score(current):
            selected[symbol] = asset
    return selected


def build_sector_benchmarks(
    assets: list[Instrument], definitions_path: Path
) -> list[BenchmarkResult]:
    config = load_yaml(definitions_path)
    definitions = dict(config.get("benchmarks", {}))
    sufficient_at = int(config.get("sufficient_constituents", 5))
    concentrated_at = int(config.get("concentrated_constituents", 3))
    markets = deduplicate_markets(assets)
    results: list[BenchmarkResult] = []
    for benchmark_id, definition in definitions.items():
        requested = list(dict.fromkeys(str(s).upper() for s in definition.get("symbols", [])))
        chosen = [markets[symbol] for symbol in requested if symbol in markets]
        available = [asset.canonical_symbol.upper() for asset in chosen]
        missing = [symbol for symbol in requested if symbol not in markets]
        count = len(chosen)
        status: Literal["sufficient", "concentrated", "insufficient"] = (
            "sufficient"
            if count >= sufficient_at
            else "concentrated"
            if count >= concentrated_at
            else "insufficient"
        )
        warnings: list[str] = []
        if count and any(asset.volume_24h_usd is None for asset in chosen):
            warnings.append("Volume 24h unavailable for one or more constituents")
        results.append(
            BenchmarkResult(
                benchmark_id=str(benchmark_id),
                name=str(definition.get("name", benchmark_id)),
                status=status,
                requested_symbols=requested,
                available_symbols=available,
                missing_symbols=missing,
                unique_constituents=count,
                coverage_ratio=count / len(requested) if requested else 0,
                total_volume_24h_usd=sum(
                    (asset.volume_24h_usd or Decimal(0) for asset in chosen), Decimal(0)
                ),
                total_open_interest_usd=sum(
                    (asset.open_interest_usd or Decimal(0) for asset in chosen), Decimal(0)
                ),
                countries=sorted({asset.country or "Unclassified" for asset in chosen}),
                constituents=[
                    {
                        "symbol": asset.canonical_symbol,
                        "dex": asset.dex,
                        "country": asset.country,
                        "asset_class": asset.asset_class,
                        "volume_24h_usd": asset.volume_24h_usd,
                        "open_interest_usd": asset.open_interest_usd,
                        "mark_price": asset.mark_price,
                    }
                    for asset in chosen
                ],
                warnings=warnings,
            )
        )
    return sorted(results, key=lambda result: (-result.unique_constituents, result.name))


def export_benchmark_report(results: list[BenchmarkResult], output_dir: Path) -> None:
    atomic_json(
        output_dir / "sector_benchmark_report.json",
        [result.model_dump(mode="python") for result in results],
    )
    rows: list[dict[str, Any]] = []
    for result in results:
        rows.append(
            {
                "benchmark_id": result.benchmark_id,
                "name": result.name,
                "status": result.status,
                "unique_constituents": result.unique_constituents,
                "coverage_ratio": round(result.coverage_ratio, 4),
                "available_symbols": "|".join(result.available_symbols),
                "missing_symbols": "|".join(result.missing_symbols),
                "countries": "|".join(result.countries),
                "total_volume_24h_usd": result.total_volume_24h_usd,
                "total_open_interest_usd": result.total_open_interest_usd,
                "warnings": "|".join(result.warnings),
            }
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "sector_benchmark_report.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
