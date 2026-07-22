# Hyperliquid Beyond Crypto: Which TradFi Benchmarks Can We Actually Build?

![Financial trading charts on multiple screens](../assets/medium-cover.jpg)

*Cover photo by [Jakub Żerdzicki](https://unsplash.com/@jakubzerdzicki) on [Unsplash](https://unsplash.com/photos/vKNRKjSNbTo), used under the Unsplash License.*

*Analysis generated on July 22, 2026 from public Hyperliquid market data.*

Hyperliquid is no longer only a venue for crypto perpetuals. The expansion of HIP-3 markets now provides access to equities, indices, commodities, currencies, and pre-IPO assets. But a list of tickers is not enough: a credible benchmark also requires market depth, liquidity, diversification, and reliable data.

## What We Measured

The catalog contains **196 non-crypto contracts**. After deduplicating identical underlyings listed on multiple DEXs, we evaluated 17 themes. For each ticker, we retained the market with the highest 24-hour volume, using open interest as the secondary selection criterion.

For the 40 most liquid markets, the study combines 90 days of daily candles with an L2 order book snapshot. The resulting metrics include returns, annualized volatility, maximum drawdown, historical 95% VaR, spread, depth within 10 basis points, and estimated slippage for a $10,000 order.

### Universe by asset class

| Asset class | Contracts | Share of non-crypto catalog |
|---|---:|---:|
| Equity | 90 | 45.9% |
| Equity Index | 47 | 24.0% |
| Commodity | 37 | 18.9% |
| Pre Ipo | 11 | 5.6% |
| Forex | 7 | 3.6% |
| Volatility Index | 2 | 1.0% |
| Interest Rate | 2 | 1.0% |

### Geographic distribution

The country field refers to the underlying reference market. Global commodities are kept in a separate bucket rather than assigned to a single country.

| Reference country or region | Contracts |
|---|---:|
| United States | 114 |
| Global | 39 |
| China | 12 |
| South Korea | 9 |
| Japan | 8 |
| Eurozone | 3 |
| Pre-IPO / Global | 3 |
| Taiwan | 2 |
| Brazil | 2 |
| United Kingdom | 2 |
| India | 1 |
| Netherlands | 1 |

## Five Themes Already Have Sufficient Breadth

Of the 17 benchmarks, **5 have sufficient breadth**, **6 remain concentrated**, and **6 are insufficient**. We require at least five unique constituents before considering a benchmark sufficiently diversified.

| Benchmark | Status | Constituents | Measured | Coverage | Score | Grade | 24h Volume |
|---|---|---:|---:|---:|---:|:---:|---:|
| Big Tech | sufficient | 10 | 9 | 100% | 93.0 | A | $213.76 M |
| Artificial Intelligence | sufficient | 9 | 8 | 82% | 85.1 | A | $261.54 M |
| Semiconductors | sufficient | 17 | 6 | 100% | 70.2 | B | $1.25B |
| Banking and Fintech | concentrated | 4 | 3 | 100% | 65.1 | B | $33.49 M |
| Space | insufficient | 2 | 2 | 67% | 62.9 | C | $240.30 M |
| Pre-IPO | sufficient | 8 | 4 | 73% | 62.1 | C | $1.01B |
| Precious Metals | concentrated | 4 | 2 | 57% | 47.5 | D | $162.44 M |
| US Equity Indices | concentrated | 4 | 2 | 50% | 46.4 | D | $372.15 M |
| Asian Equity Indices | sufficient | 5 | 2 | 56% | 44.4 | D | $51.85 M |
| Energy | concentrated | 4 | 2 | 36% | 42.5 | D | $159.44 M |
| Automotive | concentrated | 3 | 1 | 60% | 36.7 | D | $27.42 M |
| Foreign Exchange | concentrated | 3 | 0 | 60% | 22.5 | D | $3.69 M |
| Biotech and Healthcare | insufficient | 2 | 0 | 67% | 20.3 | D | $2.09 M |
| Industrial Metals | insufficient | 1 | 0 | 50% | 13.5 | D | $1.79 M |
| Defense | insufficient | 1 | 0 | 33% | 10.2 | D | $2.39 M |
| Agriculture | insufficient | 0 | 0 | 0% | 0.0 | D | $0 |
| Volatility | insufficient | 0 | 0 | 0% | 0.0 | D | $0 |

Semiconductors, Big Tech, and artificial intelligence emerge as the most natural universes. They combine broader constituent sets with a higher probability of finding several actively traded markets.

## The Most Liquid Markets in the Snapshot

| Asset | DEX | Liquidity Score | 24h Volume | Open Interest | Spread |
|---|---|---:|---:|---:|---:|
| XYZ100 | xyz | 99.8 | $241.56 M | $288.95 M | 0.3 bps |
| SP500 | xyz | 98.3 | $127.23 M | $524.48 M | 0.9 bps |
| SPCX | xyz | 97.8 | $232.10 M | $154.35 M | 0.9 bps |
| CL | xyz | 97.6 | $313.45 M | $175.31 M | 0.1 bps |
| SNDK | xyz | 96.6 | $638.43 M | $113.59 M | 0.6 bps |
| MU | xyz | 96.6 | $420.21 M | $208.38 M | 0.6 bps |
| GOLD | xyz | 96.5 | $63.01 M | $164.34 M | 0.2 bps |
| SKHX | xyz | 96.5 | $535.59 M | $475.85 M | 1.5 bps |
| BRENTOIL | xyz | 96.2 | $151.27 M | $212.39 M | 1.0 bps |
| SKHY | xyz | 96.2 | $229.63 M | $184.97 M | 0.6 bps |

## Execution Quality: What a $10,000 Order Might Face

Displayed volume alone does not guarantee execution quality. We therefore estimate the cost of immediately buying or selling $10,000 against the visible L2 book. These figures are static snapshots: they exclude latency, hidden liquidity, adverse selection, and the market's reaction to the order.

| Asset | DEX | Spread | Buy slippage | Sell slippage | Bid depth ±10bps | Ask depth ±10bps |
|---|---|---:|---:|---:|---:|---:|
| CRCL | xyz | 0.15 bps | 0.08 bps | 0.08 bps | $118.6 k | $333.1 k |
| CL | xyz | 0.12 bps | 0.17 bps | 0.14 bps | $301.6 k | $667.8 k |
| XYZ100 | xyz | 0.34 bps | 0.17 bps | 0.17 bps | $2.77 M | $3.35 M |
| GOLD | xyz | 0.24 bps | 0.25 bps | 0.36 bps | $423.7 k | $648.1 k |
| SILVER | xyz | 0.17 bps | 0.41 bps | 0.22 bps | $197.3 k | $240.9 k |
| SP500 | xyz | 0.93 bps | 0.47 bps | 0.47 bps | $1.07 M | $840.6 k |
| SPCX | xyz | 0.86 bps | 0.86 bps | 0.43 bps | $1.02 M | $801.2 k |
| TSLA | xyz | 1.10 bps | 0.55 bps | 0.97 bps | $222.7 k | $189.3 k |
| DRAM | xyz | 1.18 bps | 0.74 bps | 0.90 bps | $125.1 k | $114.0 k |
| SNDK | xyz | 0.61 bps | 1.40 bps | 0.31 bps | $398.9 k | $524.2 k |

## Correlation Clusters Matter for Diversification

A benchmark with many names can still be economically concentrated if its members move together. The table below shows the strongest absolute daily-return correlations in the analyzed sample. Correlations are indicative because markets may follow different trading calendars and the available history is limited.

| Asset A | Asset B | Daily-return correlation |
|---|---|---:|
| BRENTOIL | CL | 0.978 |
| DRAM | EWY | 0.960 |
| DRAM | MU | 0.949 |
| DRAM | SKHX | 0.942 |
| EWY | SKHX | 0.923 |
| DRAM | KIOXIA | 0.915 |
| KIOXIA | SKHX | 0.907 |
| EWY | SMSN | 0.897 |
| EWY | KIOXIA | 0.895 |
| EWY | MU | 0.894 |

## Risk Remains Highly Uneven

The most volatile assets in the sample should not receive the same weight as a major index or a liquid large-cap equity without additional risk controls. Equal weighting is easy to explain, but a liquidity-capped or volatility-aware methodology is usually more robust for a synthetic product.

| Asset | Annualized Volatility | Maximum Drawdown | Daily 95% VaR |
|---|---:|---:|---:|
| ZHIPU | 201.4% | -65.2% | -20.4% |
| KIOXIA | 167.0% | -47.6% | -16.5% |
| SKHY | 137.9% | -18.0% | 0.0% |
| QNT | 125.0% | -50.1% | -8.9% |
| CBRS | 124.6% | -48.9% | -10.7% |

### Recent 30-day dispersion

The gap between recent winners and losers illustrates why benchmark construction needs diversification and rebalancing rules rather than discretionary ticker picking.

| Strongest 30-day returns | Return | Weakest 30-day returns | Return |
|---|---:|---|---:|
| CL | 16.9% | ZHIPU | -53.2% |
| BRENTOIL | 16.4% | SKHX | -31.8% |
| AAPL | 10.1% | RKLB | -30.4% |
| META | 10.1% | MRVL | -29.0% |
| MSFT | 5.2% | SNDK | -28.0% |

## How the Benchmark Quality Score Works

The 0–100 score is intentionally conservative. It combines four components:

- **35% breadth:** the number of unique active constituents, capped at ten;
- **20% coverage:** the share of the target definition currently available;
- **25% liquidity:** the average liquidity score of measured constituents, penalized when detailed analytics cover only part of the benchmark;
- **20% data quality:** historical and order-book completeness, using the same measured-coverage penalty.

Grades are A for scores of 80 or above, B from 65 to 79.9, C from 50 to 64.9, and D below 50. Breadth status and quality grade answer different questions: a theme may contain five names yet still receive a weak grade if liquidity or measured data coverage is poor.

## What This Means for an Investable Product

A benchmark should not be considered investable based on ticker count alone. It needs minimum volume requirements, a maximum acceptable spread, sufficient depth for the intended trade size, and fallback rules when a market is suspended. Concentrated themes may be useful exploratory indicators, but they are not yet broad references.

The next step is to retain a daily history of these metrics, measure their stability, and simulate rebalancing, turnover, and transaction costs. The technical availability of a contract is not the same thing as sustainable execution capacity.

### Practical construction rules

A first production methodology could impose the following controls:

1. Require at least five active, unique underlyings and cap any constituent at 25%.
2. Exclude markets below explicit 24-hour volume, open-interest, depth, and data-quality thresholds.
3. Prefer liquidity weighting with constituent caps; use equal weighting only when execution quality is comparable.
4. Rebalance on a predictable schedule and add a buffer zone to reduce unnecessary turnover.
5. Suspend additions when the reference market is closed, the oracle is stale, or spreads exceed a defined ceiling.
6. Maintain a fallback DEX mapping for duplicate underlyings, but never switch venues without validating margin and oracle differences.

## Methodology and Limitations

The data comes from the public Hyperliquid API and represents a point-in-time snapshot. Slippage estimates use the visible order book and do not model dynamic market impact. Volatility is annualized over 252 trading sessions from daily returns. Funding is annualized for illustration from the current hourly rate. We do not fabricate market capitalization data; market-cap weighting would require a reliable external source.

Technical sources: [Hyperliquid Info endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint) and [rate limits](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits).

*This analysis is provided for informational purposes only and does not constitute financial advice.*
