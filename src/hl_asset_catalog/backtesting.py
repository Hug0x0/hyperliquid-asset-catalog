from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from .models import SCHEMA_VERSION
from .utils import atomic_json

WeightingMethod = Literal["equal", "liquidity", "inverse_volatility"]


def _weights(
    symbols: list[str],
    rows: dict[str, dict[str, float]],
    histories: dict[str, list[float]],
    method: WeightingMethod,
) -> dict[str, float]:
    if method == "liquidity":
        raw = {symbol: max(0.0, rows[symbol].get("volume", 0.0)) for symbol in symbols}
    elif method == "inverse_volatility":
        raw = {}
        for symbol in symbols:
            values = histories[symbol][-20:]
            if len(values) < 5:
                raw[symbol] = 1.0
                continue
            mean = sum(values) / len(values)
            variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
            raw[symbol] = 1 / math.sqrt(variance) if variance > 0 else 1.0
    else:
        raw = {symbol: 1.0 for symbol in symbols}
    total = sum(raw.values())
    if total <= 0:
        return {symbol: 1 / len(symbols) for symbol in symbols}
    return {symbol: value / total for symbol, value in raw.items()}


def backtest_benchmark(
    history: list[dict[str, Any]],
    *,
    symbols: list[str],
    weighting: WeightingMethod = "equal",
    rebalance_every: int = 5,
) -> dict[str, Any]:
    by_date: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for item in history:
        symbol = str(item["symbol"]).upper()
        if symbol in symbols:
            by_date[str(item["date"])][symbol] = {
                key: float(item.get(key, 0))
                for key in ("close", "volume", "spread_bps", "slippage_bps")
            }
    dates = sorted(by_date)
    histories: dict[str, list[float]] = defaultdict(list)
    previous_close: dict[str, float] = {}
    weights: dict[str, float] = {}
    cumulative = 1.0
    peak = 1.0
    max_drawdown = 0.0
    total_turnover = 0.0
    total_cost = 0.0
    daily_results: list[dict[str, Any]] = []
    for index, date in enumerate(dates):
        rows = by_date[date]
        available = [symbol for symbol in symbols if symbol in rows and rows[symbol]["close"] > 0]
        returns = {
            symbol: rows[symbol]["close"] / previous_close[symbol] - 1
            for symbol in available
            if symbol in previous_close
        }
        portfolio_return = sum(weights.get(symbol, 0) * value for symbol, value in returns.items())
        for symbol, value in returns.items():
            histories[symbol].append(value)
        turnover = cost = 0.0
        if available and (not weights or index % rebalance_every == 0):
            new_weights = _weights(available, rows, histories, weighting)
            turnover = (
                sum(
                    abs(new_weights.get(symbol, 0) - weights.get(symbol, 0))
                    for symbol in set(weights) | set(new_weights)
                )
                / 2
            )
            average_cost_bps = sum(
                rows[symbol].get("spread_bps", 0) + rows[symbol].get("slippage_bps", 0)
                for symbol in available
            ) / len(available)
            cost = turnover * average_cost_bps / 10_000
            weights = new_weights
        net_return = portfolio_return - cost
        cumulative *= 1 + net_return
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative / peak - 1)
        total_turnover += turnover
        total_cost += cost
        daily_results.append(
            {
                "date": date,
                "gross_return": portfolio_return,
                "net_return": net_return,
                "turnover": turnover,
                "transaction_cost": cost,
                "cumulative_return": cumulative - 1,
                "weights": weights,
            }
        )
        previous_close.update({symbol: rows[symbol]["close"] for symbol in available})
    net_returns = [row["net_return"] for row in daily_results]
    mean = sum(net_returns) / len(net_returns) if net_returns else 0.0
    variance = (
        sum((value - mean) ** 2 for value in net_returns) / (len(net_returns) - 1)
        if len(net_returns) > 1
        else 0.0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "weighting": weighting,
        "rebalance_every_sessions": rebalance_every,
        "symbols": symbols,
        "observations": len(daily_results),
        "total_return": cumulative - 1,
        "annualized_volatility": math.sqrt(variance) * math.sqrt(252),
        "max_drawdown": max_drawdown,
        "total_turnover": total_turnover,
        "total_transaction_cost": total_cost,
        "daily": daily_results,
        "disclaimer": "Historical simulation is descriptive and not a forecast.",
    }


def export_backtest(result: dict[str, Any], output_path: Path) -> None:
    atomic_json(output_path, result)
