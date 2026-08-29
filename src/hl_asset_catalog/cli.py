from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from .analytics import analyze_markets, export_analytics
from .basket_engine import build_baskets as evaluate_baskets
from .benchmark_engine import build_sector_benchmarks, export_benchmark_report
from .classification import Classifier
from .config import Settings
from .discovery import discover_catalog
from .exporters import export_catalog, make_report, validate_catalog
from .hyperliquid_client import HyperliquidClient
from .models import Instrument, MarketAnalytics
from .provenance import git_revision, write_analysis_manifest
from .reporting import benchmark_quality, export_benchmark_quality, generate_medium_article
from .utils import atomic_json

app = typer.Typer(no_args_is_help=True, help="Read-only Hyperliquid asset catalog")
ROOT = Path(__file__).resolve().parents[2]


async def _fetch(
    settings: Settings, *, force_refresh: bool = False
) -> tuple[list[Instrument], HyperliquidClient, list[str]]:
    classifier = Classifier(ROOT / "config/classification_rules.yaml")
    client = HyperliquidClient(settings)
    async with client:
        assets, errors = await discover_catalog(client, classifier, force_refresh=force_refresh)
    return assets, client, errors


def _load(output_dir: Path) -> list[Instrument]:
    path = output_dir / "all_assets.json"
    if not path.exists():
        raise typer.BadParameter(f"{path} does not exist; run fetch first")
    return [
        Instrument.model_validate(item) for item in json.loads(path.read_text(encoding="utf-8"))
    ]


