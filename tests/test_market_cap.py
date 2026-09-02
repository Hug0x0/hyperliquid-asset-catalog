import json
from decimal import Decimal
from pathlib import Path

import pytest

from hl_asset_catalog.market_cap import enrich_market_caps
from hl_asset_catalog.models import Instrument


def asset(identifier: str) -> Instrument:
    return Instrument(
        id=identifier,
        canonical_symbol="BTC",
        exchange_symbol="BTC",
        dex="native",
        market_type="perp",
    )


def test_market_cap_requires_exact_id_and_preserves_provenance(tmp_path: Path) -> None:
    source = tmp_path / "caps.json"
    source.write_text(json.dumps({"native:BTC": "1000.25", "BTC": 999}), encoding="utf-8")
    result = enrich_market_caps(
        [asset("native:BTC"), asset("xyz:BTC")],
        source,
        source_name="Licensed Feed",
        license_url="https://provider.test/license",
    )
    assert result[0].market_cap_usd == Decimal("1000.25")
    assert result[0].market_cap_source == "Licensed Feed"
    assert result[1].market_cap_usd is None


def test_market_cap_rejects_missing_license(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="license"):
        enrich_market_caps([asset("native:BTC")], tmp_path, source_name="feed", license_url="")
