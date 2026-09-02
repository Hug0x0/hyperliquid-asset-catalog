# Versioned benchmark methodologies

Methodologies in `config/benchmark_methodologies.yaml` define eligibility, weighting, constituent
buffers, caps and rebalance cadence under a stable ID and semantic version. Pass
`--methodology-id equal-weight` or `liquidity-capped` to `backtest-benchmark`.

Every result embeds the fully resolved methodology and SHA-256 input snapshot ID. Rule changes bump
the methodology version: patch for clarifications, minor for backward-compatible additions, major
for changed selection or return behavior. Historical results remain descriptive, are vulnerable to
survivorship bias when inputs are not point-in-time, and are never forecasts.
