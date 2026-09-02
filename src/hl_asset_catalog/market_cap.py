from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Instrument


def enrich_market_caps(
    assets: list[Instrument],
    source_path: Path,
    *,
    source_name: str,
    license_url: str,
) -> list[Instrument]:
    if not source_name.strip() or not license_url.startswith(("https://", "http://")):
        raise ValueError("source name and an HTTP(S) license URL are required")
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("market-cap source must be an object keyed by exact instrument ID")
    retrieved_at = datetime.now(UTC).isoformat()
    enriched: list[Instrument] = []
    for asset in assets:
        raw_value = payload.get(asset.id)
        if raw_value is None:
            enriched.append(asset)
            continue
        try:
            value = Decimal(str(raw_value))
        except InvalidOperation as exc:
            raise ValueError(f"invalid market cap for {asset.id}") from exc
        if value <= 0:
            raise ValueError(f"market cap must be positive for {asset.id}")
        enriched.append(
            asset.model_copy(
                update={
                    "market_cap_usd": value,
                    "market_cap_source": source_name,
                    "market_cap_license_url": license_url,
                    "market_cap_retrieved_at": retrieved_at,
                }
            )
        )
    return enriched
