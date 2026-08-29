from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from pathlib import Path
from typing import Literal

from .config import load_yaml
from .models import BasketResult, Instrument


def _weights(assets: list[Instrument], method: str) -> tuple[dict[str, float], list[str]]:
    if not assets:
        return {}, []
    warnings: list[str] = []
    if method == "equal":
        raw = [Decimal(1) for _ in assets]
    elif method == "liquidity":
        raw = [asset.volume_24h_usd or Decimal(0) for asset in assets]
    elif method == "open_interest":
        raw = [asset.open_interest_usd or Decimal(0) for asset in assets]
    elif method in {"market_cap", "inverse_volatility"}:
        return {}, [f"{method} requires a configured reliable data source"]
    else:
        return {}, [f"Unknown weighting method: {method}"]
    total = sum(raw)
    if total <= 0:
        raw = [Decimal(1) for _ in assets]
        total = Decimal(len(assets))
        warnings.append(f"Missing {method} data; equal weights used")
    quantum = Decimal("0.00000001")
    rounded = [(value / total).quantize(quantum, rounding=ROUND_DOWN) for value in raw]
    rounded[-1] = Decimal(1) - sum(rounded[:-1])
    return {
        asset.canonical_symbol: float(weight) for asset, weight in zip(assets, rounded, strict=True)
    }, warnings


def build_baskets(assets: list[Instrument], definitions_path: Path) -> list[BasketResult]:
    definitions = dict(load_yaml(definitions_path).get("baskets", {}))
    active = [asset for asset in assets if asset.is_active]
    results: list[BasketResult] = []
    for basket_id, definition in definitions.items():
        selection = definition.get("selection", {})
        requested = [str(s).upper() for s in selection.get("symbols", [])]
        tags = set(selection.get("tags", []))
        chosen: list[Instrument] = []
        for symbol in requested:
            matches = [a for a in active if a.canonical_symbol.upper() == symbol]
            if matches:
                chosen.append(
                    sorted(matches, key=lambda a: (a.dex != "xyz", a.market_type != "perp"))[0]
                )
        if tags:
            for asset in active:
                if tags.intersection(asset.tags) and asset.id not in {a.id for a in chosen}:
                    chosen.append(asset)
            requested = sorted(set(requested) | {a.canonical_symbol for a in chosen})
        available = [a.canonical_symbol for a in chosen]
        missing = [s for s in requested if s not in {a.upper() for a in available}]
        minimum = int(definition.get("minimum_constituents", len(requested)))
        status: Literal["available", "partial", "unavailable"] = (
            "available"
            if not missing and chosen
            else "partial"
            if len(chosen) >= minimum
            else "unavailable"
        )
        method = str(definition.get("weighting", "equal"))
        weights, warnings = _weights(chosen, method)
        results.append(
            BasketResult(
                basket_id=str(basket_id),
                name=str(definition.get("name", basket_id)),
                status=status,
                requested_symbols=requested,
                available_symbols=available,
                missing_symbols=missing,
                coverage_ratio=len(chosen) / len(requested) if requested else 0,
                constituents=[
                    {"id": a.id, "symbol": a.canonical_symbol, "dex": a.dex} for a in chosen
                ],
                weighting_method=method,
                suggested_weights=weights,
                warnings=warnings,
            )
        )
    return results
