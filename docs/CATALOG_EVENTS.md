# Catalog events

`hl-catalog diff-events PREVIOUS CURRENT` emits one JSON object per line, ordered by asset ID.
Listings, delistings, metadata changes and classification changes use schema version `1.0`.
Event IDs hash the asset ID, type and before/after values, so repeated diffs are idempotent.
`observed_at` records when the comparison was made and is intentionally excluded from the ID.

Minor schema additions remain backward compatible. Removing or changing a field requires a new
major schema version. Consumers should retain unknown fields and partition streams by schema major.
