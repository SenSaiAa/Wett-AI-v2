"""Probability calibration utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass
class TemperatureCalibrator:
    """Simple temperature scaling calibrator."""

    temperature: float = 1.0

    def transform(self, probability: float) -> float:
        probability = min(max(probability, 1e-6), 1 - 1e-6)
        logit = math.log(probability / (1 - probability))
        scaled = logit / max(self.temperature, 1e-6)
        return 1 / (1 + math.exp(-scaled))

    @classmethod
    def fit(cls, probs: Iterable[float], targets: Iterable[int]) -> "TemperatureCalibrator":
        probs_list = list(probs)
        targets_list = list(targets)
        if not probs_list:
            return cls(1.0)
        # Use a simple grid-search over plausible temperatures to avoid heavy dependencies.
        best_temp = 1.0
        best_loss = float("inf")
        for temp in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]:
            loss = 0.0
            for p, y in zip(probs_list, targets_list):
                calibrated = cls(temp).transform(p)
                loss -= y * math.log(calibrated) + (1 - y) * math.log(1 - calibrated)
            if loss < best_loss:
                best_loss = loss
                best_temp = temp
        return cls(best_temp)

    def to_tuple(self) -> Tuple[float]:
        return (self.temperature,)


__all__ = ["TemperatureCalibrator"]
