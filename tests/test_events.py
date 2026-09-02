import json
from pathlib import Path

import pytest

from hl_asset_catalog.events import diff_catalogs, load_snapshot


def test_diff_catalogs_covers_event_types_and_is_idempotent() -> None:
    old = [
        {"id": "gone", "asset_class": "equity", "value": 1},
        {"id": "class", "asset_class": "unknown", "value": 1},
        {"id": "meta", "asset_class": "equity", "value": 1},
    ]
    new = [
        {"id": "new", "asset_class": "equity", "value": 1},
        {"id": "class", "asset_class": "equity", "value": 1},
        {"id": "meta", "asset_class": "equity", "value": 2},
    ]
    first = diff_catalogs(old, new, observed_at="2026-01-01T00:00:00+00:00")
    second = diff_catalogs(old, new, observed_at="2026-01-01T00:00:00+00:00")
    assert first == second
    assert {event["event_type"] for event in first} == {
        "listing",
        "delisting",
        "classification_change",
        "metadata_change",
    }


def test_load_snapshot_rejects_malformed_input(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"id": "not-an-array"}), encoding="utf-8")
    with pytest.raises(ValueError, match="array of objects"):
        load_snapshot(path)
