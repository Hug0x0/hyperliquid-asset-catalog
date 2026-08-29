import json
from pathlib import Path

from jsonschema import Draft202012Validator

from hl_asset_catalog.models import Instrument, MarketAnalytics

SCHEMAS = Path(__file__).parents[1] / "schemas"


def schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMAS / name).read_text())


def test_catalog_schema_accepts_current_model() -> None:
    asset = Instrument(
        id="native:BTC",
        canonical_symbol="BTC",
        exchange_symbol="BTC",
        dex="native",
        market_type="perp",
        asset_class="crypto",
    )
    Draft202012Validator(schema("catalog.schema.json")).validate([asset.model_dump(mode="json")])


def test_analytics_schema_accepts_current_model() -> None:
    row = MarketAnalytics(
        instrument_id="native:BTC",
        symbol="BTC",
        dex="native",
        asset_class="crypto",
        observations=30,
        liquidity_score=80,
        data_quality_score=90,
        retrieved_at="2026-01-01T00:00:00Z",
    )
    Draft202012Validator(schema("analytics.schema.json")).validate([row.model_dump(mode="json")])


def test_schema_version_rejects_incompatible_fixture() -> None:
    validator = Draft202012Validator(schema("catalog.schema.json"))
    errors = list(validator.iter_errors([{"schema_version": "2.0"}]))
    assert errors
