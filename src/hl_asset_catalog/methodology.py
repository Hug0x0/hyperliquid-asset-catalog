from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import load_yaml


def load_methodology(path: Path, methodology_id: str) -> dict[str, Any]:
    data = load_yaml(path)
    definitions = data.get("methodologies", {})
    if not isinstance(definitions, dict) or methodology_id not in definitions:
        raise ValueError(f"unknown methodology: {methodology_id}")
    raw = definitions[methodology_id]
    if not isinstance(raw, dict):
        raise ValueError("methodology must be a mapping")
    result = {"id": methodology_id, **raw}
    version = result.get("version")
    weighting = result.get("weighting")
    cap = result.get("max_weight")
    rebalance = result.get("rebalance_every_sessions")
    buffer = result.get("constituent_buffer")
    if not isinstance(version, str) or version.count(".") != 2:
        raise ValueError("methodology version must use semantic X.Y.Z form")
    if weighting not in {"equal", "liquidity", "inverse_volatility"}:
        raise ValueError("unsupported weighting rule")
    if not isinstance(rebalance, int) or rebalance < 1:
        raise ValueError("rebalance cadence must be positive")
    if not isinstance(buffer, int) or buffer < 0:
        raise ValueError("constituent buffer must be non-negative")
    if cap is not None and (not isinstance(cap, (float, int)) or not 0 < float(cap) <= 1):
        raise ValueError("max weight must be in (0, 1]")
    return result


def input_snapshot_id(history: list[dict[str, Any]]) -> str:
    payload = json.dumps(history, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def cap_weights(weights: dict[str, float], cap: float | None) -> dict[str, float]:
    if cap is None or not weights:
        return weights
    if cap * len(weights) < 1 - 1e-12:
        raise ValueError("max weight is infeasible for the constituent count")
    result = dict(weights)
    for _ in range(len(result)):
        excess = sum(max(0.0, value - cap) for value in result.values())
        if excess <= 1e-12:
            break
        capped = {symbol for symbol, value in result.items() if value >= cap}
        available = sum(result[symbol] for symbol in result if symbol not in capped)
        for symbol in capped:
            result[symbol] = cap
        if available:
            for symbol in result.keys() - capped:
                result[symbol] += excess * result[symbol] / available
    total = sum(result.values())
    return {symbol: value / total for symbol, value in result.items()}
