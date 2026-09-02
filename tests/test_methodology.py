from pathlib import Path

import pytest

from hl_asset_catalog.methodology import cap_weights, load_methodology

ROOT = Path(__file__).parents[1]


def test_loads_versioned_equal_weight_methodology() -> None:
    method = load_methodology(ROOT / "config/benchmark_methodologies.yaml", "equal-weight")
    assert method["version"] == "1.0.0"
    assert method["weighting"] == "equal"


def test_capped_weights_are_normalized() -> None:
    result = cap_weights({"A": 0.8, "B": 0.1, "C": 0.1}, 0.4)
    assert result == pytest.approx({"A": 0.4, "B": 0.3, "C": 0.3})
    assert sum(result.values()) == pytest.approx(1)


def test_rejects_infeasible_cap() -> None:
    with pytest.raises(ValueError, match="infeasible"):
        cap_weights({"A": 0.5, "B": 0.5}, 0.4)
