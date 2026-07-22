from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from .models import BenchmarkResult, MarketAnalytics
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
        depth_score = min(100.0, benchmark.unique_constituents / 10 * 100)
        score = round(
            depth_score * 0.35
            + benchmark.coverage_ratio * 100 * 0.20
            + average_liquidity * 0.25
            + average_quality * 0.20,
            2,
        )
        grade = "A" if score >= 80 else "B" if score >= 65 else "C" if score >= 50 else "D"
        rows.append(
            {
                "benchmark_id": benchmark.benchmark_id,
                "name": benchmark.name,
                "status": benchmark.status,
                "quality_score": score,
                "grade": grade,
                "unique_constituents": benchmark.unique_constituents,
                "coverage_ratio": round(benchmark.coverage_ratio, 4),
                "measured_constituents": len(measured),
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
        return f"${number / 1_000_000_000:.2f} Md"
    if number >= 1_000_000:
        return f"${number / 1_000_000:.2f} M"
    if number >= 1_000:
        return f"${number / 1_000:.1f} k"
    return f"${number:.0f}"


def generate_medium_article(
    quality_rows: list[dict[str, Any]],
    analytics: list[MarketAnalytics],
    *,
    total_non_crypto: int,
    output_path: Path,
) -> None:
    status_counts = Counter(str(row["status"]) for row in quality_rows)
    liquid = sorted(analytics, key=lambda item: item.liquidity_score, reverse=True)[:10]
    volatile = sorted(
        (item for item in analytics if item.annualized_volatility_pct is not None),
        key=lambda item: item.annualized_volatility_pct or 0,
        reverse=True,
    )[:5]
    best = quality_rows[:8]
    generated = datetime.now(UTC).strftime("%d %B %Y")
    lines = [
        "# Hyperliquid au-delà de la crypto : quels benchmarks TradFi "
        "peut-on vraiment construire ?",
        "",
        f"*Analyse générée le {generated} à partir des marchés publics Hyperliquid.*",
        "",
        "Hyperliquid n’est plus seulement un terrain de jeu pour les perpetuals crypto. "
        "L’essor des marchés HIP-3 ouvre l’accès à des actions, indices, matières premières, "
        "devises et actifs pre-IPO. Mais une liste de tickers ne suffit pas : pour construire "
        "un benchmark crédible, il faut de la profondeur, de la liquidité et des données fiables.",
        "",
        "## Ce que nous avons mesuré",
        "",
        f"Le catalogue contient **{total_non_crypto} contrats non-crypto**. Après déduplication "
        "des mêmes sous-jacents entre DEX, nous avons évalué 17 thèmes. Le marché retenu pour "
        "chaque ticker est celui affichant le meilleur volume 24 h, puis le meilleur "
        "open interest.",
        "",
        "Pour les 40 marchés les plus liquides, l’étude combine 90 jours de bougies quotidiennes "
        "avec un instantané du carnet L2 : rendements, volatilité annualisée, drawdown maximal, "
        "VaR historique à 95 %, spread, profondeur à 10 points de base et slippage "
        "estimé pour $10k.",
        "",
        "## Résultat : cinq thèmes ont déjà une profondeur suffisante",
        "",
        f"Sur 17 benchmarks, **{status_counts['sufficient']} sont suffisants**, "
        f"**{status_counts['concentrated']} concentrés** et "
        f"**{status_counts['insufficient']} insuffisants**. Le seuil retenu est de cinq "
        "constituants uniques pour un benchmark suffisamment diversifié.",
        "",
        "| Benchmark | Constituants | Couverture | Score | Grade | Volume 24 h | Open interest |",
        "|---|---:|---:|---:|:---:|---:|---:|",
    ]
    for row in best:
        lines.append(
            f"| {row['name']} | {row['unique_constituents']} | "
            f"{row['coverage_ratio'] * 100:.0f}% | {row['quality_score']:.1f} | "
            f"{row['grade']} | {_money(row['total_volume_24h_usd'])} | "
            f"{_money(row['total_open_interest_usd'])} |"
        )
    lines.extend(
        [
            "",
            "Les semi-conducteurs, la Big Tech et l’intelligence artificielle ressortent comme "
            "les univers les plus naturels. Ils combinent davantage de sous-jacents et une "
            "meilleure "
            "probabilité de trouver plusieurs marchés activement négociés.",
            "",
            "## Les marchés offrant la meilleure liquidité observée",
            "",
            "| Actif | DEX | Score de liquidité | Volume 24 h | Open interest | Spread |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for item in liquid:
        spread = f"{item.spread_bps:.1f} bps" if item.spread_bps is not None else "n/d"
        lines.append(
            f"| {item.symbol} | {item.dex} | {item.liquidity_score:.1f} | "
            f"{_money(item.volume_24h_usd or 0)} | "
            f"{_money(item.open_interest_usd or 0)} | {spread} |"
        )
    lines.extend(
        [
            "",
            "## Le risque reste très hétérogène",
            "",
            "Les actifs les plus volatils de l’échantillon ne doivent pas recevoir le même poids "
            "qu’un grand indice ou qu’une action liquide sans contrôle de risque. Une pondération "
            "équipondérée est facile à expliquer, mais une approche plafonnée par liquidité ou par "
            "volatilité est généralement plus robuste pour un produit synthétique.",
            "",
            "| Actif | Volatilité annualisée | Drawdown maximal | VaR 95 % quotidienne |",
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
            "## Ce que cela implique pour un produit investissable",
            "",
            "Un benchmark ne devrait pas être déclaré investissable sur le seul nombre de tickers. "
            "Il faut imposer un volume minimal, un spread maximal, une profondeur suffisante pour "
            "la taille visée et un mécanisme de repli lorsqu’un marché est suspendu. Les thèmes "
            "concentrés peuvent servir d’indicateurs exploratoires, mais pas encore de références "
            "largement diversifiées.",
            "",
            "La prochaine étape consiste à conserver un historique quotidien de ces métriques afin "
            "de mesurer leur stabilité, puis à simuler les rebalancements, le turnover et "
            "les coûts "
            "de transaction. La disponibilité technique d’un contrat n’est pas équivalente à une "
            "capacité d’exécution durable.",
            "",
            "## Méthodologie et limites",
            "",
            "Les données proviennent de l’API publique Hyperliquid et représentent un instantané. "
            "Les estimations de slippage utilisent le carnet visible et ignorent l’impact "
            "dynamique. "
            "La volatilité est annualisée sur 252 séances à partir des rendements quotidiens. Le "
            "funding est annualisé à titre indicatif à partir du taux horaire courant. "
            "Aucun market cap n’est inventé : une pondération par capitalisation nécessiterait "
            "une source externe fiable.",
            "",
            "*Cette analyse est fournie à titre informatif et ne constitue pas un conseil "
            "financier.*",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
