from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HL_CATALOG_", env_file=".env", extra="ignore")
    api_url: str = "https://api.hyperliquid.xyz/info"
    output_dir: Path = Path("output")
    cache_dir: Path = Path(".cache/hl_asset_catalog")
    timeout: float = 20.0
    max_retries: int = 4
    concurrency: int = 4
    weighted_request_budget: int = 1_000
    analytics_jitter_max: float = 0.05
    oracle_divergence_bps: float = 100.0
    abnormal_spread_bps: float = 50.0
    stale_candle_hours: float = 48.0
    api_cache_ttl: int = 60
    doc_cache_ttl: int = 86_400
    user_agent: str = "hl-asset-catalog/0.1"


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data
