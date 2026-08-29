from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .api_validation import (
    validate_candles,
    validate_l2_book,
    validate_meta_contexts,
    validate_perp_dexs,
)
from .config import Settings
from .utils import atomic_json, cache_key


class HyperliquidAPIError(RuntimeError):
    pass


class HyperliquidClient:
    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.request_count = 0
        self.cache_hits = 0
        self.cache_corruptions: list[str] = []
        self.stale_cache_fallbacks: list[str] = []
        self.errors: list[str] = []
        self.endpoints: set[str] = set()
        self._semaphore = asyncio.Semaphore(settings.concurrency)
        self._cache_locks: dict[str, asyncio.Lock] = {}
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
        lock = self._cache_locks.setdefault(path.name, asyncio.Lock())
        async with lock:
            cached = self._read_cache(path)
            if (
                not force_refresh
                and cached is not None
                and time.time() - path.stat().st_mtime < self.settings.api_cache_ttl
            ):
                self.cache_hits += 1
                return cached
            return await self._request_and_cache(payload, path, cached)

    def _read_cache(self, path: Path) -> Any | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            quarantined = path.with_suffix(f".corrupt-{int(time.time())}.json")
            path.replace(quarantined)
            self.cache_corruptions.append(f"{path.name}: {type(exc).__name__}")
            return None

    async def _request_and_cache(
        self, payload: dict[str, Any], path: Path, stale: Any | None
    ) -> Any:
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
                    atomic_json(path, data, pretty=False)
                    return data
        except Exception as exc:
            self.errors.append(f"{payload.get('type')}: {exc}")
            if stale is not None:
                self.stale_cache_fallbacks.append(str(payload.get("type", "unknown")))
                return stale
            raise

    async def perp_dexs(self, *, force_refresh: bool = False) -> list[str]:
        data = await self.post({"type": "perpDexs"}, force_refresh=force_refresh)
        data = validate_perp_dexs(data)
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
        return validate_meta_contexts(data, "metaAndAssetCtxs")

    async def spot_meta_contexts(self, *, force_refresh: bool = False) -> list[Any]:
        data = await self.post({"type": "spotMetaAndAssetCtxs"}, force_refresh=force_refresh)
        return validate_meta_contexts(data, "spotMetaAndAssetCtxs")

    async def candle_snapshot(
        self,
        coin: str,
        *,
        interval: str,
        start_time: int,
        end_time: int,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        data = await self.post(
            {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": interval,
                    "startTime": start_time,
                    "endTime": end_time,
                },
            },
            force_refresh=force_refresh,
        )
        return validate_candles(data)

    async def l2_book(self, coin: str, *, force_refresh: bool = False) -> dict[str, Any]:
        data = await self.post({"type": "l2Book", "coin": coin}, force_refresh=force_refresh)
        return validate_l2_book(data)
