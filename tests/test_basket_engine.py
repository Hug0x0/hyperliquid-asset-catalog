from pathlib import Path

import yaml

from hl_asset_catalog.basket_engine import build_baskets
from hl_asset_catalog.models import Instrument


def test_equal_weights_sum_exactly_one(tmp_path: Path) -> None:
    config = {
        "baskets": {
            "x": {
                "name": "X",
                "selection": {"symbols": ["A", "B", "C"]},
                "weighting": "equal",
                "minimum_constituents": 2,
            }
        }
    }
    path = tmp_path / "baskets.yaml"
    path.write_text(yaml.safe_dump(config))
    assets = [
        Instrument(
            id=s,
            canonical_symbol=s,
            exchange_symbol=s,
            dex="native",
            market_type="perp",
            is_active=True,
        )
        for s in "ABC"
    ]
    result = build_baskets(assets, path)[0]
    assert result.status == "available"
    assert sum(result.suggested_weights.values()) == 1.0
