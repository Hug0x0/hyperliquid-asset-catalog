from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).parents[1]
DESTINATION = ROOT / "site-docs"
SOURCES = [
    "CLI.md",
    "SCHEMA_VERSIONING.md",
    "CATALOG_EVENTS.md",
    "PARQUET.md",
    "SCORE_METHODOLOGY.md",
    "BENCHMARK_METHODOLOGIES.md",
    "MARKET_SESSIONS.md",
    "OBSERVABILITY.md",
    "SCHEDULED_REFRESH.md",
    "CONTAINER.md",
]


def main() -> None:
    for name in SOURCES:
        shutil.copyfile(ROOT / "docs" / name, DESTINATION / name)
    shutil.copyfile(ROOT / "CONTRIBUTING.md", DESTINATION / "CONTRIBUTING.md")
    shutil.copyfile(ROOT / "SECURITY.md", DESTINATION / "SECURITY.md")


if __name__ == "__main__":
    main()
