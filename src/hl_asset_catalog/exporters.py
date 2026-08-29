from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .models import Instrument, RunReport
from .utils import atomic_json, json_default


def serialized(assets: list[Instrument], *, include_raw: bool = True) -> list[dict[str, Any]]:
    rows = [asset.model_dump(mode="python") for asset in assets]
    if not include_raw:
        for row in rows:
            row["raw_metadata"] = {}
    return rows


def catalog_diff(previous: list[dict[str, Any]], current: list[dict[str, Any]]) -> dict[str, Any]:
    old = {str(item["id"]): item for item in previous}
    new = {str(item["id"]): item for item in current}
    changed: list[dict[str, Any]] = []
    keys = (
        "is_delisted",
        "max_leverage",
        "margin_mode",
        "trading_hours",
        "asset_class",
        "subcategory",
    )
    for asset_id in old.keys() & new.keys():
        fields = {
            key: {"old": old[asset_id].get(key), "new": new[asset_id].get(key)}
            for key in keys
            if old[asset_id].get(key) != new[asset_id].get(key)
        }
        if fields:
            changed.append({"id": asset_id, "fields": fields})
    return {
        "new_markets": sorted(new.keys() - old.keys()),
        "removed_markets": sorted(old.keys() - new.keys()),
        "changed_markets": changed,
    }


def export_catalog(
    assets: list[Instrument], output_dir: Path, *, pretty: bool = True, include_raw: bool = True
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    current = serialized(assets, include_raw=include_raw)
    all_path = output_dir / "all_assets.json"
    previous: list[dict[str, Any]] = []
    if all_path.exists():
        loaded = json.loads(all_path.read_text(encoding="utf-8"))
        previous = loaded if isinstance(loaded, list) else []
    diff = catalog_diff(previous, current)
    non_crypto = [a for a in assets if a.asset_class not in {"crypto", "spot_crypto", "unknown"}]
    groups = {
        "all_assets.json": assets,
        "hyperliquid_native_perps.json": [a for a in assets if a.dex == "native"],
        "hip3_assets.json": [a for a in assets if a.market_type == "perp" and a.dex != "native"],
        "xyz_assets.json": [a for a in assets if a.dex == "xyz"],
        "spot_assets.json": [a for a in assets if a.market_type == "spot"],
        "tradfi_assets.json": non_crypto,
        "non_crypto_assets.json": non_crypto,
        "crypto_assets.json": [a for a in assets if a.asset_class in {"crypto", "spot_crypto"}],
        "unknown_assets.json": [a for a in assets if a.asset_class == "unknown"],
    }
    for filename, subset in groups.items():
        atomic_json(
            output_dir / filename, serialized(subset, include_raw=include_raw), pretty=pretty
        )
    by_country: dict[str, list[dict[str, Any]]] = {}
    for asset in non_crypto:
        country = asset.country or "Unclassified"
        by_country.setdefault(country, []).append(asset.model_dump(mode="python"))
    country_catalog = {
        country: {
            "count": len(items),
            "assets": sorted(items, key=lambda item: (item["canonical_symbol"], item["dex"])),
        }
        for country, items in sorted(by_country.items())
    }
    atomic_json(output_dir / "non_crypto_by_country.json", country_catalog, pretty=pretty)
    atomic_json(output_dir / "catalog_diff.json", diff, pretty=pretty)
    export_unknown_classification_report(assets, output_dir, pretty=pretty)
    rows = serialized(assets, include_raw=False)
    with (output_dir / "all_assets.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        k: "|".join(map(str, v))
                        if isinstance(v, list)
                        else json.dumps(v, default=json_default)
                        if isinstance(v, dict)
                        else v
                        for k, v in row.items()
                    }
                )
    non_crypto_rows = serialized(non_crypto, include_raw=False)
    with (output_dir / "non_crypto_assets.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(non_crypto_rows[0]) if non_crypto_rows else []
        )
        if non_crypto_rows:
            writer.writeheader()
            for row in non_crypto_rows:
                writer.writerow(
                    {
                        k: "|".join(map(str, v))
                        if isinstance(v, list)
                        else json.dumps(v, default=json_default)
                        if isinstance(v, dict)
                        else v
                        for k, v in row.items()
                    }
                )
    return diff


def export_unknown_classification_report(
    assets: list[Instrument], output_dir: Path, *, pretty: bool = True
) -> list[dict[str, Any]]:
    path = output_dir / "unknown_classification_report.json"
    previous: dict[str, dict[str, Any]] = {}
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            previous = {str(row.get("id")): row for row in loaded if isinstance(row, dict)}
    classified_symbols = {
        asset.canonical_symbol.upper() for asset in assets if asset.asset_class != "unknown"
    }
    rows: list[dict[str, Any]] = []
    for asset in sorted(
        (item for item in assets if item.asset_class == "unknown"),
        key=lambda item: (item.dex, item.canonical_symbol),
    ):
        symbol = asset.canonical_symbol.upper()
        clean = symbol.removeprefix("1000").removeprefix("K")
        old = previous.get(asset.id)
        status = "likely_alias" if clean in classified_symbols else "unknown" if old else "new"
        rows.append(
            {
                "id": asset.id,
                "symbol": asset.canonical_symbol,
                "dex": asset.dex,
                "triage_status": status,
                "likely_alias_of": clean if status == "likely_alias" else None,
                "volume_24h_usd": asset.volume_24h_usd,
                "open_interest_usd": asset.open_interest_usd,
                "first_seen_at": old.get("first_seen_at") if old else asset.retrieved_at,
                "retrieved_at": asset.retrieved_at,
            }
        )
    atomic_json(path, rows, pretty=pretty)
    csv_path = output_dir / "unknown_classification_report.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    return rows


def validate_catalog(assets: list[Instrument]) -> list[str]:
    report = validate_catalog_report(assets)
    return report["errors"] + report["warnings"]


def validate_catalog_report(assets: list[Instrument]) -> dict[str, list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for field in ("id", "exchange_symbol"):
        counts = Counter(getattr(a, field) for a in assets)
        errors.extend(f"Duplicate {field}: {value}" for value, count in counts.items() if count > 1)
    for asset in assets:
        if asset.mark_price is not None and asset.mark_price <= 0:
            errors.append(f"Non-positive price: {asset.id}")
        if asset.max_leverage is not None and asset.max_leverage <= 0:
            errors.append(f"Invalid leverage: {asset.id}")
        if asset.asset_class == "unknown":
            warnings.append(f"Unknown classification: {asset.id}")
    return {"errors": errors, "warnings": warnings}


def make_report(
    assets: list[Instrument],
    *,
    endpoints: list[str],
    request_count: int,
    errors: list[str],
    changes: dict[str, Any],
) -> RunReport:
    fields = Instrument.model_fields
    missing = {name: sum(getattr(a, name) is None for a in assets) for name in fields}
    return RunReport(
        retrieved_at=assets[0].retrieved_at,
        endpoints=endpoints,
        request_count=request_count,
        errors=errors,
        total_assets=len(assets),
        by_dex=dict(Counter(a.dex for a in assets)),
        by_asset_class=dict(Counter(a.asset_class for a in assets)),
        active_assets=sum(a.is_active for a in assets),
        delisted_assets=sum(a.is_delisted for a in assets),
        missing_fields=missing,
        changes=changes,
    )
