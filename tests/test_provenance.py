import hashlib
from pathlib import Path

from hl_asset_catalog.provenance import sha256_file, write_analysis_manifest


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_bytes(b"catalog")
    assert sha256_file(path) == hashlib.sha256(b"catalog").hexdigest()
    assert sha256_file(tmp_path / "missing") is None


def test_write_analysis_manifest(tmp_path: Path) -> None:
    (tmp_path / "all_assets.json").write_text("[]")
    manifest = write_analysis_manifest(
        tmp_path,
        root=tmp_path,
        started_at="2026-01-01T00:00:00Z",
        api_endpoint="https://api.example.test/info",
        arguments={"lookback_days": 90},
        cache_hits=2,
        stale_cache_fallbacks=["l2Book"],
    )

    assert manifest["schema_version"] == 1
    assert manifest["git_commit"] is None
    assert manifest["cache"] == {"fresh_hits": 2, "stale_fallbacks": ["l2Book"]}
    assert (tmp_path / "analysis_manifest.json").is_file()
