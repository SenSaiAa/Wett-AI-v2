"""Data validation helpers for fixtures and related datasets."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List, Tuple

LOGGER = logging.getLogger(__name__)


class DataQuality:
    """Represents quality levels for downstream decision-making."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


def detect_duplicates(fixture_ids: Iterable[int]) -> List[int]:
    seen = set()
    duplicates = []
    for fixture_id in fixture_ids:
        if fixture_id in seen:
            duplicates.append(fixture_id)
        else:
            seen.add(fixture_id)
    if duplicates:
        LOGGER.warning("Duplicate fixtures detected: %s", duplicates)
    return duplicates


def validate_fixture_dates(fixtures: Iterable[Tuple[int, str]]) -> List[int]:
    """Validate fixture timestamps are ISO formatted and in UTC."""

    invalid = []
    for fixture_id, kickoff in fixtures:
        try:
            dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
        except ValueError:
            invalid.append(fixture_id)
            continue
        if dt.tzinfo is None:
            invalid.append(fixture_id)
    if invalid:
        LOGGER.error("Fixtures with invalid kickoff times: %s", invalid)
    return invalid


__all__ = ["DataQuality", "detect_duplicates", "validate_fixture_dates"]
