from __future__ import annotations

from typing import Any

from .utils import decimal_or_none


class APIResponseValidationError(ValueError):
    pass


def safe_summary(data: object) -> str:
    if isinstance(data, dict):
        return f"object keys={sorted(map(str, data.keys()))[:10]}"
    if isinstance(data, list):
        return f"array length={len(data)}"
    return type(data).__name__


def _error(payload_type: str, message: str, data: object) -> APIResponseValidationError:
    return APIResponseValidationError(f"{payload_type}: {message} ({safe_summary(data)})")


def validate_perp_dexs(data: object) -> list[Any]:
    if not isinstance(data, list):
        raise _error("perpDexs", "expected an array", data)
    for item in data:
        if item is not None and not isinstance(item, (str, dict)):
            raise _error("perpDexs", "entries must be strings, objects, or null", data)
        if isinstance(item, dict) and "name" in item and not isinstance(item["name"], str):
            raise _error("perpDexs", "object name must be a string", item)
    return data


def validate_meta_contexts(data: object, payload_type: str) -> list[Any]:
    if not isinstance(data, list) or len(data) != 2:
        raise _error(payload_type, "expected [metadata, contexts]", data)
    metadata, contexts = data
    if not isinstance(metadata, dict) or not isinstance(metadata.get("universe", []), list):
        raise _error(payload_type, "metadata must contain an array universe", metadata)
    if not isinstance(contexts, list):
        raise _error(payload_type, "contexts must be an array", contexts)
    if payload_type == "spotMetaAndAssetCtxs" and not isinstance(metadata.get("tokens", []), list):
        raise _error(payload_type, "spot metadata tokens must be an array", metadata)
    return data


def validate_candles(data: object) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise _error("candleSnapshot", "expected an array", data)
    candles: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise _error("candleSnapshot", "candle must be an object", item)
        if not isinstance(item.get("t"), int) or decimal_or_none(item.get("c")) is None:
            raise _error("candleSnapshot", "candle requires integer t and numeric c", item)
        candles.append(item)
    return candles


def validate_l2_book(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise _error("l2Book", "expected an object", data)
    levels = data.get("levels")
    if not isinstance(levels, list) or len(levels) < 2:
        raise _error("l2Book", "levels must contain bid and ask arrays", data)
    for side in levels[:2]:
        if not isinstance(side, list):
            raise _error("l2Book", "each book side must be an array", side)
        for level in side:
            if not isinstance(level, dict):
                raise _error("l2Book", "levels must be objects", level)
            if decimal_or_none(level.get("px")) is None or decimal_or_none(level.get("sz")) is None:
                raise _error("l2Book", "level requires numeric px and sz", level)
    return data
