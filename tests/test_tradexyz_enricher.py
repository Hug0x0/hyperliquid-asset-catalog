from hl_asset_catalog.models import Instrument
from hl_asset_catalog.tradexyz_enricher import TradeXYZEnricher, parse_tables


def test_header_based_parser_and_enrichment() -> None:
    rows, warnings = parse_tables(
        "<table><tr><th>Exchange</th><th>Symbol</th><th>Name</th></tr>"
        "<tr><td>NASDAQ</td><td>NVDA</td><td>Nvidia</td></tr></table>"
    )
    assert warnings == []
    asset = Instrument(
        id="xyz:NVDA",
        canonical_symbol="NVDA",
        exchange_symbol="xyz:NVDA",
        dex="xyz",
        market_type="perp",
    )
    result = TradeXYZEnricher().enrich([asset], rows)
    assert result[0].display_name == "Nvidia"
    assert result[0].reference_exchange == "NASDAQ"
    assert "tradexyz_docs" in result[0].source


def test_parser_warns_when_structure_changes() -> None:
    rows, warnings = parse_tables("<table><tr><th>Ticker</th></tr></table>")
    assert rows == []
    assert warnings
