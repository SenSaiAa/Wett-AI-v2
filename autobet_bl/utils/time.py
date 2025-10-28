"""Time utilities for scheduling refresh windows."""

from __future__ import annotations

from datetime import datetime, timedelta


def within_window(kickoff: datetime, window: timedelta) -> bool:
    return datetime.utcnow() - kickoff <= window


__all__ = ["within_window"]
