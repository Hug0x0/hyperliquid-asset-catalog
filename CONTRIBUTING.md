# Contributing

Thank you for improving Hyperliquid Asset Catalog. Contributions should keep the project read-only,
deterministic, and auditable.

## Development setup

Python 3.12 is the supported runtime.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

Before opening a pull request, run:

```bash
ruff check .
ruff format --check .
mypy src
pytest
pip-audit
```

## Pull requests

- Keep changes focused and link the relevant issue.
- Add or update tests for every behavior change.
- Preserve backward-compatible output schemas unless the change explicitly documents a new schema
  version.
- Never add wallet, private-key, signing, or order-execution logic without a separate security and
  scope review.
- Do not commit generated market snapshots, caches, credentials, cookies, or local environments.

## Data and classification changes

The public Hyperliquid Info API is the sole source of truth for whether a market exists and is
tradable. External sources may enrich metadata but must not create instruments.

Changes to `config/classification_rules.yaml` must include:

- the exact symbol and DEX;
- a primary or authoritative source supporting the classification;
- the date the source was checked;
- tests covering the resulting asset class, country, and important tags;
- an explanation for aliases or ambiguous symbols.

Do not infer missing financial values. New data sources must document their license, provenance,
cache policy, update frequency, and failure behavior.

## Commit style

Use Conventional Commits where practical, for example:

```text
fix(analytics): align returns by trading date (#11)
```

By submitting a contribution, you agree that it is licensed under Apache-2.0.
