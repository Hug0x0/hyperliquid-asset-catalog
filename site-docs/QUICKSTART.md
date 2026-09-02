# Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
hl-catalog fetch --active-only
hl-catalog validate
hl-catalog query --where asset_class=equity --format json
```

All commands are read-only with respect to Hyperliquid. Generated files are written under
`output/` and cache entries under `.cache/hl_asset_catalog/`.
