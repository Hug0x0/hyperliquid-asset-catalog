from __future__ import annotations

from decimal import Decimal
from typing import Any

from .models import Instrument
from .utils import decimal_or_none, hip3_asset_id

API_URL = "https://api.hyperliquid.xyz/info"


def _price_change(mark: Decimal | None, previous: Decimal | None) -> Decimal | None:
    return (
        ((mark - previous) / previous * 100)
        if mark is not None and previous not in (None, 0)
        else None
    )


def normalize_perp(
    meta: dict[str, Any], ctx: dict[str, Any], *, dex: str, dex_index: int, index: int
) -> Instrument:
    exchange_symbol = str(meta["name"])
    symbol = exchange_symbol.split(":", 1)[-1]
    is_native = dex == ""
    mark = decimal_or_none(ctx.get("markPx"))
    previous = decimal_or_none(ctx.get("prevDayPx"))
    oi = decimal_or_none(ctx.get("openInterest"))
    delisted = bool(meta.get("isDelisted", False))
    aid = index if is_native else hip3_asset_id(dex_index, index)
    return Instrument(
        id=f"perp:{'native' if is_native else dex}:{symbol}",
        canonical_symbol=symbol,
        exchange_symbol=exchange_symbol,
        dex="native" if is_native else dex,
        market_type="perp",
        quote_currency="USDC",
        asset_id=aid,
        index_in_meta=index,
        perp_dex_index=None if is_native else dex_index,
        sz_decimals=meta.get("szDecimals"),
        max_leverage=decimal_or_none(meta.get("maxLeverage")),
        margin_mode=meta.get("marginMode", "cross" if is_native else "isolated"),
        mark_price=mark,
        oracle_price=decimal_or_none(ctx.get("oraclePx")),
        mid_price=decimal_or_none(ctx.get("midPx")),
        funding_rate=decimal_or_none(ctx.get("funding")),
        open_interest=oi,
        open_interest_usd=oi * mark if oi is not None and mark is not None else None,
        volume_24h_usd=decimal_or_none(ctx.get("dayNtlVlm")),
        previous_day_price=previous,
        price_change_24h_pct=_price_change(mark, previous),
        is_active=not delisted and mark is not None,
        is_delisted=delisted,
        source_urls=[API_URL],
        raw_metadata={"meta": meta, "context": ctx},
    )


def normalize_spot(
    market: dict[str, Any], ctx: dict[str, Any], tokens: dict[int, dict[str, Any]]
) -> Instrument:
    token_ids = market.get("tokens", [])
    base = tokens.get(token_ids[0], {}) if token_ids else {}
    quote = tokens.get(token_ids[1], {}) if len(token_ids) > 1 else {}
    name = str(market.get("name", f"@{market.get('index')}"))
    display = f"{base.get('name', name)}/{quote.get('name', 'USDC')}"
    mark = decimal_or_none(ctx.get("markPx") or ctx.get("midPx"))
    previous = decimal_or_none(ctx.get("prevDayPx"))
    return Instrument(
        id=f"spot:{market.get('index')}:{display}",
        canonical_symbol=display,
        exchange_symbol=name,
        display_name=base.get("fullName") or display,
        dex="spot",
        market_type="spot",
        quote_currency=quote.get("name"),
        underlying_symbol=base.get("name"),
        asset_id=10_000 + int(market.get("index", 0)),
        index_in_meta=market.get("index"),
        sz_decimals=base.get("szDecimals"),
        mark_price=mark,
        oracle_price=decimal_or_none(ctx.get("oraclePx")),
        mid_price=decimal_or_none(ctx.get("midPx")),
        volume_24h_usd=decimal_or_none(ctx.get("dayNtlVlm")),
        previous_day_price=previous,
        price_change_24h_pct=_price_change(mark, previous),
        is_active=mark is not None,
        source_urls=[API_URL],
        raw_metadata={"market": market, "base_token": base, "context": ctx},
    )
