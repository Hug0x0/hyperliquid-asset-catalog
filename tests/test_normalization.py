from decimal import Decimal

from hl_asset_catalog.normalization import normalize_perp, normalize_spot


def test_normalize_hip3_perp() -> None:
    asset = normalize_perp(
        {"name": "xyz:NVDA", "szDecimals": 3, "maxLeverage": 20},
        {"markPx": "100", "oraclePx": "99", "openInterest": "2", "prevDayPx": "80"},
        dex="xyz",
        dex_index=2,
        index=4,
    )
    assert asset.asset_id == 120_004
    assert asset.canonical_symbol == "NVDA"
    assert asset.open_interest_usd == Decimal("200")
    assert asset.price_change_24h_pct == Decimal("25")


def test_normalize_spot_resolves_token_names() -> None:
    asset = normalize_spot(
        {"name": "@1", "index": 1, "tokens": [2, 0]},
        {"midPx": "2"},
        {0: {"name": "USDC", "szDecimals": 8}, 2: {"name": "HFUN", "szDecimals": 2}},
    )
    assert asset.canonical_symbol == "HFUN/USDC"
    assert asset.asset_class == "unknown"
