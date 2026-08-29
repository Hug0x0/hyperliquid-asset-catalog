import json
from decimal import Decimal
from pathlib import Path

from hl_asset_catalog.exporters import export_unknown_classification_report
from hl_asset_catalog.models import Instrument


def instrument(symbol: str, asset_class: str = "unknown") -> Instrument:
    return Instrument(
        id=f"xyz:{symbol}",
        canonical_symbol=symbol,
        exchange_symbol=f"xyz:{symbol}",
        dex="xyz",
        market_type="perp",
        asset_class=asset_class,  # type: ignore[arg-type]
        volume_24h_usd=Decimal("100"),
        retrieved_at="2026-01-02T00:00:00Z",
    )


def test_unknown_report_preserves_first_seen_and_detects_alias(tmp_path: Path) -> None:
    previous = [
        {
            "id": "xyz:NEW",
            "first_seen_at": "2026-01-01T00:00:00Z",
        }
    ]
    (tmp_path / "unknown_classification_report.json").write_text(json.dumps(previous))

    rows = export_unknown_classification_report(
        [instrument("NEW"), instrument("1000PEPE"), instrument("PEPE", "crypto")], tmp_path
    )

    assert rows[0]["triage_status"] == "likely_alias"
    assert rows[0]["likely_alias_of"] == "PEPE"
    assert rows[1]["first_seen_at"] == "2026-01-01T00:00:00Z"
    assert rows[1]["triage_status"] == "unknown"
    assert (tmp_path / "unknown_classification_report.csv").is_file()
