from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .config import Settings
from .utils import cache_key


class HyperliquidAPIError(RuntimeError):
    pass


class HyperliquidClient:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.request_count = 0
        self.errors: list[str] = []
        self.endpoints: set[str] = set()
        self._semaphore = asyncio.Semaphore(settings.concurrency)
        self._client = httpx.AsyncClient(
            timeout=settings.timeout,
            headers={"User-Agent": settings.user_agent, "Content-Type": "application/json"},
            transport=transport,
        )

    async def __aenter__(self) -> HyperliquidClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._client.aclose()

    async def post(self, payload: dict[str, Any], *, force_refresh: bool = False) -> Any:
        path = self.settings.cache_dir / "api" / f"{cache_key(payload)}.json"
        if (
            not force_refresh
            and path.exists()
            and time.time() - path.stat().st_mtime < self.settings.api_cache_ttl
        ):
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self.settings.max_retries),
                wait=wait_random_exponential(multiplier=0.5, max=8),
                retry=retry_if_exception_type((httpx.HTTPError, HyperliquidAPIError)),
                reraise=True,
            ):
                with attempt:
                    async with self._semaphore:
                        self.request_count += 1
                        self.endpoints.add(self.settings.api_url)
                        response = await self._client.post(self.settings.api_url, json=payload)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    if "json" not in content_type:
                        raise HyperliquidAPIError(f"Unexpected Content-Type: {content_type}")
                    data = response.json()
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(data), encoding="utf-8")
                    return data
        except Exception as exc:
            self.errors.append(f"{payload.get('type')}: {exc}")
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
            raise

    async def perp_dexs(self, *, force_refresh: bool = False) -> list[str]:
        data = await self.post({"type": "perpDexs"}, force_refresh=force_refresh)
        if not isinstance(data, list):
            raise HyperliquidAPIError("perpDexs returned a non-list")
        names: list[str] = [""]
        for item in data:
            name = item.get("name") if isinstance(item, dict) else item
            if name:
                names.append(str(name))
        return names

    async def perp_meta_contexts(self, dex: str, *, force_refresh: bool = False) -> list[Any]:
        data = await self.post(
            {"type": "metaAndAssetCtxs", "dex": dex}, force_refresh=force_refresh
        )
        if not isinstance(data, list):
            raise HyperliquidAPIError("metaAndAssetCtxs returned a non-list")
        return data

    async def spot_meta_contexts(self, *, force_refresh: bool = False) -> list[Any]:
        data = await self.post({"type": "spotMetaAndAssetCtxs"}, force_refresh=force_refresh)
        if not isinstance(data, list):
            raise HyperliquidAPIError("spotMetaAndAssetCtxs returned a non-list")
        return data
