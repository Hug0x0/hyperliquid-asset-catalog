# I Mapped Every Hyperliquid Market With Python — Without a Wallet or Private Key

![Financial trading charts across multiple screens](https://images.unsplash.com/photo-1767424412548-1a1ac7f4b9bc?auto=format&fit=crop&w=1600&q=85)

*Cover photo by [Jakub Żerdzicki](https://unsplash.com/@jakubzerdzicki) on
[Unsplash](https://unsplash.com/photos/vKNRKjSNbTo), used under the Unsplash License.*

Hyperliquid is evolving quickly. What began as a venue best known for crypto perpetuals now spans
native markets, HIP-3 deployments, specialized DEXs, spot assets, and a growing selection of
traditional-finance underlyings: equities, indices, commodities, currencies, and even pre-IPO
exposure.

That expansion creates a practical problem for developers and analysts: **how do you get one
normalized, auditable view of everything that is actually available?**

That is the purpose of
[Hyperliquid Asset Catalog](https://github.com/Hug0x0/hyperliquid-asset-catalog), an open-source,
read-only Python tool that discovers markets from Hyperliquid's public Info API, normalizes and
classifies them, and produces reusable datasets and market-quality analytics.

> The market figures in this article come from a July 22, 2026 snapshot. They illustrate the
> project rather than current market conditions and are not financial advice.

## A ticker list is not a market catalog

Fetching a list of symbols is easy. Building a catalog that can support research is not.

The same underlying may trade on several DEXs. HIP-3 asset IDs depend on both the dynamically
discovered DEX index and the instrument's position in that DEX's metadata. Some markets are paused,
some have limited depth, and a symbol alone does not tell you whether it represents a crypto asset,
an equity, an index, or a commodity.

A useful pipeline must also preserve numerical precision, tolerate partial API failures, document
data freshness, and avoid confusing technical availability with investability.

Hyperliquid Asset Catalog turns that moving API surface into a deterministic workflow:

1. Discover every perpetual DEX dynamically.
2. Fetch metadata and market contexts concurrently.
3. Normalize native perpetuals, HIP-3 markets, and spot pairs.
4. Apply explicit, version-controlled classification rules.
5. Validate, deduplicate, and export JSON and CSV datasets.
6. Optionally analyze candles and L2 order books.

## Read-only by design

The most important architectural decision is also the simplest: there is no order path in the
repository.

No wallet. No private key. No signing. No trading automation.

The client only calls Hyperliquid's public Info API. This separation keeps the security surface
small and makes the project suitable for research, market monitoring, universe construction, and
data engineering.

You can explore the full market surface with a few commands:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

hl-catalog list-dexes
hl-catalog fetch --pretty
hl-catalog validate
hl-catalog export --format csv
```

The output includes a complete catalog plus dedicated native, HIP-3, XYZ, spot, crypto, and
non-crypto subsets. Partial failures are written to a run report instead of being silently dropped.

![Laptop displaying Python code](https://images.unsplash.com/photo-1675495277087-10598bf7bcd1?auto=format&fit=crop&w=1600&q=85)

*Photo by [Bernd Dittrich](https://unsplash.com/@hdbernd) on
[Unsplash](https://unsplash.com/photos/uL1TI7xyLHQ), used under the Unsplash License.*

## Why normalization matters

Financial data pipelines often fail in quiet, unglamorous ways. Precision is one example.

Hyperliquid Asset Catalog retains monetary values as Python `Decimal` objects internally and
serializes them as strings in JSON. This avoids the subtle rounding errors that binary floating
point can introduce.

Classification is equally deliberate. The rules live in version-controlled YAML, where they can be
reviewed, tested, and corrected through a pull request. No LLM decides in production whether a new
ticker is an equity or a commodity.

That approach is less magical than opaque classification, but it offers what a financial catalog
actually needs: auditability.

The API also remains the sole source of truth for tradability. Optional documentation enrichment
can add context, but it can never invent a market that Hyperliquid itself does not report.

## From a catalog to thematic benchmarks

Once the markets are normalized, the project can evaluate whether a thematic basket is technically
constructible.

Before evaluating a benchmark, it deduplicates underlyings listed on multiple DEXs. It keeps the
market with the highest 24-hour volume, using open interest as the secondary criterion.

The snapshot tracked in the repository contained **196 non-crypto contracts**. Across 17 proposed
themes, five had at least five unique constituents, six remained concentrated, and six were
insufficient. Big Tech, artificial intelligence, and semiconductors emerged as the most natural
universes at that point in time.

The result highlights an important distinction: a large number of contracts does not automatically
produce a credible benchmark. Four separate dimensions matter:

- breadth of the available universe;
- coverage of the intended benchmark definition;
- constituent liquidity;
- completeness and quality of the underlying data.

The project's benchmark-quality score combines all four and penalizes themes for which detailed
market analytics cover only part of the constituent set.

## Measuring what headline volume cannot show

The analytics command enriches the most liquid deduplicated non-crypto markets with daily candles
and a live L2 order-book snapshot:

```bash
hl-catalog analyze-markets --lookback-days 90 --max-assets 40
```

It computes 1-, 7-, and 30-day returns, annualized volatility, maximum drawdown, historical 95%
Value at Risk, spread, depth within ten basis points, and estimated slippage for a $10,000 order.

![Market charts shown on digital devices](https://images.unsplash.com/photo-1748439281934-2803c6a3ee36?auto=format&fit=crop&w=1600&q=85)

*Photo by [Jakub Żerdzicki](https://unsplash.com/@jakubzerdzicki) on
[Unsplash](https://unsplash.com/photos/rUimC7J5j1k), used under the Unsplash License.*

This distinction matters. A market can report impressive volume while offering poor execution at
the moment you try to trade. Conversely, a deep book and tight spread today do not prove that the
same conditions will persist tomorrow.

The analytics are therefore descriptive, not predictive. Slippage is estimated from a static book;
it does not model latency, hidden liquidity, dynamic market impact, or adverse selection.

## Engineering for an API that changes

The implementation uses a compact Python stack: HTTPX for asynchronous requests, Pydantic for data
models, Typer for the CLI, and Pytest for verification.

Concurrency is bounded with a semaphore. Transient failures are retried with randomized exponential
backoff. A short-lived cache reduces API load, while stale valid responses can provide a fallback
during temporary failures. Every partial DEX error remains visible in the generated run report.

At the time of writing, the repository passes linting, formatting, strict static typing, 18 unit
tests, and a package build. It is released under the Apache License 2.0.

The project is still an evolving research tool. Important next steps include aligning correlation
inputs on exact candle dates, recording a reproducibility manifest for every analysis, automating
dependency and secret scanning, and adding a scheduled smoke test for upstream API schema changes.

## What can be built on top of it?

The catalog can become the foundation for several useful products:

- a searchable HIP-3 market explorer;
- a daily history of listings, suspensions, and metadata changes;
- alerts for changing liquidity, depth, or spreads;
- a screening engine for thematic baskets;
- a research dataset on the growth of on-chain TradFi markets;
- a dashboard comparing execution quality across DEXs.

Its job is not to issue a buy signal. Its job is to make the universe observable, comparable, and
reproducible.

## The broader lesson

As Hyperliquid expands beyond crypto perpetuals, the ecosystem needs an open and auditable data
layer. Hyperliquid Asset Catalog offers one in the form of a readable CLI with no private access and
no trading automation.

The project is available on GitHub:
[github.com/Hug0x0/hyperliquid-asset-catalog](https://github.com/Hug0x0/hyperliquid-asset-catalog).

If you work on market data, thematic benchmarks, or the HIP-3 ecosystem, the most valuable
contributions are better classification evidence, new API edge cases, and stronger ways to measure
liquidity and reproducibility.

*Disclaimer: This project and article are provided for informational and experimental purposes
only. They do not constitute financial advice. Derivatives involve substantial risk.*

---

**Medium publishing metadata**

- Subtitle: *A read-only Python CLI for discovering, normalizing, and analyzing native, HIP-3, XYZ,
  and spot markets.*
- Suggested tags: `Hyperliquid`, `Python`, `DeFi`, `Data Engineering`, `Open Source`
- Suggested kicker: `OPEN-SOURCE MARKET DATA`
- Canonical URL: leave empty unless this article is first published elsewhere.

