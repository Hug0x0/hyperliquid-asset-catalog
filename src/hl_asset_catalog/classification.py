from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import load_yaml
from .models import AssetClass, Instrument


class Classifier:
    def __init__(self, rules_path: Path):
        raw = load_yaml(rules_path)
        self.symbols: dict[str, dict[str, Any]] = {
            str(k).upper(): v for k, v in dict(raw.get("symbols", {})).items()
        }
        self.tag_groups: dict[str, set[str]] = {
            str(tag): {str(s).upper() for s in symbols}
            for tag, symbols in dict(raw.get("tag_groups", {})).items()
        }
        self.asset_class_groups: dict[str, set[str]] = {
            str(asset_class): {str(s).upper() for s in symbols}
            for asset_class, symbols in dict(raw.get("asset_class_groups", {})).items()
        }
        self.country_groups: dict[str, dict[str, Any]] = {
            str(country): value for country, value in dict(raw.get("country_groups", {})).items()
        }

    def classify(self, instrument: Instrument) -> Instrument:
        symbol = instrument.canonical_symbol.upper()
        clean = symbol.removeprefix("K") if symbol.startswith("K") else symbol
        manual = self.symbols.get(symbol, self.symbols.get(clean, {}))
        if manual:
            instrument.asset_class = manual.get("asset_class", instrument.asset_class)
            instrument.display_name = manual.get("display_name", instrument.display_name)
            instrument.subcategory = manual.get("subcategory", instrument.subcategory)
            instrument.country = manual.get("country", instrument.country)
            instrument.country_code = manual.get("country_code", instrument.country_code)
            instrument.underlying_symbol = manual.get(
                "underlying_symbol", instrument.underlying_symbol
            )
            instrument.reference_exchange = manual.get(
                "reference_exchange", instrument.reference_exchange
            )
            instrument.trading_hours = manual.get("trading_hours", instrument.trading_hours)
            instrument.is_24_7 = manual.get("is_24_7", instrument.is_24_7)
            instrument.is_pre_ipo = bool(manual.get("is_pre_ipo", instrument.is_pre_ipo))
            instrument.tags.extend(manual.get("tags", []))
        elif instrument.market_type == "spot":
            instrument.asset_class = "spot_crypto"
            instrument.is_24_7 = True
        elif instrument.dex == "native":
            instrument.asset_class = "crypto"
            instrument.is_24_7 = True
        elif any(token in symbol for token in ("USD", "EUR", "JPY", "GBP")) and "/" in symbol:
            instrument.asset_class = "forex"
        elif symbol in {"GOLD", "SILVER", "OIL", "COPPER", "NATGAS"}:
            instrument.asset_class = "commodity"
        elif symbol.endswith(("100", "500")):
            instrument.asset_class = "equity_index"
        if instrument.market_type == "perp" and instrument.dex != "native":
            for asset_class, symbols in self.asset_class_groups.items():
                if symbol in symbols:
                    instrument.asset_class = valid_asset_class(asset_class)
            for country, rule in self.country_groups.items():
                symbols = {str(s).upper() for s in rule.get("symbols", [])}
                if symbol in symbols:
                    instrument.country = country
                    instrument.country_code = rule.get("code")
        for tag, symbols in self.tag_groups.items():
            if symbol in symbols or clean in symbols:
                instrument.tags.append(tag)
        instrument.tags = sorted(set(instrument.tags))
        if instrument.is_pre_ipo:
            instrument.asset_class = "pre_ipo"
        if instrument.market_type == "spot":
            instrument.asset_class = "spot_crypto"
            instrument.country = None
            instrument.country_code = None
        elif instrument.dex == "native":
            instrument.asset_class = "crypto"
            instrument.is_pre_ipo = False
            instrument.country = None
            instrument.country_code = None
        return instrument


def valid_asset_class(value: str) -> AssetClass:
    allowed = {
        "crypto",
        "equity",
        "equity_index",
        "commodity",
        "forex",
        "interest_rate",
        "volatility_index",
        "pre_ipo",
        "spot_crypto",
        "unknown",
    }
    return value if value in allowed else "unknown"  # type: ignore[return-value]
