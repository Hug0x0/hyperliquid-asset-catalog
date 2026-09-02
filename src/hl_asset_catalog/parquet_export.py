from __future__ import annotations

import importlib
import json
import os
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import Instrument


def _scalar(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    return value


def parquet_rows(assets: list[Instrument]) -> list[dict[str, object]]:
    return [
        {key: _scalar(value) for key, value in asset.model_dump(mode="python").items()}
        for asset in assets
    ]


def export_parquet(
    assets: list[Instrument], output_dir: Path, *, snapshot_date: str | None = None
) -> Path:
    try:
        pa: Any = importlib.import_module("pyarrow")
        pq: Any = importlib.import_module("pyarrow.parquet")
    except ImportError as exc:
        raise RuntimeError("Parquet export requires: pip install '.[parquet]'") from exc
    partition = snapshot_date or datetime.now().date().isoformat()
    destination = output_dir / f"snapshot_date={partition}" / "catalog.parquet"
    destination.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(parquet_rows(assets))
    descriptor, temporary_name = tempfile.mkstemp(dir=destination.parent, suffix=".parquet.tmp")
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        pq.write_table(table, temporary, compression="zstd")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination
