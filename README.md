# Hyperliquid Asset Catalog

Production-oriented, read-only discovery of Hyperliquid native perpetuals, every dynamically
discovered HIP-3 DEX (including `xyz`), and spot markets. It uses only the public Info API: no
wallet, private key, signature, or order path exists in this project.

## Install

Python 3.12 is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Usage

```bash
hl-catalog list-dexes
hl-catalog fetch --pretty --include-raw
hl-catalog fetch --dex xyz --active-only
hl-catalog fetch --market-type spot
hl-catalog fetch --asset-class equity --tag semiconductors
hl-catalog validate
hl-catalog build-baskets
hl-catalog build-benchmarks
hl-catalog analyze-markets --lookback-days 90 --max-assets 40
hl-catalog export --format csv
```

`fetch` discovers the DEX list first and queries metadata/context for each DEX concurrently.
Failures are retried with exponential jitter. A short API cache lives under
`.cache/hl_asset_catalog`; `--force-refresh` bypasses fresh cache entries, and stale valid entries
are used when the API temporarily fails. Partial DEX failures are recorded in `run_report.json`.

The API is the sole source of truth for tradability. TradeXYZ documentation enrichment is a
conservative optional hook and cannot create an instrument. Manual, deterministic classification
lives in `config/classification_rules.yaml`; no LLM runs in the pipeline.

## Data rules

- HIP-3 IDs use `100000 + perp_dex_index * 10000 + index_in_meta`; the DEX index is discovered.
- Decimal arithmetic is retained internally. JSON serializes `Decimal` values as strings to avoid
  precision loss. CSV uses `|` for list fields and JSON text for mappings.
- `all_assets.json` from the previous run is compared before replacement; changes are written to
  `catalog_diff.json`.
- Equal weights are rounded to 8 decimals and the final constituent receives the exact remainder.
  Market-cap and inverse-volatility weighting refuse to invent unavailable inputs.

## Outputs

The `output/` directory contains the complete JSON/CSV catalog, native/HIP-3/XYZ/spot/classified
subsets, a run report and catalog diff. `build-baskets` adds available and unavailable basket
evaluations. Outputs and caches are deliberately excluded from Git.

`non_crypto_assets.json` and `non_crypto_assets.csv` contain only explicitly classified TradFi
instruments; crypto, spot crypto and unknown instruments are excluded. `non_crypto_by_country.json`
groups the same instruments by reference country. Cross-country commodities use `Global`, while
pre-IPO instruments without a single listed home market use `Pre-IPO / Global`.

`build-benchmarks` deduplicates identical underlyings across DEXs by selecting the market with the
highest 24-hour volume (then open interest), and generates `sector_benchmark_report.json` plus CSV.
Five or more unique constituents is `sufficient`, three or four is `concentrated`, and fewer than
three is `insufficient`. Definitions are editable in `config/benchmark_definitions.yaml`.

`analyze-markets` enriches the most liquid deduplicated non-crypto markets with daily candles and
L2 books. It computes 1/7/30-day returns, annualized volatility, maximum drawdown, historical 95%
VaR, spread, depth within 10 bps, estimated slippage for a $10k order, annualized funding, liquidity
and data-quality scores, plus a return correlation matrix. Defaults are deliberately capped at 40
markets over 90 days to remain below the public API's weighted rate limit.

Analytics outputs:

- `market_analytics.json` and `.csv`: risk, activity and execution metrics per selected market;
- `correlation_matrix.json`: pairwise daily-return correlations;
- `benchmark_quality_report.json` and `.csv`: investability-oriented sector scores;
- `medium_analysis.md`: a publication-ready English analysis generated from the live results.

The generated Medium article is intentionally tracked in `output/medium_analysis.md` as a
publication snapshot. Its cover image is stored in `assets/medium-cover.jpg`, with source and
license details in `assets/medium-cover-ATTRIBUTION.md`.

Risk measures are descriptive, not forecasts. Volatility uses 252 trading days; historical VaR is
the empirical fifth percentile and funding annualization assumes the context rate is hourly. Book
slippage is a static snapshot that does not model market impact or latency.

## Verification

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Official references: [Info endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint),
[perpetuals](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals),
[spot](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/spot), and
[asset IDs](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids).
