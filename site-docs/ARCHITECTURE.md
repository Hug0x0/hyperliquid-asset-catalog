# Architecture

The discovery layer queries the public Info API and dynamically enumerates DEXes. Normalization
creates strict `Instrument` models; deterministic classification rules enrich those instruments.
Exporters write atomic JSON/CSV/Parquet artifacts. Analytics consumes local catalog models plus
public candles and books, then emits versioned reports and provenance manifests.

External documentation and market-cap feeds are optional enrichment only. Neither may create an
instrument. The public API remains the tradability authority.
