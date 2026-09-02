# Score methodology

Liquidity and data-quality scores are descriptive heuristics from 0 to 100, versioned as `1.0.0`.
Liquidity combines reported volume/open interest, order-book depth, spread and simulated slippage.
Data quality combines field completeness, history length and anomaly/error penalties.

Run `hl-catalog calibrate-scores` to compare the implementation contract with the reviewed fixture.
The fixture is synthetic and checks bounds, monotonic missing-data behavior and rank stability. It is
not labelled market ground truth and the scores do not forecast returns, solvency or execution.
Any weight or threshold change must bump the score version and include a before/after report.
