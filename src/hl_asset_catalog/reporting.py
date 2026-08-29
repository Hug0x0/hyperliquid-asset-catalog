from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import SCHEMA_VERSION, BenchmarkResult, Instrument, MarketAnalytics
from .utils import atomic_json


def benchmark_quality(
    benchmarks: list[BenchmarkResult], analytics: list[MarketAnalytics]
) -> list[dict[str, Any]]:
    by_symbol = {item.symbol.upper(): item for item in analytics}
    rows: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        measured = [
            by_symbol[symbol] for symbol in benchmark.available_symbols if symbol in by_symbol
        ]
        average_liquidity = (
            sum(item.liquidity_score for item in measured) / len(measured) if measured else 0
        )
        average_quality = (
            sum(item.data_quality_score for item in measured) / len(measured) if measured else 0
        )
        measured_ratio = (
            len(measured) / benchmark.unique_constituents if benchmark.unique_constituents else 0
        )
        depth_score = min(100.0, benchmark.unique_constituents / 10 * 100)
        score = round(
            depth_score * 0.35
            + benchmark.coverage_ratio * 100 * 0.20
            + average_liquidity * measured_ratio * 0.25
            + average_quality * measured_ratio * 0.20,
            2,
        )
        grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "benchmark_id": benchmark.benchmark_id,
                "name": benchmark.name,
                "status": benchmark.status,
                "quality_score": score,
                "grade": grade,
                "unique_constituents": benchmark.unique_constituents,
                "coverage_ratio": round(benchmark.coverage_ratio, 4),
                "measured_constituents": len(measured),
                "measured_ratio": round(measured_ratio, 4),
                "average_liquidity_score": round(average_liquidity, 2),
                "average_data_quality_score": round(average_quality, 2),
                "total_volume_24h_usd": benchmark.total_volume_24h_usd,
                "total_open_interest_usd": benchmark.total_open_interest_usd,
                "available_symbols": benchmark.available_symbols,
                "missing_symbols": benchmark.missing_symbols,
            }
        )
    return sorted(rows, key=lambda row: (-row["quality_score"], row["name"]))


