# Container image

Tagged releases publish `ghcr.io/hug0x0/hyperliquid-asset-catalog` for AMD64 and ARM64 with
immutable semantic-version and commit tags. Builds use a digest-pinned Python base, execute as UID
10001, and attach BuildKit SBOM and provenance attestations. CI smoke-tests the CLI and scans the
filesystem for high/critical vulnerabilities.

Mount writable volumes at `/data/output` and `/data/cache`:

```bash
docker run --rm -v "$PWD/output:/data/output" -v "$PWD/cache:/data/cache" \
  ghcr.io/hug0x0/hyperliquid-asset-catalog:0.1.0 fetch --active-only
```

Use an immutable digest in scheduled production jobs. No wallet or secret is needed.
