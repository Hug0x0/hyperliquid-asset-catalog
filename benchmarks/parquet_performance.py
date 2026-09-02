"""Compare JSON and Parquet storage for a generated catalog fixture."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from hl_asset_catalog.models import Instrument
from hl_asset_catalog.parquet_export import export_parquet


def main() -> None:
    assets = [
        Instrument(
            id=f"native:S{i}",
            canonical_symbol=f"S{i}",
            exchange_symbol=f"S{i}",
            dex="native",
            market_type="perp",
        )
        for i in range(10_000)
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        started = time.perf_counter()
        payload = json.dumps([asset.model_dump(mode="json") for asset in assets])
        json_seconds = time.perf_counter() - started
        json_path = root / "catalog.json"
        json_path.write_text(payload, encoding="utf-8")
        started = time.perf_counter()
        parquet_path = export_parquet(assets, root)
        parquet_seconds = time.perf_counter() - started
        print(
            json.dumps(
                {
                    "json_bytes": json_path.stat().st_size,
                    "json_write_seconds": json_seconds,
                    "parquet_bytes": parquet_path.stat().st_size,
                    "parquet_write_seconds": parquet_seconds,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
