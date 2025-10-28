"""API-Football client with request budgeting, caching, and delta refresh logic."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, Optional

import requests

from ..config import ApiConfig, CachePolicy
from .cache import JsonCache

LOGGER = logging.getLogger(__name__)


@dataclass
class BudgetState:
    """Tracks the API budget and pending work beyond the limit."""

    used: int = 0
    queued_jobs: list[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.queued_jobs is None:
            self.queued_jobs = []

    def remaining(self, config: ApiConfig) -> int:
        return max(config.daily_limit - self.used, 0)

    def can_execute(self, config: ApiConfig) -> bool:
        return self.used < config.hard_cap

    def register(self, count: int = 1) -> None:
        self.used += count


class FootballApiClient:
    """Thin wrapper around API-Football with caching and budget enforcement."""

    def __init__(self, api_config: ApiConfig, cache_policy: CachePolicy) -> None:
        self.api_config = api_config
        self.cache_policy = cache_policy
        self.cache = JsonCache(api_config.cache_dir)
        self.budget = BudgetState()

    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, ttl: Optional[timedelta] = None) -> Dict[str, Any]:
        ttl = ttl or self.cache_policy.cache_ttl
        cache_key = f"{endpoint}:{sorted((params or {}).items())}"
        cached = self.cache.get(cache_key, ttl)
        if cached:
            LOGGER.debug("cache hit for %s", cache_key)
            return cached.payload

        if not self.budget.can_execute(self.api_config):
            LOGGER.warning("API budget exhausted, queueing job %s", cache_key)
            self.budget.queued_jobs.append({"endpoint": endpoint, "params": params})
            raise RuntimeError("API budget exhausted")

        headers = {"x-apisports-key": self.api_config.api_key} if self.api_config.api_key else {}
        response = requests.get(
            f"{self.api_config.base_url}/{endpoint}",
            headers=headers,
            params=params,
            timeout=self.api_config.timeout,
        )
        self.budget.register()
        LOGGER.info("API request %s remaining=%d", endpoint, self.budget.remaining(self.api_config))
        response.raise_for_status()
        payload = response.json()
        self.cache.set(cache_key, payload)
        return payload

    def resume_queue(self) -> Iterable[Dict[str, Any]]:
        """Return queued jobs for processing when the next window opens."""
        queued, self.budget.queued_jobs = self.budget.queued_jobs, []
        LOGGER.info("Resuming %d queued jobs", len(queued))
        return queued

    def fetch_fixtures(self, date_from: datetime, date_to: datetime) -> Dict[str, Any]:
        params = {
            "league": "Bundesliga",
            "from": date_from.strftime("%Y-%m-%d"),
            "to": date_to.strftime("%Y-%m-%d"),
        }
        return self._request("fixtures", params=params)

    def fetch_fixture_details(self, fixture_id: int) -> Dict[str, Any]:
        return self._request(f"fixtures?id={fixture_id}")

    def fetch_odds(self, fixture_id: int) -> Dict[str, Any]:
        return self._request("odds", params={"fixture": fixture_id})

    def fetch_injuries(self, fixture_id: int) -> Dict[str, Any]:
        return self._request("injuries", params={"fixture": fixture_id})

    def fetch_lineups(self, fixture_id: int) -> Dict[str, Any]:
        return self._request("fixtures/lineups", params={"fixture": fixture_id}, ttl=timedelta(minutes=15))

    def fetch_standings(self, season: int, league_id: int) -> Dict[str, Any]:
        return self._request("standings", params={"season": season, "league": league_id}, ttl=timedelta(hours=6))

    def sleep_until_budget_resets(self, reset_hour: int = 0) -> None:  # pragma: no cover - scheduling guard
        now = datetime.utcnow()
        reset = now.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
        if reset <= now:
            reset += timedelta(days=1)
        wait_seconds = (reset - now).total_seconds()
        LOGGER.info("Sleeping %.0f seconds until API budget resets", wait_seconds)
        time.sleep(wait_seconds)


__all__ = ["FootballApiClient", "BudgetState"]
