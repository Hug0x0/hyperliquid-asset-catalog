from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import httpx
import typer

from .analytics import analyze_markets, export_analytics
from .backtesting import backtest_benchmark, export_backtest
from .basket_engine import build_baskets as evaluate_baskets
from .benchmark_engine import build_sector_benchmarks, export_benchmark_report
from .calibration import evaluate_calibration
from .classification import Classifier
from .config import Settings
from .discovery import discover_catalog
from .doctor import doctor_exit_code, run_doctor
from .events import diff_catalogs, load_snapshot
from .exporters import export_catalog, make_report, validate_catalog_report
from .hyperliquid_client import HyperliquidClient
from .market_cap import enrich_market_caps
from .methodology import load_methodology
from .models import Instrument, MarketAnalytics
from .observability import configure_logging, log_summary
from .parquet_export import export_parquet
from .provenance import git_revision, write_analysis_manifest
from .reporting import benchmark_quality, export_benchmark_quality, generate_medium_article
from .tradexyz_enricher import TradeXYZEnricher
from .utils import atomic_json

app = typer.Typer(no_args_is_help=True, help="Read-only Hyperliquid asset catalog")
ROOT = Path(__file__).resolve().parents[2]


class MarketTypeOption(StrEnum):
    PERP = "perp"
    SPOT = "spot"


class AssetClassOption(StrEnum):
    CRYPTO = "crypto"
    EQUITY = "equity"
    EQUITY_INDEX = "equity_index"
    COMMODITY = "commodity"
    FOREX = "forex"
    INTEREST_RATE = "interest_rate"
    VOLATILITY_INDEX = "volatility_index"
    PRE_IPO = "pre_ipo"
    SPOT_CRYPTO = "spot_crypto"
    UNKNOWN = "unknown"


class OutputFormat(StrEnum):
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"


class QueryFormat(StrEnum):
    TABLE = "table"
    JSON = "json"
    JSONL = "jsonl"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class BacktestWeighting(StrEnum):
    EQUAL = "equal"
    LIQUIDITY = "liquidity"
    INVERSE_VOLATILITY = "inverse_volatility"


def _validate_writable_directory(path: Path, option_name: str) -> Path:
    if path.exists() and not path.is_dir():
        raise typer.BadParameter(f"{path} is not a directory", param_hint=option_name)
    probe = path
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    if not probe.is_dir() or not os.access(probe, os.W_OK):
        raise typer.BadParameter(f"{path} is not writable", param_hint=option_name)
    return path


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
def query(
    output_dir: Path = Path("output"),
    where: Annotated[list[str] | None, typer.Option("--where")] = None,
    sort_by: str = "id",
    descending: bool = False,
    fields: str = "id,canonical_symbol,dex,market_type,asset_class",
    limit: Annotated[int, typer.Option(min=0)] = 100,
    format: QueryFormat = QueryFormat.TABLE,
) -> None:
    """Filter and project a local catalog deterministically."""
    available = set(Instrument.model_fields)
    selected = [field.strip() for field in fields.split(",") if field.strip()]
    invalid = sorted((set(selected) | {sort_by}) - available)
    filters: list[tuple[str, str]] = []
    for expression in where or []:
        if "=" not in expression:
            raise typer.BadParameter("filters must use FIELD=VALUE", param_hint="--where")
        key, value = expression.split("=", 1)
        if key not in available:
            invalid.append(key)
        filters.append((key, value))
    if invalid:
        raise typer.BadParameter(f"unknown field(s): {', '.join(sorted(set(invalid)))}")
    rows = [asset.model_dump(mode="json") for asset in _load(output_dir)]
    rows = [
        row
        for row in rows
        if all(str(row.get(key, "")).lower() == value.lower() for key, value in filters)
    ]
    rows.sort(
        key=lambda row: (row.get(sort_by) is None, str(row.get(sort_by, ""))), reverse=descending
    )
    projected = [{key: row.get(key) for key in selected} for row in rows[:limit]]
    if format is QueryFormat.JSON:
        typer.echo(json.dumps(projected, indent=2, sort_keys=True))
    elif format is QueryFormat.JSONL:
        typer.echo("".join(json.dumps(row, sort_keys=True) + "\n" for row in projected), nl=False)
    else:
        typer.echo("\t".join(selected))
        for row in projected:
            typer.echo("\t".join("" if row[key] is None else str(row[key]) for key in selected))


@app.command()
def doctor(
    output_dir: Path = Path("output"),
    cache_dir: Path = Path(".cache/hl_asset_catalog"),
    json_output: Annotated[bool, typer.Option("--json")] = False,
    check_network: bool = False,
) -> None:
    """Run safe, read-only configuration and cache diagnostics."""
    report = run_doctor(
        ROOT,
        Settings(output_dir=output_dir, cache_dir=cache_dir),
        check_network=check_network,
    )
    if json_output:
        typer.echo(json.dumps(report, indent=2, sort_keys=True))
    else:
        for check in report["checks"]:
            typer.echo(f"{check['status'].upper():7} {check['name']}: {check['message']}")
    code = doctor_exit_code(report)
    if code:
        raise typer.Exit(code=code)


