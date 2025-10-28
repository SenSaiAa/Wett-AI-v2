"""Configuration models for AutoBet BL system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional


@dataclass(frozen=True)
class ApiConfig:
    """Holds configuration for API-Football access and budgeting."""

    base_url: str = "https://v3.football.api-sports.io"
    api_key: Optional[str] = None
    soft_cap: int = 7200
    hard_cap: int = 7450
    daily_limit: int = 7500
    cache_dir: Path = Path(".cache/api_football")
    timeout: int = 20


@dataclass(frozen=True)
class CachePolicy:
    """Defines caching and refresh policies for data refresh windows."""

    historical_start_season: int = 2020
    historical_end_season: int = 2025
    refresh_offsets: tuple[timedelta, ...] = (
        timedelta(hours=48),
        timedelta(hours=24),
        timedelta(hours=6),
        timedelta(hours=1),
        timedelta(minutes=15),
    )
    live_delta_window: timedelta = timedelta(days=2)
    cache_ttl: timedelta = timedelta(days=1)


@dataclass(frozen=True)
class ModelingConfig:
    """Configuration for the probabilistic models used for pricing."""

    max_goals: int = 8
    fractional_kelly: float = 0.25
    kelly_cap: float = 0.02
    margin_buffer: float = 0.02
    calibration_enabled: bool = True
    default_calibration_temperature: float = 1.0


@dataclass(frozen=True)
class LoggingConfig:
    """Configuration for logging destinations and retention."""

    log_dir: Path = Path("logs")
    jsonl_dir: Path = Path("logs/jsonl")
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5


@dataclass(frozen=True)
class AutoBetConfig:
    """Top level configuration container for the application."""

    api: ApiConfig = field(default_factory=ApiConfig)
    cache_policy: CachePolicy = field(default_factory=CachePolicy)
    modeling: ModelingConfig = field(default_factory=ModelingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    model_version: str = "1.0.0"
    data_cutoff: str = "2025-06-01"

    def to_dict(self) -> Dict[str, object]:
        return {
            "api": self.api.__dict__,
            "cache_policy": self.cache_policy.__dict__,
            "modeling": self.modeling.__dict__,
            "logging": self.logging.__dict__,
            "model_version": self.model_version,
            "data_cutoff": self.data_cutoff,
        }
