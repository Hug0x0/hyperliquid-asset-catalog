# Proposed GitHub issues

The labels and priorities below are suggestions. Each section is ready to paste into a GitHub issue.

## 1. [DONE] Choose and add an open-source license

**Labels:** `legal`, `documentation`, `priority: critical`

Resolved with Apache-2.0: the canonical `LICENSE` text, SPDX project metadata and README section
have been added. Ownership of all tracked code/configuration should still be confirmed before the
repository becomes public.

**Acceptance criteria**

- GitHub detects the selected license.
- `pyproject.toml` contains valid SPDX license metadata.
- README contains a License section.
- All tracked third-party assets retain their own attribution/license information.

## 2. [P1] Align correlation inputs on candle timestamps

**Labels:** `bug`, `analytics`, `priority: high`

Correlation currently pairs return arrays by trailing position. This can misalign markets with
different holidays, missing candles, or trading calendars. Build timestamp-to-return series, use
the intersection of dates for each pair, and expose the shared observation count.

**Acceptance criteria**

- Pairwise correlations use identical timestamps only.
- Pairs below a configurable minimum number of common observations return `null`.
- The output records shared observation counts.
- Tests cover missing and non-overlapping candle dates.

## 3. [P1] Add full-history secret scanning

**Labels:** `security`, `ci`, `priority: high`

Add Gitleaks to CI for pushes and pull requests, document a local command, and enable GitHub secret
scanning when available.

**Acceptance criteria**

- CI fails on a synthetic secret fixture/test case.
- The scanner covers Git history, not only the working tree.
- False-positive handling is documented and auditable.

## 4. [P1] Add dependency security and update automation

**Labels:** `security`, `dependencies`, `ci`

Add `pip-audit` to CI and Dependabot for Python packages and GitHub Actions. Decide whether to
publish a reproducible constraints/lock file for development and analysis snapshots.

**Acceptance criteria**

- CI audits the installed dependency graph.
- Dependabot is configured with a reasonable update cadence.
- GitHub Actions are pinned to immutable commit SHAs or an explicit policy documents why tags are
  accepted.

## 5. [P1] Add provenance metadata to generated analytics

**Labels:** `analytics`, `reproducibility`, `documentation`

Generated reports should identify exactly how and when they were produced. Add retrieval start/end
times, Git commit, CLI arguments, API endpoint, source-data hash, schema version, and stale-cache
usage to a machine-readable manifest and article footer.

**Acceptance criteria**

- Every analysis run writes `analysis_manifest.json`.
- The Medium generator includes a visible snapshot date and commit.
- Stale-cache fallback is disclosed per affected request.
- A documented command can reproduce the output structure.

## 6. [P1] Validate live API schemas at the boundary

**Labels:** `reliability`, `api`, `testing`

Replace broad `Any` handling at the HTTP boundary with explicit validation for the response shapes
the pipeline consumes. Preserve partial-failure behavior with actionable error messages.

**Acceptance criteria**

- Metadata, context, candle and L2 payloads are validated before normalization.
- Schema errors include endpoint/payload type and a safe response summary.
- Tests cover malformed, partial and forward-compatible responses.

## 7. [P2] Add a scheduled read-only upstream smoke test

**Labels:** `ci`, `integration-test`, `api`

Run a small scheduled workflow against the public Info API to detect upstream schema drift. Keep
the request budget low and do not commit market snapshots.

**Acceptance criteria**

- The workflow runs weekly and on manual dispatch.
- It discovers DEXes, fetches a minimal catalog and runs validation.
- It uploads the run report as a short-lived artifact on failure.

## 8. [P2] Add public-project governance files

**Labels:** `documentation`, `community`

Add `CONTRIBUTING.md`, `SECURITY.md`, issue templates and a pull-request template. Include supported
Python versions, verification commands, disclosure instructions, and the policy for classification
rule changes.

**Acceptance criteria**

- Security reports have a private disclosure route.
- Contributions require tests and explain data-source/provenance expectations.
- Bug and classification-change templates request reproducible evidence.

## 9. [P2] Improve CLI validation and machine-readable exit behavior

**Labels:** `cli`, `developer-experience`

Use typed enums/ranges for all filter and format options, validate writable output/cache paths, and
return non-zero exit codes when validation finds errors or a run is materially partial.

**Acceptance criteria**

- Invalid market/asset class/format values fail before network access.
- `validate` distinguishes warnings from errors and supports JSON output.
- Partial-fetch exit behavior is documented and tested.

## 10. [P2] Publish package and release metadata

**Labels:** `packaging`, `documentation`

Complete PEP 621 metadata, add project URLs and classifiers, create a changelog, and define a tagged
release process. Publishing to PyPI can remain a separate decision.

**Acceptance criteria**

- Built wheel and sdist pass `twine check`.
- Package metadata includes license, authors, URLs, keywords and classifiers.
- A documented release checklist produces versioned GitHub releases.
