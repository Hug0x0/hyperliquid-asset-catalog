from pathlib import Path

import httpx
import respx

from hl_asset_catalog.config import Settings
from hl_asset_catalog.doctor import doctor_exit_code, redact, run_doctor


def test_redacts_query_secrets() -> None:
    assert redact("https://x.test/?api_key=hunter2&mode=read") == (
        "https://x.test/?api_key=<redacted>&mode=read"
    )


def test_doctor_runs_offline_and_reports_stable_schema(tmp_path: Path) -> None:
    root = tmp_path / "root"
    config = root / "config"
    config.mkdir(parents=True)
    for name in (
        "classification_rules.yaml",
        "basket_definitions.yaml",
        "benchmark_definitions.yaml",
    ):
        (config / name).write_text("items: []\n", encoding="utf-8")
    report = run_doctor(root, Settings(output_dir=tmp_path, cache_dir=tmp_path / "cache"))
    assert report["schema_version"] == "1.0"
    assert doctor_exit_code(report) in {0, 2}


def test_doctor_failure_exit_code(tmp_path: Path) -> None:
    report = run_doctor(tmp_path, Settings(output_dir=tmp_path, cache_dir=tmp_path))
    assert doctor_exit_code(report) == 1


@respx.mock
def test_doctor_can_check_upstream_connectivity(tmp_path: Path) -> None:
    respx.post("https://api.test/info").mock(return_value=httpx.Response(200, json=[]))
    report = run_doctor(
        tmp_path,
        Settings(api_url="https://api.test/info", output_dir=tmp_path, cache_dir=tmp_path),
        check_network=True,
    )
    check = next(item for item in report["checks"] if item["name"] == "upstream_connectivity")
    assert check["status"] == "pass"