def export_benchmark_quality(rows: list[dict[str, Any]], output_dir: Path) -> None:
    atomic_json(output_dir / "benchmark_quality_report.json", rows)
    csv_rows = [
        {
            **row,
            "available_symbols": "|".join(row["available_symbols"]),
            "missing_symbols": "|".join(row["missing_symbols"]),
        }
        for row in rows
    ]
    with (output_dir / "benchmark_quality_report.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]) if csv_rows else [])
        if csv_rows:
            writer.writeheader()
            writer.writerows(csv_rows)


def _money(value: Decimal | int | float) -> str:
    number = float(value)
    if number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if number >= 1_000_000:
        return f"${number / 1_000_000:.2f} M"
    if number >= 1_000:
        return f"${number / 1_000:.1f} k"
    return f"${number:.0f}"


def generate_medium_article(
    quality_rows: list[dict[str, Any]],
    analytics: list[MarketAnalytics],
    assets: list[Instrument],
    correlations: dict[str, dict[str, float | None]],
    *,
    total_non_crypto: int,
    lookback_days: int,
    output_path: Path,
    git_commit: str | None = None,
) -> None:
    status_counts = Counter(str(row["status"]) for row in quality_rows)
    liquid = sorted(analytics, key=lambda item: item.liquidity_score, reverse=True)[:10]
    volatile = sorted(
        (item for item in analytics if item.annualized_volatility_pct is not None),
        key=lambda item: item.annualized_volatility_pct or 0,
        reverse=True,
    )[:5]
    with_monthly_returns = [item for item in analytics if item.return_30d_pct is not None]
    winners = sorted(with_monthly_returns, key=lambda item: item.return_30d_pct or 0, reverse=True)[
        :5
    ]
    losers = sorted(with_monthly_returns, key=lambda item: item.return_30d_pct or 0)[:5]
    non_crypto = [
        asset for asset in assets if asset.asset_class not in {"crypto", "spot_crypto", "unknown"}
    ]
    class_counts = Counter(asset.asset_class for asset in non_crypto)
    country_counts = Counter(asset.country or "Unclassified" for asset in non_crypto)
    executable = sorted(
        (
            item
            for item in analytics
            if item.buy_slippage_10k_bps is not None and item.sell_slippage_10k_bps is not None
        ),
        key=lambda item: ((item.buy_slippage_10k_bps or 0) + (item.sell_slippage_10k_bps or 0)) / 2,
    )[:10]
    correlation_pairs = sorted(
        (
            (left, right, value)
            for left, row in correlations.items()
            for right, value in row.items()
            if left < right and value is not None
        ),
        key=lambda pair: abs(pair[2]),
        reverse=True,
    )[:10]
    generated = datetime.now(UTC).strftime("%B %d, %Y")
    lines = [
        "# Hyperliquid Beyond Crypto: Which TradFi Benchmarks Can We Actually Build?",
        "",
        "![Financial trading charts on multiple screens](../assets/medium-cover.jpg)",
        "",
        "*Cover photo by [Jakub Żerdzicki](https://unsplash.com/@jakubzerdzicki) on "
        "[Unsplash](https://unsplash.com/photos/vKNRKjSNbTo), used under the Unsplash License.*",
        "",
        f"*Analysis generated on {generated} from public Hyperliquid market data"
        f"{f' at commit `{git_commit[:12]}`' if git_commit else ''}.*",
        "",
        "Hyperliquid is no longer only a venue for crypto perpetuals. The expansion of HIP-3 "
        "markets now provides access to equities, indices, commodities, currencies, and pre-IPO "
        "assets. But a list of tickers is not enough: a credible benchmark also requires market "
        "depth, liquidity, diversification, and reliable data.",
        "",
        "## What We Measured",
        "",
        f"The catalog contains **{total_non_crypto} non-crypto contracts**. After deduplicating "
        "identical underlyings listed on multiple DEXs, we evaluated 17 themes. For each ticker, "
        "we retained the market with the highest 24-hour volume, using open interest as the "
        "secondary selection criterion.",
        "",
        f"For the {len(analytics)} most liquid markets, the study combines {lookback_days} days "
        "of daily candles with an L2 order book snapshot. The resulting metrics include returns, "
        "annualized volatility, maximum drawdown, historical 95% VaR, spread, depth within 10 "
        "basis points, and estimated slippage for a $10,000 order.",
        "",
        "### Universe by asset class",
        "",
        "| Asset class | Contracts | Share of non-crypto catalog |",
        "|---|---:|---:|",
    ]
    for asset_class, count in class_counts.most_common():
        lines.append(
            f"| {asset_class.replace('_', ' ').title()} | {count} | "
            f"{count / len(non_crypto) * 100:.1f}% |"
        )
    lines.extend(
        [
            "",
            "### Geographic distribution",
            "",
            "The country field refers to the underlying reference market. Global commodities "
            "are kept in a separate bucket rather than assigned to a single country.",
            "",
            "| Reference country or region | Contracts |",
            "|---|---:|",
        ]
    )
    for country, count in country_counts.most_common():
        lines.append(f"| {country} | {count} |")
    lines.extend(
        [
            "",
            "## Five Themes Already Have Sufficient Breadth",
            "",
            f"Of the 17 benchmarks, **{status_counts['sufficient']} have sufficient breadth**, "
            f"**{status_counts['concentrated']} remain concentrated**, and "
            f"**{status_counts['insufficient']} are insufficient**. We require at least five "
            "unique "
            "constituents before considering a benchmark sufficiently diversified.",
            "",
            "| Benchmark | Status | Constituents | Measured | Coverage | Score | Grade | "
            "24h Volume |",
            "|---|---|---:|---:|---:|---:|:---:|---:|",
        ]
    )
    for row in quality_rows:
        lines.append(
            f"| {row['name']} | {row['status']} | {row['unique_constituents']} | "
            f"{row['measured_constituents']} | "
            f"{row['coverage_ratio'] * 100:.0f}% | {row['quality_score']:.1f} | "
            f"{row['grade']} | {_money(row['total_volume_24h_usd'])} |"
        )
    lines.extend(
        [
            "",
            "Semiconductors, Big Tech, and artificial intelligence emerge as the most natural "
            "universes. They combine broader constituent sets with a higher probability of "
            "finding several actively traded markets.",
            "",
            "## The Most Liquid Markets in the Snapshot",
            "",
            "| Asset | DEX | Liquidity Score | 24h Volume | Open Interest | Spread |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for item in liquid:
        spread = f"{item.spread_bps:.1f} bps" if item.spread_bps is not None else "n/a"
        lines.append(
            f"| {item.symbol} | {item.dex} | {item.liquidity_score:.1f} | "
            f"{_money(item.volume_24h_usd or 0)} | "
            f"{_money(item.open_interest_usd or 0)} | {spread} |"
        )
    lines.extend(
        [
            "",
            "## Execution Quality: What a $10,000 Order Might Face",
            "",
            "Displayed volume alone does not guarantee execution quality. We therefore estimate "
            "the cost of immediately buying or selling $10,000 against the visible L2 book. "
            "These figures are static snapshots: they exclude latency, hidden liquidity, adverse "
            "selection, and the market's reaction to the order.",
            "",
            "| Asset | DEX | Spread | Buy slippage | Sell slippage | Bid depth ±10bps | "
            "Ask depth ±10bps |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for item in executable:
        lines.append(
            f"| {item.symbol} | {item.dex} | {(item.spread_bps or 0):.2f} bps | "
            f"{(item.buy_slippage_10k_bps or 0):.2f} bps | "
            f"{(item.sell_slippage_10k_bps or 0):.2f} bps | "
            f"{_money(item.bid_depth_10bps_usd or 0)} | "
            f"{_money(item.ask_depth_10bps_usd or 0)} |"
        )
    lines.extend(
        [
            "",
            "## Correlation Clusters Matter for Diversification",
            "",
            "A benchmark with many names can still be economically concentrated if its members "
            "move together. The table below shows the strongest absolute daily-return correlations "
            "in the analyzed sample. Correlations are indicative because markets may follow "
            "different trading calendars and the available history is limited.",
            "",
            "| Asset A | Asset B | Daily-return correlation |",
            "|---|---|---:|",
        ]
    )
    for left, right, value in correlation_pairs:
        lines.append(f"| {left} | {right} | {value:.3f} |")
    lines.extend(
        [
            "",
            "## Risk Remains Highly Uneven",
            "",
            "The most volatile assets in the sample should not receive the same weight as a major "
            "index or a liquid large-cap equity without additional risk controls. Equal weighting "
            "is easy to explain, but a liquidity-capped or volatility-aware methodology is usually "
            "more robust for a synthetic product.",
            "",
            "| Asset | Annualized Volatility | Maximum Drawdown | Daily 95% VaR |",
            "|---|---:|---:|---:|",
        ]
    )
    for item in volatile:
        lines.append(
            f"| {item.symbol} | {item.annualized_volatility_pct:.1f}% | "
            f"{(item.max_drawdown_pct or 0):.1f}% | {(item.historical_var_95_pct or 0):.1f}% |"
        )
    lines.extend(
        [
            "",
            "### Recent 30-day dispersion",
            "",
            "The gap between recent winners and losers illustrates why benchmark construction "
            "needs diversification and rebalancing rules rather than discretionary ticker picking.",
            "",
            "| Strongest 30-day returns | Return | Weakest 30-day returns | Return |",
            "|---|---:|---|---:|",
        ]
    )
    for winner, loser in zip(winners, losers, strict=False):
        lines.append(
            f"| {winner.symbol} | {(winner.return_30d_pct or 0):.1f}% | "
            f"{loser.symbol} | {(loser.return_30d_pct or 0):.1f}% |"
        )
    lines.extend(
        [
            "",
            "## How the Benchmark Quality Score Works",
            "",
            "The 0–100 score is intentionally conservative. It combines four components:",
            "",
            "- **35% breadth:** the number of unique active constituents, capped at ten;",
            "- **20% coverage:** the share of the target definition currently available;",
            "- **25% liquidity:** the average liquidity score of measured constituents, "
            "penalized when detailed analytics cover only part of the benchmark;",
            "- **20% data quality:** historical and order-book completeness, using the same "
            "measured-coverage penalty.",
            "",
            "Grades are A for scores of 80 or above, B from 65 to 79.9, C from 50 to 64.9, "
            "and D below 50. Breadth status and quality grade answer different questions: a theme "
            "may contain five names yet still receive a weak grade if liquidity or measured data "
            "coverage is poor.",
            "",
            "## What This Means for an Investable Product",
            "",
            "A benchmark should not be considered investable based on ticker count alone. It needs "
            "minimum volume requirements, a maximum acceptable spread, sufficient depth for the "
            "intended trade size, and fallback rules when a market is suspended. Concentrated "
            "themes may be useful exploratory indicators, but they are not yet broad references.",
            "",
            "The next step is to retain a daily history of these metrics, measure their stability, "
            "and simulate rebalancing, turnover, and transaction costs. The technical availability "
            "of a contract is not the same thing as sustainable execution capacity.",
            "",
            "### Practical construction rules",
            "",
            "A first production methodology could impose the following controls:",
            "",
            "1. Require at least five active, unique underlyings and cap any constituent at 25%.",
            "2. Exclude markets below explicit 24-hour volume, open-interest, depth, and "
            "data-quality thresholds.",
            "3. Prefer liquidity weighting with constituent caps; use equal weighting only "
            "when execution quality is comparable.",
            "4. Rebalance on a predictable schedule and add a buffer zone to reduce "
            "unnecessary turnover.",
            "5. Suspend additions when the reference market is closed, the oracle is stale, "
            "or spreads exceed a defined ceiling.",
            "6. Maintain a fallback DEX mapping for duplicate underlyings, but never switch "
            "venues without validating margin and oracle differences.",
            "",
            "## Methodology and Limitations",
            "",
            "The data comes from the public Hyperliquid API and represents a point-in-time "
            "snapshot. "
            "Slippage estimates use the visible order book and do not model dynamic market impact. "
            "Volatility is annualized over 252 trading sessions from daily returns. Funding is "
            "annualized for illustration from the current hourly rate. We do not fabricate market "
            "capitalization data; market-cap weighting would require a reliable external source.",
            "",
            "Technical sources: [Hyperliquid Info endpoint]"
            "(https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint) "
            "and [rate limits]"
            "(https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/"
            "rate-limits-and-user-limits).",
            "",
            "*This analysis is provided for informational purposes only and does not constitute "
            "financial advice.*",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
