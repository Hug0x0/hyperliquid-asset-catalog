from __future__ import annotations

import asyncio
from typing import Any

from .classification import Classifier
from .hyperliquid_client import HyperliquidClient
from .models import Instrument
from .normalization import normalize_perp, normalize_spot


async def discover_catalog(
    client: HyperliquidClient, classifier: Classifier, *, force_refresh: bool = False
) -> tuple[list[Instrument], list[str]]:
    dexes = await client.perp_dexs(force_refresh=force_refresh)
    results = await asyncio.gather(
        *(client.perp_meta_contexts(dex, force_refresh=force_refresh) for dex in dexes),
        return_exceptions=True,
    )
    assets: list[Instrument] = []
    errors: list[str] = []
    for dex_index, (dex, result) in enumerate(zip(dexes, results, strict=True)):
        if isinstance(result, BaseException):
            errors.append(f"DEX {dex or 'native'}: {result}")
            continue
        if not isinstance(result, list) or len(result) != 2:
            errors.append(f"DEX {dex or 'native'}: malformed response")
            continue
        meta, contexts = result
        universe = meta.get("universe", [])
        for index, item in enumerate(universe):
            ctx: dict[str, Any] = contexts[index] if index < len(contexts) else {}
            assets.append(
                classifier.classify(
                    normalize_perp(item, ctx, dex=dex, dex_index=dex_index, index=index)
                )
            )
    try:
        spot_meta, spot_contexts = await client.spot_meta_contexts(force_refresh=force_refresh)
        tokens = {int(t["index"]): t for t in spot_meta.get("tokens", [])}
        for index, market in enumerate(spot_meta.get("universe", [])):
            ctx = spot_contexts[index] if index < len(spot_contexts) else {}
            assets.append(classifier.classify(normalize_spot(market, ctx, tokens)))
    except Exception as exc:
        errors.append(f"Spot: {exc}")
    if not assets:
        raise RuntimeError("No catalog assets could be generated")
    return assets, errors