@app.command()
def fetch(
    dex: str | None = None,
    market_type: Annotated[str | None, typer.Option(help="perp or spot")] = None,
    asset_class: str | None = None,
    tag: str | None = None,
    active_only: bool = False,
    output_dir: Path = Path("output"),
    timeout: float = 20,
    max_retries: int = 4,
    concurrency: int = 4,
    pretty: bool = True,
    include_raw: bool = True,
    log_level: str = "INFO",
    force_refresh: bool = False,
) -> None:
    """Discover every DEX dynamically and write a normalized catalog."""
    logging.basicConfig(level=log_level.upper(), format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings(
        output_dir=output_dir, timeout=timeout, max_retries=max_retries, concurrency=concurrency
    )
    assets, client, errors = asyncio.run(_fetch(settings, force_refresh=force_refresh))
    filtered = [
        a
        for a in assets
        if (dex is None or a.dex == dex)
        and (market_type is None or a.market_type == market_type)
        and (asset_class is None or a.asset_class == asset_class)
        and (tag is None or tag in a.tags)
        and (not active_only or a.is_active)
    ]
    changes = export_catalog(filtered, output_dir, pretty=pretty, include_raw=include_raw)
    report = make_report(
        filtered,
        endpoints=sorted(client.endpoints),
        request_count=client.request_count,
        errors=client.errors + errors,
        changes=changes,
    )
    atomic_json(output_dir / "run_report.json", report.model_dump(mode="python"), pretty=pretty)
    typer.echo(f"Wrote {len(filtered)} assets to {output_dir}")


@app.command("list-dexes")
def list_dexes(timeout: float = 20) -> None:
    async def run() -> list[str]:
        async with HyperliquidClient(Settings(timeout=timeout)) as client:
            return await client.perp_dexs()

    for index, dex in enumerate(asyncio.run(run())):
        typer.echo(f"{index}\t{dex or 'native'}")


@app.command()
def validate(output_dir: Path = Path("output")) -> None:
    warnings = validate_catalog(_load(output_dir))
    for warning in warnings:
        typer.echo(f"WARNING: {warning}")
    typer.echo(f"Validation complete: {len(warnings)} warning(s)")


@app.command("build-baskets")
def build_baskets(output_dir: Path = Path("output")) -> None:
    results = evaluate_baskets(_load(output_dir), ROOT / "config/basket_definitions.yaml")
    available = [r.model_dump(mode="python") for r in results if r.status != "unavailable"]
    unavailable = [r.model_dump(mode="python") for r in results if r.status == "unavailable"]
    atomic_json(output_dir / "available_baskets.json", available)
    atomic_json(output_dir / "unavailable_baskets.json", unavailable)
    typer.echo(f"Built {len(results)} basket evaluations")


@app.command("build-benchmarks")
def build_benchmarks(output_dir: Path = Path("output")) -> None:
    """Evaluate deduplicated non-crypto sector benchmark depth."""
    results = build_sector_benchmarks(_load(output_dir), ROOT / "config/benchmark_definitions.yaml")
    export_benchmark_report(results, output_dir)
    counts = {
        status: sum(result.status == status for result in results)
        for status in ("sufficient", "concentrated", "insufficient")
    }
    typer.echo(
        f"Built {len(results)} benchmarks: {counts['sufficient']} sufficient, "
        f"{counts['concentrated']} concentrated, {counts['insufficient']} insufficient"
    )


@app.command("analyze-markets")
def analyze_market_data(
    output_dir: Path = Path("output"),
    lookback_days: Annotated[int, typer.Option(min=30, max=365)] = 90,
    max_assets: Annotated[int, typer.Option(min=1, max=45)] = 40,
    timeout: float = 20,
    max_retries: int = 4,
    concurrency: Annotated[int, typer.Option(min=1, max=8)] = 4,
    force_refresh: bool = False,
) -> None:
    """Compute risk, liquidity, correlation and benchmark quality analytics."""
    assets = _load(output_dir)
    started_at = datetime.now(UTC).isoformat()
    revision = git_revision(ROOT)
    settings = Settings(
        output_dir=output_dir,
        timeout=timeout,
        max_retries=max_retries,
        concurrency=concurrency,
    )

    async def run() -> tuple[
        list[MarketAnalytics],
        dict[str, dict[str, float | None]],
        dict[str, dict[str, int]],
        int,
        list[str],
    ]:
        async with HyperliquidClient(settings) as client:
            results = await analyze_markets(
                client,
                assets,
                lookback_days=lookback_days,
                max_assets=max_assets,
                force_refresh=force_refresh,
            )
            return (*results, client.cache_hits, client.stale_cache_fallbacks)

    analytics, correlations, correlation_observations, cache_hits, stale_fallbacks = asyncio.run(
        run()
    )
    export_analytics(analytics, correlations, correlation_observations, output_dir)
    benchmarks = build_sector_benchmarks(assets, ROOT / "config/benchmark_definitions.yaml")
    quality = benchmark_quality(benchmarks, analytics)
    export_benchmark_quality(quality, output_dir)
    non_crypto_count = sum(
        asset.asset_class not in {"crypto", "spot_crypto", "unknown"} for asset in assets
    )
    generate_medium_article(
        quality,
        analytics,
        assets,
        correlations,
        total_non_crypto=non_crypto_count,
        lookback_days=lookback_days,
        output_path=output_dir / "medium_analysis.md",
        git_commit=revision,
    )
    write_analysis_manifest(
        output_dir,
        root=ROOT,
        started_at=started_at,
        api_endpoint=settings.api_url,
        arguments={
            "lookback_days": lookback_days,
            "max_assets": max_assets,
            "timeout": timeout,
            "max_retries": max_retries,
            "concurrency": concurrency,
            "force_refresh": force_refresh,
        },
        cache_hits=cache_hits,
        stale_cache_fallbacks=stale_fallbacks,
    )
    typer.echo(
        f"Analyzed {len(analytics)} markets over {lookback_days} days; "
        f"wrote analytics and Medium report to {output_dir}"
    )


@app.command()
def export(
    format: Annotated[str, typer.Option()] = "json", output_dir: Path = Path("output")
) -> None:
    if format not in {"json", "csv"}:
        raise typer.BadParameter("format must be json or csv")
    export_catalog(_load(output_dir), output_dir)
    typer.echo(f"Exported {format} to {output_dir}")


if __name__ == "__main__":
    app()
