from __future__ import annotations

import json
import platform
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, TypedDict

from .config import Settings, load_yaml

DoctorStatus = Literal["pass", "warning", "failure"]


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    status: DoctorStatus
    message: str


class DoctorReport(TypedDict):
    schema_version: str
    checks: list[dict[str, str]]
    summary: dict[str, int]


_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|secret|password|signature)=([^&\s]+)")


def redact(value: str) -> str:
    return _SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=<redacted>", value)


def run_doctor(root: Path, settings: Settings) -> DoctorReport:
    checks: list[DoctorCheck] = []
    checks.append(
        DoctorCheck(
            "runtime",
            "pass" if sys.version_info >= (3, 12) else "failure",
            f"Python {platform.python_version()}",
        )
    )
    for name, path in (("output_dir", settings.output_dir), ("cache_dir", settings.cache_dir)):
        parent = path if path.exists() else path.parent
        status: DoctorStatus = "pass" if parent.exists() and parent.is_dir() else "warning"
        checks.append(DoctorCheck(name, status, redact(str(path))))
    for relative in (
        "config/classification_rules.yaml",
        "config/basket_definitions.yaml",
        "config/benchmark_definitions.yaml",
    ):
        path = root / relative
        try:
            load_yaml(path)
            checks.append(DoctorCheck(relative, "pass", "valid YAML mapping"))
        except (OSError, ValueError) as exc:
            checks.append(DoctorCheck(relative, "failure", redact(str(exc))))
    cache_files = list(settings.cache_dir.rglob("*.json")) if settings.cache_dir.is_dir() else []
    corrupt = 0
    for path in cache_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            corrupt += 1
    checks.append(
        DoctorCheck(
            "cache_integrity",
            "warning" if corrupt else "pass",
            f"{len(cache_files)} JSON file(s), {corrupt} unreadable",
        )
    )
    summary = {
        status: sum(check.status == status for check in checks)
        for status in ("pass", "warning", "failure")
    }
    return {
        "schema_version": "1.0",
        "checks": [asdict(check) for check in checks],
        "summary": summary,
    }


def doctor_exit_code(report: DoctorReport) -> int:
    summary = report["summary"]
    if summary.get("failure", 0):
        return 1
    return 2 if summary.get("warning", 0) else 0
