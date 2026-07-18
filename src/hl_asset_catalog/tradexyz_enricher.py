from __future__ import annotations

from collections.abc import Iterable

from .models import Instrument


class TradeXYZEnricher:
    """Conservative enrichment hook; API tradability always remains authoritative.

    TradeXYZ documentation URLs and structure are intentionally configurable rather than scraped
    by default. This prevents an undocumented HTML change from impacting catalog generation.
    """

    def enrich(self, assets: Iterable[Instrument]) -> list[Instrument]:
        return list(assets)
