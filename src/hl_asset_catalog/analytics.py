from __future__ import annotations

import asyncio
import csv
import math
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .benchmark_engine import deduplicate_markets
from .hyperliquid_client import HyperliquidClient
from .models import Instrument, MarketAnalytics
from .statistics import (
    OrderBookMetrics,
    annualized_volatility,
    close_prices,
    correlation,
    historical_var_95,
    max_drawdown,
    order_book_metrics,
    period_return,
    simple_returns,
)
from .utils import atomic_json


def _liquidity_score(asset: Instrument, book: OrderBookMetrics) -> float:
    volume = float(asset.volume_24h_usd or 0)
    open_interest = float(asset.open_interest_usd or 0)
    depth = float(
        (book["bid_depth_10bps_usd"] or Decimal(0)) + (book["ask_depth_10bps_usd"] or Decimal(0))
    )
    spread = float(book.get("spread_bps") or 1000)
    slippages = [book.get("buy_slippage_10k_bps"), book.get("sell_slippage_10k_bps")]
    slippage_values = [float(value) for value in slippages if value is not None]
    slippage = sum(slippage_values) / len(slippage_values) if slippage_values else 1000
    activity = min(40.0, math.log10(1 + volume) * 5) + min(25.0, math.log10(1 + open_interest) * 3)
    book_score = min(20.0, math.log10(1 + depth) * 3)
    execution = max(0.0, 15.0 - min(10.0, spread / 2) - min(5.0, slippage / 5))
    return round(min(100.0, activity + book_score + execution), 2)


def _quality_score(observations: int, values: list[object | None], errors: list[str]) -> float:
    completeness = sum(value is not None for value in values) / len(values) if values else 0
    history = min(1.0, observations / 60)
    penalty = min(0.4, len(errors) * 0.1)
    return round(max(0.0, (completeness * 0.7 + history * 0.3 - penalty) * 100), 2)


async def analyze_markets(
    client: HyperliquidClient,
    assets: list[Instrument],
    *,
    lookback_days: int = 90,
    max_assets: int = 40,
    force_refresh: bool = False,
) -> tuple[list[MarketAnalytics], dict[str, dict[str, float | None]]]:
    markets = sorted(
        deduplicate_markets(assets).values(),
        key=lambda asset: (
            asset.volume_24h_usd or Decimal(0),
            asset.open_interest_usd or Decimal(0),
        ),
        reverse=True,
    )[:max_assets]
    end_time = int(time.time() * 1000)
    start_time = end_time - lookback_days * 86_400_000

    async def analyze(asset: Instrument) -> tuple[MarketAnalytics, list[float]]:
        errors: list[str] = []
        candles: list[dict[str, Any]] = []
        book: dict[str, Any] = {}
        try:
            candles, book = await asyncio.gather(
                client.candle_snapshot(
                    asset.exchange_symbol,
                    interval="1d",
                    start_time=start_time,
                    end_time=end_time,
                    force_refresh=force_refresh,
                ),
                client.l2_book(asset.exchange_symbol, force_refresh=force_refresh),
            )
        except Exception as exc:
            errors.append(str(exc))
        prices = close_prices(candles)
        returns = simple_returns(prices)
        book_metrics = order_book_metrics(book)
        volatility = annualized_volatility(returns)
        drawdown = max_drawdown(prices)
        value_at_risk = historical_var_95(returns)
        funding_annualized = (
            float(asset.funding_rate * Decimal(24 * 365 * 100))
            if asset.funding_rate is not None
            else None
        )
        return_1d = period_return(prices, 1)
        return_7d = period_return(prices, 7)
        return_30d = period_return(prices, 30)
        values: list[object | None] = [
            return_1d,
            return_7d,
            return_30d,
            volatility,
            drawdown,
            value_at_risk,
            book_metrics["spread_bps"],
            book_metrics["bid_depth_10bps_usd"],
            book_metrics["ask_depth_10bps_usd"],
        ]
        result = MarketAnalytics(
            instrument_id=asset.id,
            symbol=asset.canonical_symbol,
            dex=asset.dex,
            country=asset.country,
            asset_class=asset.asset_class,
            observations=len(prices),
            return_1d_pct=return_1d,
            return_7d_pct=return_7d,
            return_30d_pct=return_30d,
            annualized_volatility_pct=volatility,
            max_drawdown_pct=drawdown,
            historical_var_95_pct=value_at_risk,
            spread_bps=book_metrics["spread_bps"],
            bid_depth_10bps_usd=book_metrics["bid_depth_10bps_usd"],
            ask_depth_10bps_usd=book_metrics["ask_depth_10bps_usd"],
            buy_slippage_10k_bps=book_metrics["buy_slippage_10k_bps"],
            sell_slippage_10k_bps=book_metrics["sell_slippage_10k_bps"],
            volume_24h_usd=asset.volume_24h_usd,
            open_interest_usd=asset.open_interest_usd,
            funding_rate=asset.funding_rate,
            funding_annualized_pct=funding_annualized,
            liquidity_score=_liquidity_score(asset, book_metrics),
            data_quality_score=_quality_score(len(prices), values, errors),
            retrieved_at=datetime.now(UTC).isoformat(),
            errors=errors,
        )
        return result, returns

    pairs = await asyncio.gather(*(analyze(asset) for asset in markets))
    results = [pair[0] for pair in pairs]
    return_map = {pair[0].symbol: pair[1] for pair in pairs}
    correlations = {
        left: {right: correlation(return_map[left], return_map[right]) for right in return_map}
        for left in return_map
    }
    return results, correlations


def export_analytics(
    results: list[MarketAnalytics],
    correlations: dict[str, dict[str, float | None]],
    output_dir: Path,
) -> None:
    rows = [result.model_dump(mode="python") for result in results]
    atomic_json(output_dir / "market_analytics.json", rows)
    atomic_json(output_dir / "correlation_matrix.json", correlations)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "market_analytics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
