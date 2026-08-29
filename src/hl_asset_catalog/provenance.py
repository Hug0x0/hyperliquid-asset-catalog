from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .utils import atomic_json


def git_revision(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_analysis_manifest(
    output_dir: Path,
    *,
    root: Path,
    started_at: str,
    api_endpoint: str,
    arguments: dict[str, Any],
    cache_hits: int,
    stale_cache_fallbacks: list[str],
) -> dict[str, Any]:
    generated_files = [
        "market_analytics.json",
        "correlation_matrix.json",
        "correlation_observations.json",
        "benchmark_quality_report.json",
        "medium_analysis.md",
    ]
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "retrieval_started_at": started_at,
        "retrieval_completed_at": datetime.now(UTC).isoformat(),
        "git_commit": git_revision(root),
        "api_endpoint": api_endpoint,
        "arguments": arguments,
        "source_files": {"all_assets.json": sha256_file(output_dir / "all_assets.json")},
        "generated_files": {
            filename: sha256_file(output_dir / filename) for filename in generated_files
        },
        "cache": {
            "fresh_hits": cache_hits,
            "stale_fallbacks": stale_cache_fallbacks,
        },
    }
    atomic_json(output_dir / "analysis_manifest.json", manifest)
    return manifest
