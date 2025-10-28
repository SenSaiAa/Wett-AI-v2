"""Local caching utilities for API responses and derived datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """Represents an item stored in the cache."""

    payload: Dict[str, Any]
    timestamp: datetime

    def is_expired(self, ttl: timedelta) -> bool:
        return datetime.utcnow() - self.timestamp > ttl


class JsonCache:
    """A light-weight JSON cache stored on disk."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        sanitized = key.replace("/", "_")
        return self.root / f"{sanitized}.json"

    def get(self, key: str, ttl: timedelta) -> Optional[CacheEntry]:
        path = self._path_for(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            entry = CacheEntry(payload=raw["payload"], timestamp=datetime.fromisoformat(raw["timestamp"]))
        except (ValueError, KeyError):
            return None
        if entry.is_expired(ttl):
            return None
        return entry

    def set(self, key: str, payload: Dict[str, Any]) -> CacheEntry:
        path = self._path_for(key)
        entry = CacheEntry(payload=payload, timestamp=datetime.utcnow())
        with path.open("w", encoding="utf-8") as fh:
            json.dump({"payload": payload, "timestamp": entry.timestamp.isoformat()}, fh)
        return entry


__all__ = ["JsonCache", "CacheEntry"]
