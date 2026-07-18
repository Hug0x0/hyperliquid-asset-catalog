from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def decimal_or_none(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def cache_key(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(f"Not JSON serializable: {type(value)!r}")


def atomic_json(path: Path, data: object, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, default=json_default, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def hip3_asset_id(perp_dex_index: int, index_in_meta: int) -> int:
    if perp_dex_index < 1 or index_in_meta < 0 or index_in_meta >= 10_000:
        raise ValueError("Invalid HIP-3 index")
    return 100_000 + perp_dex_index * 10_000 + index_in_meta
