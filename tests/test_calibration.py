from pathlib import Path

import pytest

from hl_asset_catalog.calibration import evaluate_calibration, rank_correlation

ROOT = Path(__file__).parents[1]


def test_calibration_fixture_is_stable_and_monotonic() -> None:
    report = evaluate_calibration(ROOT / "config/score_calibration.json")
    assert report == {
        "schema_version": "1.0",
        "score_version": "1.0.0",
        "cases": 5,
        "rank_correlation": 1.0,
        "bounds_valid": True,
        "missing_data_monotonic": True,
    }


def test_rank_correlation_rejects_incompatible_series() -> None:
    with pytest.raises(ValueError):
        rank_correlation([1], [1])
