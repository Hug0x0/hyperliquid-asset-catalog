# Security policy

## Supported versions

Security fixes are applied to the latest commit on `main`. Tagged releases will be listed here once
the first stable release is published.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or exposed secret. Use GitHub's
[private vulnerability reporting](https://github.com/Hug0x0/hyperliquid-asset-catalog/security/advisories/new)
to share the impact, affected revision, reproduction steps, and any proposed mitigation.

You should receive an acknowledgement within seven days. Please allow time for validation and a
coordinated fix before public disclosure.

## Scope

The repository is designed for public, read-only market data. Reports involving credential
handling, signing, or order execution are still relevant if a future change accidentally introduces
those capabilities. Availability of the upstream Hyperliquid API and financial losses from use of
descriptive analytics are outside this project's security guarantees.

## Secret scanning

CI scans the full Git history with Gitleaks. To run the equivalent check locally after installing
Gitleaks:

```bash
gitleaks git . --redact
```

Never suppress a finding without documenting why the matched value is safe.
