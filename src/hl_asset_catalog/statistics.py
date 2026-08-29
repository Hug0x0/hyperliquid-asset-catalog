from __future__ import annotations

import math
from collections.abc import Hashable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

from .utils import decimal_or_none


class OrderBookMetrics(TypedDict):
    spread_bps: float | None
    bid_depth_10bps_usd: Decimal | None
    ask_depth_10bps_usd: Decimal | None
    buy_slippage_10k_bps: float | None
    sell_slippage_10k_bps: float | None


def close_prices(candles: list[dict[str, Any]]) -> list[float]:
    prices: list[float] = []
    for candle in sorted(candles, key=lambda item: int(item.get("t", 0))):
        value = decimal_or_none(candle.get("c"))
        if value is not None and value > 0:
            prices.append(float(value))
    return prices


def simple_returns(prices: list[float]) -> list[float]:
    return [prices[index] / prices[index - 1] - 1 for index in range(1, len(prices))]


def dated_returns(candles: list[dict[str, Any]]) -> dict[int, float]:
    """Return close-to-close returns keyed by the closing candle timestamp."""
    closes: list[tuple[int, float]] = []
    for candle in sorted(candles, key=lambda item: int(item.get("t", 0))):
        timestamp = candle.get("t")
        value = decimal_or_none(candle.get("c"))
        if isinstance(timestamp, int) and value is not None and value > 0:
            closes.append((timestamp, float(value)))
    return {
        closes[index][0]: closes[index][1] / closes[index - 1][1] - 1
        for index in range(1, len(closes))
    }


COUNTRY_TIMEZONES = {
    "United States": "America/New_York",
    "China": "Asia/Shanghai",
    "Japan": "Asia/Tokyo",
    "South Korea": "Asia/Seoul",
    "Taiwan": "Asia/Taipei",
    "United Kingdom": "Europe/London",
    "Eurozone": "Europe/Paris",
    "India": "Asia/Kolkata",
    "Brazil": "America/Sao_Paulo",
}


def session_returns(
    candles: list[dict[str, Any]], *, is_24_7: bool | None, country: str | None
) -> dict[str, float]:
    """Return series keyed by the reference market's local session date."""
    timezone = UTC if is_24_7 else ZoneInfo(COUNTRY_TIMEZONES.get(country or "", "UTC"))
    dated = dated_returns(candles)
    return {
        datetime.fromtimestamp(timestamp / 1_000, tz=UTC)
        .astimezone(timezone)
        .date()
        .isoformat(): value
        for timestamp, value in dated.items()
    }


def period_return(prices: list[float], days: int) -> float | None:
    if len(prices) <= days or prices[-days - 1] <= 0:
        return None
    return (prices[-1] / prices[-days - 1] - 1) * 100


def annualized_volatility(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252) * 100


def max_drawdown(prices: list[float]) -> float | None:
    if not prices:
        return None
    peak = prices[0]
    worst = 0.0
    for price in prices:
        peak = max(peak, price)
        worst = min(worst, price / peak - 1)
    return worst * 100


def historical_var_95(returns: list[float]) -> float | None:
    if len(returns) < 20:
        return None
    ordered = sorted(returns)
    index = max(0, math.ceil(len(ordered) * 0.05) - 1)
    return ordered[index] * 100


def correlation(left: list[float], right: list[float]) -> float | None:
    size = min(len(left), len(right))
    if size < 20:
        return None
    x, y = left[-size:], right[-size:]
    mean_x, mean_y = sum(x) / size, sum(y) / size
    covariance = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
    variance_x = sum((a - mean_x) ** 2 for a in x)
    variance_y = sum((b - mean_y) ** 2 for b in y)
    denominator = math.sqrt(variance_x * variance_y)
    return covariance / denominator if denominator else None


def dated_correlation[SessionKey: Hashable](
    left: Mapping[SessionKey, float],
    right: Mapping[SessionKey, float],
    *,
    minimum_observations: int = 20,
) -> tuple[float | None, int]:
    """Correlate returns only where both series have the same candle timestamp."""
    shared = sorted(left.keys() & right.keys(), key=str)
    observations = len(shared)
    if observations < minimum_observations:
        return None, observations
    return correlation([left[key] for key in shared], [right[key] for key in shared]), observations


def order_book_metrics(
    book: dict[str, Any], *, target_notional: Decimal = Decimal("10000")
) -> OrderBookMetrics:
    levels = book.get("levels", [])
    bids = levels[0] if len(levels) > 0 else []
    asks = levels[1] if len(levels) > 1 else []
    best_bid = decimal_or_none(bids[0].get("px")) if bids else None
    best_ask = decimal_or_none(asks[0].get("px")) if asks else None
    if best_bid is None or best_ask is None or best_bid <= 0 or best_ask <= 0:
        return {
            "spread_bps": None,
            "bid_depth_10bps_usd": None,
            "ask_depth_10bps_usd": None,
            "buy_slippage_10k_bps": None,
            "sell_slippage_10k_bps": None,
        }
    mid = (best_bid + best_ask) / 2

    def depth(side: list[dict[str, Any]]) -> Decimal:
        return sum(
            (
                (decimal_or_none(level.get("px")) or Decimal(0))
                * (decimal_or_none(level.get("sz")) or Decimal(0))
                for level in side
                if abs((decimal_or_none(level.get("px")) or mid) / mid - 1) <= Decimal("0.001")
            ),
            start=Decimal(0),
        )

    def slippage(side: list[dict[str, Any]]) -> float | None:
        remaining, cost, quantity = target_notional, Decimal(0), Decimal(0)
        for level in side:
            price = decimal_or_none(level.get("px"))
            size = decimal_or_none(level.get("sz"))
            if price is None or size is None or price <= 0:
                continue
            fill_notional = min(remaining, price * size)
            cost += fill_notional
            quantity += fill_notional / price
            remaining -= fill_notional
            if remaining <= 0:
                break
        if remaining > 0 or quantity <= 0:
            return None
        average = cost / quantity
        return float(abs(average / mid - 1) * Decimal(10_000))

    return {
        "spread_bps": float((best_ask - best_bid) / mid * Decimal(10_000)),
        "bid_depth_10bps_usd": depth(bids),
        "ask_depth_10bps_usd": depth(asks),
        "buy_slippage_10k_bps": slippage(asks),
        "sell_slippage_10k_bps": slippage(bids),
    }