@app.command("diff-events")
def diff_events(
    previous: Path,
    current: Path,
    output: Path | None = None,
    observed_at: str | None = None,
) -> None:
    """Emit deterministic JSONL events between two catalog snapshots."""
    try:
        events = diff_catalogs(
            load_snapshot(previous), load_snapshot(current), observed_at=observed_at
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    payload = "".join(json.dumps(event, sort_keys=True, default=str) + "\n" for event in events)
    if output is None:
        typer.echo(payload, nl=False)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        typer.echo(f"Wrote {len(events)} events to {output}")


@app.command("calibrate-scores")
def calibrate_scores(
    fixture: Path = ROOT / "config/score_calibration.json",
    output: Path | None = None,
) -> None:
    """Evaluate deterministic score calibration and rank stability."""
    try:
        report = evaluate_calibration(fixture)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise typer.BadParameter(str(exc), param_hint="--fixture") from exc
    payload = json.dumps(report, indent=2, sort_keys=True)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload + "\n", encoding="utf-8")
    typer.echo(payload)
    if not report["bounds_valid"] or report["rank_correlation"] < 0.9:
        raise typer.Exit(code=1)


@app.command("enrich-market-caps")
def enrich_market_caps_command(
    source: Path,
    source_name: Annotated[str, typer.Option("--source-name")],
    license_url: Annotated[str, typer.Option("--license-url")],
    output_dir: Path = Path("output"),
) -> None:
    """Apply licensed market caps using exact catalog IDs only."""
    try:
        assets = enrich_market_caps(
            _load(output_dir), source, source_name=source_name, license_url=license_url
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise typer.BadParameter(str(exc), param_hint="source") from exc
    export_catalog(assets, output_dir)
    typer.echo(f"Enriched {sum(asset.market_cap_usd is not None for asset in assets)} assets")


@app.command("monitor-tradexyz-docs")
def monitor_tradexyz_docs(
    url: str,
    cache_dir: Path = Path(".cache/hl_asset_catalog/docs"),
    ttl_seconds: Annotated[int, typer.Option(min=60)] = 86_400,
) -> None:
    """Check the opt-in TradeXYZ documentation table contract."""
    try:
        result = TradeXYZEnricher(cache_dir).monitor(url, ttl_seconds=ttl_seconds)
    except (OSError, ValueError, PermissionError, httpx.HTTPError) as exc:
        raise typer.BadParameter(str(exc), param_hint="url") from exc
    typer.echo(json.dumps(result, indent=2, sort_keys=True))
    if result["warnings"]:
        raise typer.Exit(code=2)


@app.command()
def fetch(
    dex: str | None = None,
    market_type: MarketTypeOption | None = None,
    asset_class: AssetClassOption | None = None,
    tag: str | None = None,
    active_only: bool = False,
    output_dir: Path = Path("output"),
    cache_dir: Path = Path(".cache/hl_asset_catalog"),
    timeout: float = 20,
    max_retries: int = 4,
    concurrency: int = 4,
    pretty: bool = True,
    include_raw: bool = True,
    log_level: LogLevel = LogLevel.INFO,
    json_logs: Annotated[bool, typer.Option("--json-logs")] = False,
    force_refresh: bool = False,
) -> None:
    """Discover every DEX dynamically and write a normalized catalog."""
    output_dir = _validate_writable_directory(output_dir, "--output-dir")
    cache_dir = _validate_writable_directory(cache_dir, "--cache-dir")
    correlation_id = configure_logging(log_level.value, json_logs=json_logs)
    settings = Settings(
        output_dir=output_dir,
        cache_dir=cache_dir,
        timeout=timeout,
        max_retries=max_retries,
        concurrency=concurrency,
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
    log_summary(
        logging.getLogger("hl_asset_catalog.fetch"),
        operation="fetch",
        correlation_id=correlation_id,
        counts={
            "assets": len(filtered),
            "requests": client.request_count,
            "failures": len(errors) + len(client.errors),
        },
    )
    typer.echo(f"Wrote {len(filtered)} assets to {output_dir}")
    if errors or client.errors:
        raise typer.Exit(code=2)


@app.command("list-dexes")
def list_dexes(timeout: float = 20) -> None:
    async def run() -> list[str]:
        async with HyperliquidClient(Settings(timeout=timeout)) as client:
            return await client.perp_dexs()

    for index, dex in enumerate(asyncio.run(run())):
        typer.echo(f"{index}\t{dex or 'native'}")


@app.command()
def validate(
    output_dir: Path = Path("output"),
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit machine-readable findings")
    ] = False,
) -> None:
    report = validate_catalog_report(_load(output_dir))
    if json_output:
        typer.echo(json.dumps(report, indent=2, sort_keys=True))
    for error in report["errors"]:
        if not json_output:
            typer.echo(f"ERROR: {error}")
    for warning in report["warnings"]:
        if not json_output:
            typer.echo(f"WARNING: {warning}")
    if not json_output:
        typer.echo(
            f"Validation complete: {len(report['errors'])} error(s), "
            f"{len(report['warnings'])} warning(s)"
        )
    if report["errors"]:
        raise typer.Exit(code=1)


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
    cache_dir: Path = Path(".cache/hl_asset_catalog"),
    lookback_days: Annotated[int, typer.Option(min=30, max=365)] = 90,
    max_assets: Annotated[int, typer.Option(min=1, max=45)] = 40,
    timeout: float = 20,
    max_retries: int = 4,
    concurrency: Annotated[int, typer.Option(min=1, max=8)] = 4,
    force_refresh: bool = False,
) -> None:
    """Compute risk, liquidity, correlation and benchmark quality analytics."""
    assets = _load(output_dir)
    output_dir = _validate_writable_directory(output_dir, "--output-dir")
    cache_dir = _validate_writable_directory(cache_dir, "--cache-dir")
    started_at = datetime.now(UTC).isoformat()
    revision = git_revision(ROOT)
    settings = Settings(
        output_dir=output_dir,
        cache_dir=cache_dir,
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
        list[str],
        dict[str, int | float],
    ]:
        async with HyperliquidClient(settings) as client:
            results = await analyze_markets(
                client,
                assets,
                lookback_days=lookback_days,
                max_assets=max_assets,
                force_refresh=force_refresh,
            )
            return (
                *results,
                client.cache_hits,
                client.cache_corruptions,
                client.stale_cache_fallbacks,
                {
                    "request_weight": client.request_weight,
                    "rate_limit_responses": client.rate_limit_responses,
                    "retry_wait_seconds": round(client.retry_wait_seconds, 3),
                },
            )

    (
        analytics,
        correlations,
        correlation_observations,
        cache_hits,
        cache_corruptions,
        stale_fallbacks,
        network_metrics,
    ) = asyncio.run(run())
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
        cache_corruptions=cache_corruptions,
        stale_cache_fallbacks=stale_fallbacks,
        network_metrics=network_metrics,
    )
    typer.echo(
        f"Analyzed {len(analytics)} markets over {lookback_days} days; "
        f"wrote analytics and Medium report to {output_dir}"
    )


