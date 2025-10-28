"""Formatting utilities to present prediction results."""

from __future__ import annotations

from typing import Dict, List

from ..markets.value import MarketSelection
from ..services.predictor import PredictionResult


def format_selection(selection: MarketSelection) -> str:
    bookmaker = f", Quote: {selection.bookmaker_odds:.2f}" if selection.bookmaker_odds else ""
    highlight = f" [{selection.highlight}]" if selection.highlight else ""
    value = " VALUE" if selection.is_value else ""
    stake = f", Einsatz: {selection.stake:.2f}" if selection.stake > 0 else ""
    return (
        f"- {selection.option}: {selection.probability * 100:.2f}% (faire Quote {selection.fair_odds:.2f}{bookmaker})"
        f"{highlight}{value}{stake}"
    )


def format_market(name: str, selections: Dict[str, MarketSelection]) -> str:
    lines = [f"Markt: {name}"]
    ordered = sorted(selections.values(), key=lambda s: s.probability, reverse=True)
    for selection in ordered:
        lines.append(format_selection(selection))
    return "\n".join(lines)


def format_prediction(result: PredictionResult) -> str:
    header = (
        f"Fixture {result.fixture.fixture_id}: {result.fixture.home_team} vs {result.fixture.away_team}"
        f" ({result.fixture.league} {result.fixture.season})\n"
        f"Modell-Version: {result.model_version} | Daten-Cutoff: {result.data_cutoff}"
    )

    rationale: List[str] = ["Begründung:"]
    if result.fixture.coach_notes:
        rationale.append(f"- Coach: {result.fixture.coach_notes}")
    if result.fixture.player_notes:
        rationale.append(f"- Spieler: {result.fixture.player_notes}")
    if result.fixture.rest_days_home is not None and result.fixture.rest_days_away is not None:
        rationale.append(
            f"- Resttage: Heim {result.fixture.rest_days_home}, Auswärts {result.fixture.rest_days_away}"
        )

    markets_text = "\n\n".join(
        format_market(name, selections) for name, selections in result.markets.items()
    )

    best_prob = result.best_probability
    best_prob_line = (
        f"Beste Gesamt-Option: {best_prob[1]} ({best_prob[0]}) mit {best_prob[2].probability * 100:.2f}%"
    )

    if result.best_value:
        best_value_line = (
            f"Bester Value-Pick: {result.best_value[1]} ({result.best_value[0]}) zu Quote {result.best_value[2].bookmaker_odds:.2f}"
        )
    else:
        best_value_line = "Kein Value-Pick identifiziert."

    return "\n\n".join(
        [
            header,
            markets_text,
            best_prob_line,
            best_value_line,
            "\n".join(rationale) if len(rationale) > 1 else "",
        ]
    ).strip()


__all__ = ["format_prediction"]
