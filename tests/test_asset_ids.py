import pytest

from hl_asset_catalog.utils import hip3_asset_id


def test_official_hip3_example() -> None:
    assert hip3_asset_id(1, 0) == 110_000


def test_asset_id_uses_dynamic_dex_index() -> None:
    assert hip3_asset_id(7, 42) == 170_042


@pytest.mark.parametrize("dex,index", [(0, 0), (1, -1), (1, 10_000)])
def test_asset_id_rejects_invalid_indices(dex: int, index: int) -> None:
    with pytest.raises(ValueError):
        hip3_asset_id(dex, index)
