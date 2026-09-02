# Observability

Human-readable logs remain the default. Add `--json-logs` to `fetch` for newline-delimited JSON on
stderr. Every structured event includes a timestamp, severity, component, operation and per-run
correlation ID. The final fetch event reports asset, request and failure counts.

Log output is separate from command stdout contracts. Keys named API key, token, secret or password
are redacted. Do not add raw API responses, complete asset payloads, credentials or signed URLs to
logs.
