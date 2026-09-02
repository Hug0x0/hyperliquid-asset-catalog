# Parquet snapshots

Install the optional adapter with `pip install '.[parquet]'`, then run
`hl-catalog export --format parquet`. Snapshots are atomically written below
`output/parquet/snapshot_date=YYYY-MM-DD/catalog.parquet` with Zstandard compression.

Scalar strings, integers, floats and booleans retain their natural Arrow types. Decimal values are
stored as exact strings to preserve source precision. Lists and mappings use canonical JSON text.
New nullable columns are backward compatible; removing, renaming or changing a column type requires
a new major catalog schema. JSON output remains the canonical interchange format.
