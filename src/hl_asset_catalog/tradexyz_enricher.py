from __future__ import annotations

import hashlib
import json
import time
import urllib.robotparser
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .models import Instrument
from .utils import atomic_json

REQUIRED_HEADERS = {"symbol"}


def parse_tables(html: str) -> tuple[list[dict[str, str]], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True).lower() for cell in table.find_all("th")]
        if not REQUIRED_HEADERS.issubset(headers):
            continue
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all("td")]
            if cells and len(cells) == len(headers):
                rows.append(dict(zip(headers, cells, strict=True)))
    warnings = [] if rows else ["documentation structure changed: no symbol table found"]
    return rows, warnings


class TradeXYZEnricher:
    """Opt-in, robots-aware enrichment for existing API instruments."""

    def __init__(self, cache_dir: Path = Path(".cache/hl_asset_catalog/docs")) -> None:
        self.cache_dir = cache_dir

    def enrich(
        self, assets: Iterable[Instrument], rows: Iterable[dict[str, str]] = ()
    ) -> list[Instrument]:
        metadata = {row["symbol"].upper(): row for row in rows if row.get("symbol")}
        result: list[Instrument] = []
        for asset in assets:
            row = metadata.get(asset.canonical_symbol.upper())
            if not row:
                result.append(asset)
                continue
            updates: dict[str, object] = {
                "source": list(dict.fromkeys([*asset.source, "tradexyz_docs"]))
            }
            if row.get("name"):
                updates["display_name"] = row["name"]
            if row.get("exchange"):
                updates["reference_exchange"] = row["exchange"]
            result.append(asset.model_copy(update=updates))
        return result

    def monitor(self, url: str, *, ttl_seconds: int = 86_400) -> dict[str, object]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("documentation URL must use HTTP(S)")
        robots = urllib.robotparser.RobotFileParser(urljoin(url, "/robots.txt"))
        robots.read()
        if not robots.can_fetch("hl-asset-catalog/0.1", url):
            raise PermissionError(f"robots.txt disallows {url}")
        cache_path = self.cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}.json"
        cached: dict[str, object] = {}
        if cache_path.exists():
            loaded = json.loads(cache_path.read_text(encoding="utf-8"))
            cached = loaded if isinstance(loaded, dict) else {}
            if time.time() - float(cached.get("fetched_at", 0)) < ttl_seconds:
                return {**cached, "cache_hit": True}
        response = httpx.get(url, headers={"User-Agent": "hl-asset-catalog/0.1"}, timeout=20)
        response.raise_for_status()
        rows, warnings = parse_tables(response.text)
        fingerprint = hashlib.sha256(
            json.dumps(sorted(rows[0].keys()) if rows else []).encode()
        ).hexdigest()
        if cached.get("header_fingerprint") not in {None, fingerprint}:
            warnings.append("documentation table headers changed")
        result: dict[str, object] = {
            "schema_version": "1.0",
            "url": url,
            "fetched_at": time.time(),
            "header_fingerprint": fingerprint,
            "rows": rows,
            "warnings": warnings,
            "cache_hit": False,
        }
        atomic_json(cache_path, result)
        return result