@app.command()
def export(
    format: Annotated[OutputFormat, typer.Option()] = OutputFormat.JSON,
    output_dir: Path = Path("output"),
    json_logs: Annotated[bool, typer.Option("--json-logs")] = False,
) -> None:
    started = time.perf_counter()
    correlation_id = configure_logging(LogLevel.INFO.value, json_logs=json_logs)
    output_dir = _validate_writable_directory(output_dir, "--output-dir")
    assets = _load(output_dir)
    if format is OutputFormat.PARQUET:
        try:
            path = export_parquet(assets, output_dir / "parquet")
        except RuntimeError as exc:
            raise typer.BadParameter(str(exc), param_hint="--format") from exc
        typer.echo(f"Exported parquet to {path}")
    else:
        export_catalog(assets, output_dir)
        typer.echo(f"Exported {format.value} to {output_dir}")
    log_summary(
        logging.getLogger("hl_asset_catalog.export"),
        operation="export",
        correlation_id=correlation_id,
        counts={
            "assets": len(assets),
            "failures": 0,
            "duration_seconds": round(time.perf_counter() - started, 6),
        },
    )


@app.command("backtest-benchmark")
def backtest_benchmark_command(
    history_path: Path,
    symbols: Annotated[list[str], typer.Option("--symbol")],
    output_path: Path = Path("output/benchmark_backtest.json"),
    weighting: BacktestWeighting = BacktestWeighting.EQUAL,
    rebalance_every: Annotated[int, typer.Option(min=1)] = 5,
    methodology_id: str | None = None,
    methodology_path: Path = ROOT / "config/benchmark_methodologies.yaml",
) -> None:
    """Backtest a benchmark from a local point-in-time history without look-ahead."""
    if not history_path.is_file():
        raise typer.BadParameter(f"{history_path} does not exist", param_hint="history_path")
    history = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(history, list):
        raise typer.BadParameter("history must be a JSON array", param_hint="history_path")
    try:
        methodology = load_methodology(methodology_path, methodology_id) if methodology_id else None
        result = backtest_benchmark(
            history,
            symbols=[symbol.upper() for symbol in symbols],
            weighting=weighting.value,
            rebalance_every=rebalance_every,
            methodology=methodology,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--methodology-id") from exc
    export_backtest(result, output_path)
    typer.echo(f"Wrote {result['observations']} backtest observations to {output_path}")


if __name__ == "__main__":
    app()
