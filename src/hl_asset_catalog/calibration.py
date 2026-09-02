from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SCORE_VERSION


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    for rank, index in enumerate(order, start=1):
        ranks[index] = float(rank)
    return ranks


def rank_correlation(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("rank correlation requires equal series with at least two values")
    x, y = _ranks(left), _ranks(right)
    mean_x = sum(x) / len(x)
    mean_y = sum(y) / len(y)
    numerator = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
    denominator = (sum((a - mean_x) ** 2 for a in x) * sum((b - mean_y) ** 2 for b in y)) ** 0.5
    return numerator / denominator if denominator else 0.0


def evaluate_calibration(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or len(cases) < 2:
        raise ValueError("calibration fixture must contain at least two cases")
    expected = [float(case["expected_rank"]) for case in cases]
    liquidity = [float(case["liquidity_score"]) for case in cases]
    quality = [float(case["data_quality_score"]) for case in cases]
    combined = [(a + b) / 2 for a, b in zip(liquidity, quality, strict=True)]
    return {
        "schema_version": "1.0",
        "score_version": SCORE_VERSION,
        "cases": len(cases),
        "rank_correlation": round(rank_correlation(expected, combined), 6),
        "bounds_valid": all(0 <= value <= 100 for value in liquidity + quality),
        "missing_data_monotonic": all(
            quality[index] <= quality[index + 1] for index in range(len(quality) - 1)
        ),
    }
