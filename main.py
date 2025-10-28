"""Command line entry point for AutoBet BL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from autobet_bl.config import AutoBetConfig
from autobet_bl.presentation.formatter import format_prediction
from autobet_bl.services.predictor import FixtureContext, Predictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AutoBet BL Predictor")
    parser.add_argument(
        "--fixture-file",
        type=Path,
        help="Path to a JSON file describing the fixture context",
    )
    parser.add_argument(
        "--bankroll",
        type=float,
        default=1000.0,
        help="Current bankroll for stake sizing",
    )
    return parser.parse_args()


def load_fixture(path: Path, bankroll: float) -> FixtureContext:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    kickoff = datetime.fromisoformat(payload["kickoff"])
    return FixtureContext(
        fixture_id=payload["fixture_id"],
        home_team=payload["home_team"],
        away_team=payload["away_team"],
        kickoff=kickoff,
        league=payload["league"],
        season=payload["season"],
        odds=payload.get("odds", {}),
        data_quality=payload.get("data_quality", "B"),
        lineup_confidence=payload.get("lineup_confidence", 0.8),
        expected_goals_home=payload.get("expected_goals_home", 1.6),
        expected_goals_away=payload.get("expected_goals_away", 1.2),
        covariance=payload.get("covariance", 0.05),
        bankroll=bankroll,
        coach_notes=payload.get("coach_notes"),
        player_notes=payload.get("player_notes"),
        rest_days_home=payload.get("rest_days_home"),
        rest_days_away=payload.get("rest_days_away"),
    )


def default_fixture(bankroll: float) -> FixtureContext:
    return FixtureContext(
        fixture_id=12345,
        home_team="FC Beispiel",
        away_team="SV Demo",
        kickoff=datetime.utcnow(),
        league="Bundesliga",
        season=2025,
        odds={
            "1X2": {"1": 1.95, "X": 3.5, "2": 3.8},
            "Over/Under 2.5": {"Over 2.5": 1.9, "Under 2.5": 1.95},
            "BTTS": {"Yes": 1.85, "No": 1.95},
        },
        bankroll=bankroll,
        coach_notes="Coach seit 10 Spielen ungeschlagen",
        player_notes="Stammkeeper fit, Mittelstürmer fraglich (60%)",
        rest_days_home=6,
        rest_days_away=4,
    )


def main() -> None:
    args = parse_args()
    config = AutoBetConfig()
    predictor = Predictor(config)

    if args.fixture_file:
        fixture = load_fixture(args.fixture_file, args.bankroll)
    else:
        fixture = default_fixture(args.bankroll)

    result = predictor.predict_fixture(fixture)
    print(format_prediction(result))


if __name__ == "__main__":
    main()
