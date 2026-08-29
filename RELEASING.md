# Release process

The project creates verified build artifacts for version tags. Publishing to PyPI is intentionally
not automated yet.

## Prepare a release

1. Create a release issue and choose the next semantic version.
2. Move relevant entries from `Unreleased` in `CHANGELOG.md` to a dated version section.
3. Update `project.version` in `pyproject.toml` and `__version__` in
   `src/hl_asset_catalog/__init__.py` to the same value.
4. Run the complete verification suite:

   ```bash
   ruff check .
   ruff format --check .
   mypy src
   pytest
   pip-audit
   python -m build
   twine check dist/*
   ```

5. Merge the release pull request after required checks pass.

## Tag and publish

Create a signed annotated tag from the verified `main` commit:

```bash
git switch main
git pull --ff-only
git tag -s vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

The `Package release` workflow rebuilds the wheel and source distribution, verifies them with
Twine, and uploads them as workflow artifacts. Download and inspect those artifacts, then create a
GitHub release from the tag using the matching changelog section as release notes.

If PyPI publishing is added later, use trusted publishing with a protected GitHub environment; do
not store long-lived API tokens in repository secrets.
