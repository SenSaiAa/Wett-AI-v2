"""Staking adjustments based on data quality and lineup confidence."""

from __future__ import annotations

from dataclasses import dataclass

from ..data.validation import DataQuality


@dataclass
class RiskContext:
    bankroll: float
    data_quality: str
    lineup_confidence: float

    def quality_multiplier(self) -> float:
        quality_map = {
            DataQuality.A: 1.0,
            DataQuality.B: 0.85,
            DataQuality.C: 0.5,
            DataQuality.D: 0.0,
        }
        return quality_map.get(self.data_quality, 0.5) * max(min(self.lineup_confidence, 1.0), 0.0)


__all__ = ["RiskContext"]
