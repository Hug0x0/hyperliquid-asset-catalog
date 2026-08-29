import asyncio
import json
from typing import Any

import httpx
import pytest

from hl_asset_catalog.api_validation import APIResponseValidationError
from hl_asset_catalog.config import Settings
from hl_asset_catalog.hyperliquid_client import HyperliquidClient


@pytest.mark.asyncio
async def test_perp_dex_discovery_is_dynamic(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == "test-agent"
        return httpx.Response(
            200,
            json=[None, {"name": "xyz", "fullName": "XYZ"}, "foo"],
            headers={"content-type": "application/json"},
        )

    settings = Settings(cache_dir=tmp_path, user_agent="test-agent", max_retries=1)
    async with HyperliquidClient(settings, transport=httpx.MockTransport(handler)) as client:
        assert await client.perp_dexs() == ["", "xyz", "foo"]


@pytest.mark.asyncio
async def test_market_data_payloads(tmp_path) -> None:
    payloads: list[dict[str, Any]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        payloads.append(payload)
        data = (
            [{"t": 1, "c": "100"}]
            if payload["type"] == "candleSnapshot"
            else {"coin": "xyz:NVDA", "levels": [[], []]}
        )
        return httpx.Response(200, json=data, headers={"content-type": "application/json"})

    settings = Settings(cache_dir=tmp_path, max_retries=1)
    async with HyperliquidClient(settings, transport=httpx.MockTransport(handler)) as client:
        candles = await client.candle_snapshot("xyz:NVDA", interval="1d", start_time=1, end_time=2)
        book = await client.l2_book("xyz:NVDA")
    assert candles[0]["c"] == "100"
    assert book["coin"] == "xyz:NVDA"
    assert payloads[0]["req"]["coin"] == "xyz:NVDA"
    assert payloads[1] == {"type": "l2Book", "coin": "xyz:NVDA"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload_type", "response"),
    [
        ("candleSnapshot", [{"t": "not-an-int", "c": "100"}]),
        ("l2Book", {"levels": "malformed"}),
    ],
)
async def test_market_data_rejects_malformed_responses(
    tmp_path, payload_type: str, response: object
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response, headers={"content-type": "application/json"})

    settings = Settings(cache_dir=tmp_path, max_retries=1)
    async with HyperliquidClient(settings, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(APIResponseValidationError, match=payload_type):
            if payload_type == "candleSnapshot":
                await client.candle_snapshot("BTC", interval="1d", start_time=1, end_time=2)
            else:
                await client.l2_book("BTC")


@pytest.mark.asyncio
async def test_market_data_accepts_forward_compatible_fields(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"levels": [[], []], "futureField": {"version": 2}},
            headers={"content-type": "application/json"},
        )

    settings = Settings(cache_dir=tmp_path, max_retries=1)
    async with HyperliquidClient(settings, transport=httpx.MockTransport(handler)) as client:
        book = await client.l2_book("BTC")
    assert book["futureField"] == {"version": 2}


@pytest.mark.asyncio
async def test_cache_quarantines_corrupt_json(tmp_path) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=[None, "xyz"], headers={"content-type": "application/json"})

    settings = Settings(cache_dir=tmp_path, max_retries=1)
    async with HyperliquidClient(settings, transport=httpx.MockTransport(handler)) as client:
        await client.perp_dexs()
        cache_path = next((tmp_path / "api").glob("*.json"))
        cache_path.write_text("{broken")
        await client.perp_dexs()
        assert client.cache_corruptions
    assert calls == 2
    assert list((tmp_path / "api").glob("*.corrupt-*.json"))


@pytest.mark.asyncio
async def test_concurrent_identical_requests_share_one_cache_write(tmp_path) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return httpx.Response(200, json=[None, "xyz"], headers={"content-type": "application/json"})

    settings = Settings(cache_dir=tmp_path, max_retries=1)
    async with HyperliquidClient(settings, transport=httpx.MockTransport(handler)) as client:
        left, right = await asyncio.gather(client.perp_dexs(), client.perp_dexs())
    assert left == right
    assert calls == 1


@pytest.mark.asyncio
async def test_rate_limit_honors_retry_after(tmp_path) -> None:
    calls = 0
    waits: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"retry-after": "0.01"})
        return httpx.Response(200, json=[None, "xyz"], headers={"content-type": "application/json"})

    async def sleep(delay: float) -> None:
        waits.append(delay)

    settings = Settings(cache_dir=tmp_path, max_retries=2)
    async with HyperliquidClient(
        settings, transport=httpx.MockTransport(handler), sleep=sleep
    ) as client:
        assert await client.perp_dexs() == ["", "xyz"]
        assert client.rate_limit_responses == 1
        assert client.request_weight == 2
    assert 0.01 in waits
