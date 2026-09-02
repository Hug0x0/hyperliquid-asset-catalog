from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _identity(row: dict[str, Any]) -> str:
    value = row.get("id")
    if not isinstance(value, str) or not value:
        raise ValueError("every catalog row must contain a non-empty string id")
    return value


def _event_id(asset_id: str, event_type: str, before: object, after: object) -> str:
    payload = json.dumps(
        [asset_id, event_type, before, after], sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def diff_catalogs(
    previous: list[dict[str, Any]],
    current: list[dict[str, Any]],
    *,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = observed_at or datetime.now(UTC).isoformat()
    old = {_identity(row): row for row in previous}
    new = {_identity(row): row for row in current}
    events: list[dict[str, Any]] = []
    for asset_id in sorted(old.keys() | new.keys()):
        before = old.get(asset_id)
        after = new.get(asset_id)
        if before is None:
            event_type = "listing"
        elif after is None:
            event_type = "delisting"
        elif before == after:
            continue
        elif before.get("asset_class") != after.get("asset_class"):
            event_type = "classification_change"
        else:
            event_type = "metadata_change"
        events.append(
            {
                "schema_version": "1.0",
                "event_id": _event_id(asset_id, event_type, before, after),
                "observed_at": timestamp,
                "asset_id": asset_id,
                "event_type": event_type,
                "before": before,
                "after": after,
                "source": "catalog_snapshot_diff",
            }
        )
    return events


def load_snapshot(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read snapshot {path}: {exc}") from exc
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError(f"snapshot {path} must be an array of objects")
    return data
