from __future__ import annotations

import argparse
import csv
import io
import json
import time
import tracemalloc
from collections.abc import Callable
from pathlib import Path

from hl_asset_catalog.classification import Classifier
from hl_asset_catalog.exporters import serialized
from hl_asset_catalog.normalization import normalize_perp
from hl_asset_catalog.utils import json_default

ROOT = Path(__file__).parents[1]
INSTRUMENTS = 1_000
MAX_TOTAL_SECONDS = 5.0
MAX_PEAK_MIB = 128.0


def timed(function: Callable[[], object]) -> tuple[object, float]:
    started = time.perf_counter()
    result = function()
    return result, time.perf_counter() - started


def run_benchmark() -> dict[str, float | int]:
    tracemalloc.start()
    normalized, normalization_seconds = timed(
        lambda: [
            normalize_perp(
                {"name": f"bench:T{index}", "szDecimals": 2, "maxLeverage": 10},
                {"markPx": "100", "oraclePx": "100", "openInterest": "10"},
                dex="bench",
                dex_index=1,
                index=index,
            )
            for index in range(INSTRUMENTS)
        ]
    )
    assert isinstance(normalized, list)
    classifier = Classifier(ROOT / "config/classification_rules.yaml")
    classified, classification_seconds = timed(
        lambda: [classifier.classify(asset) for asset in normalized]
    )
    assert isinstance(classified, list)
    rows = serialized(classified, include_raw=False)
    _, json_seconds = timed(lambda: json.dumps(rows, default=json_default))

    def csv_export() -> str:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            {
                key: json.dumps(value, default=json_default)
                if isinstance(value, (dict, list))
                else value
                for key, value in row.items()
            }
            for row in rows
        )
        return output.getvalue()

    _, csv_seconds = timed(csv_export)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    total = normalization_seconds + classification_seconds + json_seconds + csv_seconds
    return {
        "instruments": INSTRUMENTS,
        "normalization_seconds": normalization_seconds,
        "classification_seconds": classification_seconds,
        "json_seconds": json_seconds,
        "csv_seconds": csv_seconds,
        "total_seconds": total,
        "peak_memory_mib": peak / 1024 / 1024,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when thresholds are exceeded")
    args = parser.parse_args()
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.check and (
        result["total_seconds"] > MAX_TOTAL_SECONDS or result["peak_memory_mib"] > MAX_PEAK_MIB
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
