from pathlib import Path

from hl_asset_catalog.classification import Classifier
from hl_asset_catalog.models import Instrument

RULES = Path(__file__).parents[1] / "config/classification_rules.yaml"


def test_manual_xyz_equity_classification() -> None:
    asset = Instrument(
        id="x", canonical_symbol="NVDA", exchange_symbol="xyz:NVDA", dex="xyz", market_type="perp"
    )
    classified = Classifier(RULES).classify(asset)
    assert classified.asset_class == "equity"
    assert "semiconductors" in classified.tags


def test_native_defaults_to_crypto() -> None:
    asset = Instrument(
        id="x", canonical_symbol="NEW", exchange_symbol="NEW", dex="native", market_type="perp"
    )
    assert Classifier(RULES).classify(asset).asset_class == "crypto"


def test_country_and_tradfi_group_classification() -> None:
    asset = Instrument(
        id="x", canonical_symbol="TSM", exchange_symbol="xyz:TSM", dex="xyz", market_type="perp"
    )
    classified = Classifier(RULES).classify(asset)
    assert classified.asset_class == "equity"
    assert classified.country == "Taiwan"
    assert classified.country_code == "TW"
