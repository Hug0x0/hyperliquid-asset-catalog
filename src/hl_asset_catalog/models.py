from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AssetClass = Literal[
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
]


class Instrument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    canonical_symbol: str
    exchange_symbol: str
    display_name: str | None = None
    dex: str
    venue: str = "hyperliquid"
    market_type: Literal["perp", "spot"]
    asset_class: AssetClass = "unknown"
    subcategory: str | None = None
    tags: list[str] = Field(default_factory=list)
    quote_currency: str | None = None
    underlying_symbol: str | None = None
    reference_exchange: str | None = None
    asset_id: int | None = None
    index_in_meta: int | None = None
    perp_dex_index: int | None = None
    sz_decimals: int | None = None
    max_leverage: Decimal | None = None
    margin_mode: str | None = None
    mark_price: Decimal | None = None
    oracle_price: Decimal | None = None
    mid_price: Decimal | None = None
    funding_rate: Decimal | None = None
    open_interest: Decimal | None = None
    open_interest_usd: Decimal | None = None
    volume_24h_usd: Decimal | None = None
    previous_day_price: Decimal | None = None
    price_change_24h_pct: Decimal | None = None
    trading_hours: str | None = None
    is_24_7: bool | None = None
    is_active: bool = True
    is_delisted: bool = False
    is_pre_ipo: bool = False
    source: list[str] = Field(default_factory=lambda: ["hyperliquid_api"])
    source_urls: list[str] = Field(default_factory=list)
    retrieved_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class BasketResult(BaseModel):
    basket_id: str
    name: str
    status: Literal["available", "partial", "unavailable"]
    requested_symbols: list[str]
    available_symbols: list[str]
    missing_symbols: list[str]
    coverage_ratio: float
    constituents: list[dict[str, Any]]
    weighting_method: str
    suggested_weights: dict[str, float]
    warnings: list[str] = Field(default_factory=list)


class RunReport(BaseModel):
    retrieved_at: str
    endpoints: list[str]
    request_count: int
    errors: list[str]
    total_assets: int
    by_dex: dict[str, int]
    by_asset_class: dict[str, int]
    active_assets: int
    delisted_assets: int
    missing_fields: dict[str, int]
    changes: dict[str, Any] = Field(default_factory=dict)
