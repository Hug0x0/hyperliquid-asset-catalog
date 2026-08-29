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
from .models import SCHEMA_VERSION, Instrument, MarketAnalytics
from .statistics import (
    OrderBookMetrics,
    annualized_volatility,
    close_prices,
    dated_correlation,
    historical_var_95,
    max_drawdown,
    order_book_metrics,
    period_return,
    session_returns,
    simple_returns,
)
from .utils import atomic_json, decimal_or_none


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


def _market_anomalies(
    asset: Instrument,
    candles: list[dict[str, Any]],
    book: dict[str, Any],
    book_metrics: OrderBookMetrics,
    *,
    now_ms: int,
    oracle_divergence_bps: float,
    abnormal_spread_bps: float,
    stale_candle_hours: float,
) -> tuple[float | None, list[str]]:
    anomalies: list[str] = []
    divergence: float | None = None
    if asset.mark_price and asset.oracle_price and asset.oracle_price > 0:
        divergence = float(abs(asset.mark_price / asset.oracle_price - 1) * Decimal(10_000))
        if divergence > oracle_divergence_bps:
            anomalies.append("mark_oracle_divergence")
    levels = book.get("levels", [])
    bids = levels[0] if isinstance(levels, list) and len(levels) > 0 else []
    asks = levels[1] if isinstance(levels, list) and len(levels) > 1 else []
    if not bids or not asks:
        anomalies.append("empty_order_book")
    else:
        best_bid = decimal_or_none(bids[0].get("px"))
        best_ask = decimal_or_none(asks[0].get("px"))
        if best_bid is not None and best_ask is not None and best_bid >= best_ask:
            anomalies.append("crossed_order_book")
    if book_metrics["spread_bps"] is not None and book_metrics["spread_bps"] > abnormal_spread_bps:
        anomalies.append("abnormal_spread")
    timestamps = [int(item["t"]) for item in candles if isinstance(item.get("t"), int)]
    if not timestamps or now_ms - max(timestamps) > stale_candle_hours * 3_600_000:
        anomalies.append("stale_candle_data")
    return divergence, anomalies


async def analyze_markets(
    client: HyperliquidClient,
    assets: list[Instrument],
    *,
    lookback_days: int = 90,
    max_assets: int = 40,
    force_refresh: bool = False,
) -> tuple[
    list[MarketAnalytics],
    dict[str, dict[str, float | None]],
    dict[str, dict[str, int]],
]:
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

    async def analyze(index: int, asset: Instrument) -> tuple[MarketAnalytics, dict[str, float]]:
        await client.analytics_jitter(index)
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
        divergence, anomalies = _market_anomalies(
            asset,
            candles,
            book,
            book_metrics,
            now_ms=end_time,
            oracle_divergence_bps=client.settings.oracle_divergence_bps,
            abnormal_spread_bps=client.settings.abnormal_spread_bps,
            stale_candle_hours=client.settings.stale_candle_hours,
        )
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
            data_quality_score=_quality_score(len(prices), values, errors + anomalies),
            mark_oracle_divergence_bps=divergence,
            anomalies=anomalies,
            retrieved_at=datetime.now(UTC).isoformat(),
            errors=errors,
        )
        return result, session_returns(candles, is_24_7=asset.is_24_7, country=asset.country)

    pairs = await asyncio.gather(*(analyze(index, asset) for index, asset in enumerate(markets)))
    results = [pair[0] for pair in pairs]
    return_map = {pair[0].symbol: pair[1] for pair in pairs}
    correlations: dict[str, dict[str, float | None]] = {}
    correlation_observations: dict[str, dict[str, int]] = {}
    for left, left_series in return_map.items():
        correlations[left] = {}
        correlation_observations[left] = {}
        for right, right_series in return_map.items():
            value, observations = dated_correlation(left_series, right_series)
            correlations[left][right] = value
            correlation_observations[left][right] = observations
    return results, correlations, correlation_observations


def export_analytics(
    results: list[MarketAnalytics],
    correlations: dict[str, dict[str, float | None]],
    correlation_observations: dict[str, dict[str, int]],
    output_dir: Path,
) -> None:
    rows = [result.model_dump(mode="python") for result in results]
    atomic_json(output_dir / "market_analytics.json", rows)
    atomic_json(
        output_dir / "correlation_matrix.json",
        {"schema_version": SCHEMA_VERSION, "data": correlations},
    )
    atomic_json(
        output_dir / "correlation_observations.json",
        {"schema_version": SCHEMA_VERSION, "data": correlation_observations},
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "market_analytics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
