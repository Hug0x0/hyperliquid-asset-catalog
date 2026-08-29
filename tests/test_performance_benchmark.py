import runpy
from pathlib import Path

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "benchmarks/catalog_performance.py"))


def test_catalog_performance_benchmark_stays_within_thresholds() -> None:
    result = MODULE["run_benchmark"]()
    assert result["instruments"] == MODULE["INSTRUMENTS"]
    assert result["total_seconds"] < MODULE["MAX_TOTAL_SECONDS"]
    assert result["peak_memory_mib"] < MODULE["MAX_PEAK_MIB"]
