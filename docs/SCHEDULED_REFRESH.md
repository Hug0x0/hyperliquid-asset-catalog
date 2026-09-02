# Scheduled refresh

The `Catalog refresh` GitHub Actions workflow runs daily and can be dispatched manually. It fetches
the read-only catalog, validates it, exports a partitioned Parquet snapshot, and publishes the
catalog, diff, run report and manifest as one artifact retained for 30 days.

Runs are serialized to avoid snapshot races. Structured logs provide counts and failures. A failed
run opens one deduplicated `catalog-refresh-failure` issue with a link to the logs. GitHub Actions
artifacts are the publication boundary: the workflow never commits generated market data and holds
only read and issue-write permissions.
