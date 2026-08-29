# Public release audit

Audit date: 2026-08-29  
Audited revision: `f2279b2`

## Decision

**Publishable. The blocking license finding has been resolved with Apache-2.0.**

The codebase is small, read-only by design, tested, and does not contain wallet or trading paths.
No credential-like material was found in tracked files, filenames, or the reviewed Git history. The
project can be made public after completing the remaining recommended release checks below.

This is a technical release review, not legal advice.

## Findings

### Resolved — Software license

The project is now licensed under Apache-2.0. The canonical license is stored in `LICENSE`, the
SPDX identifier is declared in `pyproject.toml`, and the README links to it. The author should still
confirm ownership or employer clearance for all code and configuration data.

### P1 — Secret scanning is not automated

The manual inspection found no secrets. `.env`, PEM/key files, cookies, caches, environments and
generated output are ignored. However, neither Gitleaks nor TruffleHog is installed locally and CI
does not scan commits or pull requests. Add Gitleaks to CI and enable GitHub secret scanning after
the repository becomes public.

The Git history exposes the author's email address in commit metadata. This is normal for Git, but
should be consciously accepted before publication; changing it fully requires rewriting history.

### P1 — Generated financial claims can become stale

`output/medium_analysis.md` is deliberately tracked as a point-in-time snapshot. Its date is clear,
but readers may still mistake its rankings for current market conditions. Add a prominent snapshot
notice and a reproducibility block containing the commit, command, retrieval time and source-data
hash. Avoid presenting the output as investment advice.

### P1 — Correlations are not aligned by trading date

The analytics retain only close-price arrays, then correlate the last `min(n, m)` returns. Markets
with missing sessions or different calendars can therefore be paired by position rather than date.
Align returns on candle timestamps before calculating correlations and report the number of shared
observations.

### P1 — Dependency vulnerability checks are absent

Dependencies are version-bounded, but not locked, and CI does not run a vulnerability audit or
automated dependency updates. Add Dependabot and `pip-audit`. A lock file is optional for a library,
but a reproducible development/test environment would make published analyses easier to reproduce.

### P2 — Community and release metadata are incomplete

The repository has CI and a useful README, but no contributing guide, security policy, code of
conduct, issue templates, changelog, package classifiers, project URLs, or release workflow. These
are not blockers, but adding the first four will make a public launch much easier to maintain.

### P2 — Live API behavior needs integration coverage

The unit suite mocks the Hyperliquid API and passes, but there is no scheduled smoke test detecting
upstream schema drift. Add a low-frequency, read-only workflow that fetches metadata, validates the
catalog, and stores no generated market snapshot in Git.

## Evidence

- `ruff check .`: passed
- `ruff format --check .`: passed (24 files)
- `mypy src`: passed in strict mode (16 source files)
- `pytest -q`: 18 passed
- Git working tree: clean; local `main` matched `origin/main` during the audit
- Git history/file review: no private keys, access tokens, passwords, credential files, or large
  unexpected blobs found
- Largest historical blob: the attributed Medium cover image, about 96 KB
- Runtime behavior: public Info API only; no signing, wallet, order placement, or private endpoint
- Cover asset: source, author, license link and repository crop are documented

## Release checklist

- [x] Choose and add `LICENSE`; declare it in `pyproject.toml` and the README
- [ ] Confirm ownership/employer clearance for all code and configuration data
- [ ] Decide whether the historical commit email may be public
- [ ] Run a dedicated full-history secret scanner
- [ ] Add secret scanning and dependency auditing to CI
- [ ] Add `SECURITY.md` and `CONTRIBUTING.md`
- [ ] Fix date-aligned correlations before promoting analytics as decision-grade
- [ ] Add reproducibility metadata and a strong snapshot warning to generated articles
- [ ] Enable branch protection and required CI checks on `main`
- [x] Close the P0 licensing item before making the repository public
