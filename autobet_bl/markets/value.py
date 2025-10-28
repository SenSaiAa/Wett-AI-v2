"""Value detection and odds utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class MarketSelection:
    market: str
    option: str
    probability: float
    fair_odds: float
    bookmaker_odds: Optional[float]
    is_value: bool
    highlight: Optional[str]
    stake: float


def fair_odds(probability: float) -> float:
    probability = max(min(probability, 0.9999), 1e-4)
    return 1 / probability


def compute_highlight(probability: float) -> Optional[str]:
    pct = probability * 100
    if pct >= 65:
        return "Sehr wahrscheinlich"
    if pct >= 55:
        return "Wahrscheinlich"
    return None


def detect_value(
    market: str,
    probabilities: Dict[str, float],
    bookmaker_odds: Optional[Dict[str, float]],
    kelly_fraction: float,
    kelly_cap: float,
    margin_buffer: float,
    bankroll: float,
) -> Dict[str, MarketSelection]:
    selections: Dict[str, MarketSelection] = {}
    bookmaker_odds = bookmaker_odds or {}
    for option, probability in probabilities.items():
        odds = bookmaker_odds.get(option)
        fair = fair_odds(probability)
        is_value = False
        stake = 0.0
        if odds is not None:
            threshold = fair * (1 + margin_buffer)
            if odds > threshold:
                is_value = True
                edge = (odds * probability) - 1
                if edge > 0:
                    kelly = edge / (odds - 1)
                    stake = min(bankroll * kelly_fraction * kelly, bankroll * kelly_cap)
        highlight = compute_highlight(probability)
        selections[option] = MarketSelection(
            market=market,
            option=option,
            probability=probability,
            fair_odds=fair,
            bookmaker_odds=odds,
            is_value=is_value,
            highlight=highlight,
            stake=stake,
        )
    return selections


__all__ = ["MarketSelection", "detect_value", "fair_odds", "compute_highlight"]
