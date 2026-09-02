from decimal import Decimal
from pathlib import Path

import pytest

from hl_asset_catalog.models import Instrument
from hl_asset_catalog.parquet_export import export_parquet

pyarrow = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")


def test_parquet_round_trip_and_partition(tmp_path: Path) -> None:
    asset = Instrument(
        id="native:BTC",
        canonical_symbol="BTC",
        exchange_symbol="BTC",
        dex="native",
        market_type="perp",
        mark_price=Decimal("123.4500"),
        tags=["large-cap"],
    )
    path = export_parquet([asset], tmp_path, snapshot_date="2026-01-02")
    assert path == tmp_path / "snapshot_date=2026-01-02" / "catalog.parquet"
    row = pq.read_table(path).to_pylist()[0]
    assert row["mark_price"] == "123.4500"
    assert row["tags"] == '["large-cap"]'
