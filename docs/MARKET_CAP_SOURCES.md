# Market-cap enrichment

Market caps are never inferred. Prepare a JSON object keyed by the exact catalog instrument ID and
run `hl-catalog enrich-market-caps caps.json --source-name NAME --license-url URL`. Only positive
values with an exact ID match are applied. Each value stores its provider, license URL and retrieval
timestamp; missing IDs remain null.

Before using a feed, review its reliability, update cadence, redistribution rights and identifier
mapping. The operator is responsible for supplying data they are licensed to process and publish.
The public Hyperliquid API remains the sole authority for whether an instrument is tradable.
