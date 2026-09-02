import json
from pathlib import Path

from typer.testing import CliRunner

from hl_asset_catalog.cli import app
from hl_asset_catalog.models import Instrument

runner = CliRunner()


def test_fetch_rejects_invalid_market_type_before_network_access() -> None:
    result = runner.invoke(app, ["fetch", "--market-type", "option"])
    assert result.exit_code == 2
    assert "Invalid value" in result.output


def test_validate_supports_machine_readable_findings(tmp_path: Path) -> None:
    assets = [
        Instrument(
            id="unknown:ONE",
            canonical_symbol="ONE",
            exchange_symbol="ONE",
            dex="native",
            market_type="perp",
        )
    ]
    (tmp_path / "all_assets.json").write_text(
        json.dumps([asset.model_dump(mode="json") for asset in assets])
    )

    result = runner.invoke(app, ["validate", "--output-dir", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "errors": [],
        "warnings": ["Unknown classification: unknown:ONE"],
    }


def test_validate_returns_nonzero_for_catalog_errors(tmp_path: Path) -> None:
    asset = Instrument(
        id="duplicate",
        canonical_symbol="ONE",
        exchange_symbol="ONE",
        dex="native",
        market_type="perp",
    )
    (tmp_path / "all_assets.json").write_text(
        json.dumps([asset.model_dump(mode="json"), asset.model_dump(mode="json")])
    )

    result = runner.invoke(app, ["validate", "--output-dir", str(tmp_path), "--json"])

    assert result.exit_code == 1
    assert "Duplicate id: duplicate" in result.output


def test_query_filters_sorts_and_projects_json(tmp_path: Path) -> None:
    assets = [
        Instrument(
            id="b", canonical_symbol="B", exchange_symbol="B", dex="xyz", market_type="perp"
        ),
        Instrument(
            id="a", canonical_symbol="A", exchange_symbol="A", dex="native", market_type="perp"
        ),
    ]
    (tmp_path / "all_assets.json").write_text(
        json.dumps([asset.model_dump(mode="json") for asset in assets]), encoding="utf-8"
    )
    result = runner.invoke(
        app,
        [
            "query",
            "--output-dir",
            str(tmp_path),
            "--where",
            "market_type=perp",
            "--fields",
            "id,dex",
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == [{"dex": "native", "id": "a"}, {"dex": "xyz", "id": "b"}]


def test_query_rejects_unknown_field(tmp_path: Path) -> None:
    (tmp_path / "all_assets.json").write_text("[]", encoding="utf-8")
    result = runner.invoke(app, ["query", "--output-dir", str(tmp_path), "--fields", "nope"])
    assert result.exit_code == 2
    assert "unknown field" in result.output
