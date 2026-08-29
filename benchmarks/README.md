# Performance benchmarks

Run the deterministic, network-free catalog benchmark with:

```bash
python benchmarks/catalog_performance.py --check
```

It generates 1,000 synthetic HIP-3 instruments and measures normalization, classification, JSON
serialization, CSV serialization, total elapsed time, and peak Python memory. CI currently enforces
a deliberately conservative ceiling of 5 seconds and 128 MiB to catch major regressions without
making shared-runner noise a source of flaky failures.

Tighten the limits only after collecting stable results across local and GitHub-hosted runners.
