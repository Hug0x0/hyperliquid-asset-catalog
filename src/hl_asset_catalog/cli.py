from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated

import typer

from .basket_engine import build_baskets as evaluate_baskets
from .classification import Classifier
from .config import Settings
from .discovery import discover_catalog
from .exporters import export_catalog, make_report, validate_catalog
from .hyperliquid_client import HyperliquidClient
from .models import Instrument
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
