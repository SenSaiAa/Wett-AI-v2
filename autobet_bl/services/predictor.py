"""Prediction pipeline orchestrating data, modeling, and presentation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple

from ..config import AutoBetConfig
from ..data.validation import DataQuality
from ..logging_config import configure_logging
from ..markets.value import MarketSelection, detect_value
from ..modeling.calibrator import TemperatureCalibrator
from ..modeling.poisson import (
    MarketProbabilities,
    PoissonParameters,
    aggregate_markets,
    bivariate_poisson_matrix,
)
from ..risk.staking import RiskContext

LOGGER = logging.getLogger(__name__)


@dataclass
class FixtureContext:
    fixture_id: int
    home_team: str
    away_team: str
    kickoff: datetime
    league: str
    season: int
    odds: Dict[str, Dict[str, float]]
    data_quality: str = DataQuality.B
    lineup_confidence: float = 0.8
    expected_goals_home: float = 1.6
    expected_goals_away: float = 1.2
    covariance: float = 0.05
    bankroll: float = 1000.0
    coach_notes: Optional[str] = None
    player_notes: Optional[str] = None
    rest_days_home: Optional[int] = None
    rest_days_away: Optional[int] = None


@dataclass
class PredictionResult:
    fixture: FixtureContext
    markets: Dict[str, Dict[str, MarketSelection]]
    probabilities: MarketProbabilities
    best_probability: Tuple[str, str, MarketSelection]
    best_value: Optional[Tuple[str, str, MarketSelection]]
    model_version: str
    data_cutoff: str


class Predictor:
    """Main orchestrator for generating predictions."""

    def __init__(self, config: AutoBetConfig) -> None:
        self.config = config
        configure_logging(config)
        LOGGER.info("Predictor initialised", extra={"model_version": config.model_version})

    def _calibrator(self) -> TemperatureCalibrator:
        return TemperatureCalibrator(self.config.modeling.default_calibration_temperature)

    def predict_fixture(self, fixture: FixtureContext) -> PredictionResult:
        LOGGER.info(
            "Predicting fixture",
            extra={
                "fixture_id": fixture.fixture_id,
                "home_team": fixture.home_team,
                "away_team": fixture.away_team,
            },
        )
        params = PoissonParameters(
            lambda_home=fixture.expected_goals_home,
            lambda_away=fixture.expected_goals_away,
            covariance=fixture.covariance,
        )
        matrix = bivariate_poisson_matrix(params, self.config.modeling.max_goals)
        calibrator = self._calibrator()
        probabilities = aggregate_markets(matrix, calibrator, self.config.modeling.max_goals)

        risk_context = RiskContext(
            bankroll=fixture.bankroll,
            data_quality=fixture.data_quality,
            lineup_confidence=fixture.lineup_confidence,
        )
        multiplier = risk_context.quality_multiplier()

        markets: Dict[str, Dict[str, MarketSelection]] = {}

        def record_market(market: str, probs: Dict[str, float]) -> None:
            bookmaker = fixture.odds.get(market)
            selections = detect_value(
                market,
                probs,
                bookmaker,
                kelly_fraction=self.config.modeling.fractional_kelly * multiplier,
                kelly_cap=self.config.modeling.kelly_cap,
                margin_buffer=self.config.modeling.margin_buffer,
                bankroll=fixture.bankroll,
            )
            markets[market] = selections

        record_market("1X2", probabilities.one_x_two)
        record_market("Draw No Bet", probabilities.draw_no_bet)
        record_market("Double Chance", probabilities.double_chance)
        for line, probs in probabilities.over_under.items():
            record_market(f"Over/Under {line}", {f"Over {line}": probs["over"], f"Under {line}": probs["under"]})
        for team, totals in probabilities.team_totals.items():
            for line, probs in totals.items():
                record_market(
                    f"{team.title()} Team Total {line}",
                    {f"Over {line}": probs["over"], f"Under {line}": probs["under"]},
                )
        record_market("BTTS", {"Yes": probabilities.btts["yes"], "No": probabilities.btts["no"]})
        for line, probs in probabilities.asian_handicap.items():
            record_market(
                f"Asian Handicap {line:+.2f}",
                {"Home": probs["home"], "Away": probs["away"]},
            )
        record_market("Correct Score", {score: prob for score, prob in probabilities.correct_score})
        record_market("HT 1X2", probabilities.half_time["1x2"])
        record_market(
            "HT Over/Under 1.0",
            {"Over 1.0": probabilities.half_time["over_under_1.0"]["over"], "Under 1.0": probabilities.half_time["over_under_1.0"]["under"]},
        )
        record_market("Specials", probabilities.specials)

        best_probability = self._find_best_probability(markets)
        best_value = self._find_best_value(markets)

        LOGGER.info(
            "Prediction complete",
            extra={
                "fixture_id": fixture.fixture_id,
                "best_probability": best_probability[2].probability if best_probability else None,
                "best_value": best_value[2].probability if best_value else None,
            },
        )
        return PredictionResult(
            fixture=fixture,
            markets=markets,
            probabilities=probabilities,
            best_probability=best_probability,
            best_value=best_value,
            model_version=self.config.model_version,
            data_cutoff=self.config.data_cutoff,
        )

    def _find_best_probability(
        self, markets: Dict[str, Dict[str, MarketSelection]]
    ) -> Tuple[str, str, MarketSelection]:
        best = None
        for market, selections in markets.items():
            for option, selection in selections.items():
                if best is None or selection.probability > best[2].probability:
                    best = (market, option, selection)
        assert best is not None
        return best

    def _find_best_value(
        self, markets: Dict[str, Dict[str, MarketSelection]]
    ) -> Optional[Tuple[str, str, MarketSelection]]:
        best = None
        for market, selections in markets.items():
            for option, selection in selections.items():
                if not selection.is_value:
                    continue
                score = (selection.bookmaker_odds or 0) - selection.fair_odds
                if best is None or score > (best[2].bookmaker_odds or 0) - best[2].fair_odds:
                    best = (market, option, selection)
        return best


__all__ = ["Predictor", "FixtureContext", "PredictionResult"]
