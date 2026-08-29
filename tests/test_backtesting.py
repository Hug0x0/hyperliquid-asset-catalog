import pytest

from hl_asset_catalog.backtesting import backtest_benchmark


def history() -> list[dict[str, object]]:
    rows = []
    for day, prices in enumerate(((100, 100), (101, 99), (102, 100), (103, 102)), start=1):
        for symbol, close, volume in (("A", prices[0], 1000), ("B", prices[1], 100)):
            rows.append(
                {
                    "date": f"2026-01-0{day}",
                    "symbol": symbol,
                    "close": close,
                    "volume": volume,
                    "spread_bps": 1,
                    "slippage_bps": 1,
                }
            )
    return rows


def test_backtest_accounts_for_turnover_and_costs() -> None:
    result = backtest_benchmark(history(), symbols=["A", "B"], rebalance_every=2)
    assert result["observations"] == 4
    assert result["total_turnover"] > 0
    assert result["total_transaction_cost"] > 0
    assert result["daily"][0]["net_return"] < 0
    assert "not a forecast" in result["disclaimer"]


def test_liquidity_weighting_uses_only_current_and_past_rows() -> None:
    result = backtest_benchmark(
        history(), symbols=["A", "B"], weighting="liquidity", rebalance_every=1
    )
    first_weights = result["daily"][0]["weights"]
    assert first_weights["A"] == pytest.approx(10 / 11)
    assert first_weights["B"] == pytest.approx(1 / 11)
