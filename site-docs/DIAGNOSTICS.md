# Diagnostics

Run `hl-catalog doctor` for read-only runtime, configuration and cache checks. Add `--json` for the
stable machine-readable schema. Exit 0 means healthy, 2 means warnings, and 1 means failures.
Credentials and sensitive URL parameters are redacted.
