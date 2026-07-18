import httpx
import pytest

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
