from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from hl_asset_catalog.models import Instrument
from hl_asset_catalog.parquet_export import export_parquet, parquet_rows


def sample_asset() -> Instrument:
    return Instrument(
        id="native:BTC",
        canonical_symbol="BTC",
        exchange_symbol="BTC",
        dex="native",
        market_type="perp",
        mark_price=Decimal("123.4500"),
        tags=["large-cap"],
    )


def test_parquet_rows_preserve_decimal_and_encode_collections() -> None:
    row = parquet_rows([sample_asset()])[0]
    assert row["mark_price"] == "123.4500"
    assert row["tags"] == '["large-cap"]'


def test_atomic_export_contract_without_optional_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_arrow = SimpleNamespace(Table=SimpleNamespace(from_pylist=lambda rows: rows))

    def write_table(table: object, path: Path, *, compression: str) -> None:
        assert table and compression == "zstd"
        path.write_bytes(b"PAR1")

    fake_parquet = SimpleNamespace(write_table=write_table)

    def fake_import(name: str) -> object:
        return fake_parquet if name == "pyarrow.parquet" else fake_arrow

    monkeypatch.setattr("hl_asset_catalog.parquet_export.importlib.import_module", fake_import)
    path = export_parquet([sample_asset()], tmp_path, snapshot_date="2026-01-02")
    assert path.read_bytes() == b"PAR1"


def test_parquet_round_trip_and_partition(tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    path = export_parquet([sample_asset()], tmp_path, snapshot_date="2026-01-02")
    assert path == tmp_path / "snapshot_date=2026-01-02" / "catalog.parquet"
    row = pq.read_table(path).to_pylist()[0]
    assert row["mark_price"] == "123.4500"
    assert row["tags"] == '["large-cap"]'
