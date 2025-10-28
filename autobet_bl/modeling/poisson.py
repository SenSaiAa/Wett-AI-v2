"""Bivariate Poisson scoreline modeling and derived market probabilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .calibrator import TemperatureCalibrator


@dataclass
class PoissonParameters:
    """Parameters describing team scoring intensities."""

    lambda_home: float
    lambda_away: float
    covariance: float = 0.05

    def sanitized(self) -> "PoissonParameters":
        return PoissonParameters(
            max(self.lambda_home, 0.05),
            max(self.lambda_away, 0.05),
            max(self.covariance, 0.0),
        )


def factorial(n: int) -> int:
    return math.factorial(n)


def bivariate_poisson_matrix(params: PoissonParameters, max_goals: int = 8) -> List[List[float]]:
    params = params.sanitized()
    lam1, lam2, lam3 = params.lambda_home, params.lambda_away, params.covariance
    base = math.exp(-(lam1 + lam2 + lam3))
    matrix = [[0.0 for _ in range(max_goals + 1)] for _ in range(max_goals + 1)]
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            limit = min(i, j)
            prob = 0.0
            for k in range(limit + 1):
                term = (
                    (lam1 ** (i - k))
                    * (lam2 ** (j - k))
                    * (lam3 ** k)
                    / (factorial(i - k) * factorial(j - k) * factorial(k))
                )
                prob += term
            matrix[i][j] = base * prob
    normalize_matrix(matrix)
    return matrix


def normalize_matrix(matrix: List[List[float]]) -> None:
    total = sum(sum(row) for row in matrix)
    if total <= 0:
        raise ValueError("Total probability mass is non-positive")
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            matrix[i][j] = value / total


@dataclass
class MarketProbabilities:
    """Aggregated probabilities for markets derived from the scoreline distribution."""

    one_x_two: Dict[str, float]
    draw_no_bet: Dict[str, float]
    double_chance: Dict[str, float]
    over_under: Dict[str, Dict[str, float]]
    team_totals: Dict[str, Dict[str, float]]
    btts: Dict[str, float]
    asian_handicap: Dict[float, Dict[str, float]]
    correct_score: List[Tuple[str, float]]
    half_time: Dict[str, Dict[str, float]]
    specials: Dict[str, float]


def aggregate_markets(
    matrix: List[List[float]],
    calibrator: TemperatureCalibrator,
    max_goals: int = 8,
) -> MarketProbabilities:
    # Scoreline probabilities
    score_probs: Dict[str, float] = {}
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            prob = matrix[i][j]
            score_probs[f"{i}-{j}"] = calibrator.transform(prob)

    # Normalise after calibration to ensure sum to 1
    total = sum(score_probs.values())
    score_probs = {k: v / total for k, v in score_probs.items()}

    # 1X2
    home_win = sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) > int(score.split("-")[1]))
    draw = sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) == int(score.split("-")[1]))
    away_win = 1 - home_win - draw

    one_x_two = {"1": home_win, "X": draw, "2": away_win}

    draw_no_bet = {
        "home": home_win / (1 - draw) if draw < 0.999 else 0.0,
        "away": away_win / (1 - draw) if draw < 0.999 else 0.0,
    }

    double_chance = {
        "1X": home_win + draw,
        "12": home_win + away_win,
        "X2": draw + away_win,
    }

    over_under_lines = [1.5, 2.0, 2.5, 3.0, 3.5]
    over_under = {}
    for line in over_under_lines:
        over = sum(prob for score, prob in score_probs.items() if sum(map(int, score.split("-"))) > line)
        under = 1 - over
        over_under[str(line)] = {"over": over, "under": under}

    team_lines = [0.5, 1.5]
    team_totals = {
        "home": {},
        "away": {},
    }
    for line in team_lines:
        home_over = sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) > line)
        away_over = sum(prob for score, prob in score_probs.items() if int(score.split("-")[1]) > line)
        team_totals["home"][str(line)] = {"over": home_over, "under": 1 - home_over}
        team_totals["away"][str(line)] = {"over": away_over, "under": 1 - away_over}

    btts_yes = sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) > 0 and int(score.split("-")[1]) > 0)
    btts = {"yes": btts_yes, "no": 1 - btts_yes}

    asian_lines = [x / 4 for x in range(-8, 9)]  # -2.0 to +2.0
    asian_handicap: Dict[float, Dict[str, float]] = {}
    for line in asian_lines:
        asian_handicap[line] = {
            "home": asian_handicap_probability(score_probs, line, True),
            "away": asian_handicap_probability(score_probs, line, False),
        }

    # Correct score top 5
    top_scores = sorted(score_probs.items(), key=lambda kv: kv[1], reverse=True)[:5]

    # Half-time markets via approximation (half of goals expectation)
    half_matrix = [[0.0 for _ in range(6)] for _ in range(6)]
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            half_matrix[min(i, 5)][min(j, 5)] += score_probs[f"{i}-{j}"]
    ht_home_win = sum(half_matrix[i][j] for i in range(6) for j in range(6) if i > j)
    ht_draw = sum(half_matrix[i][j] for i in range(6) for j in range(6) if i == j)
    ht_away_win = 1 - ht_home_win - ht_draw
    half_time = {
        "1x2": {"1": ht_home_win, "X": ht_draw, "2": ht_away_win},
        "over_under_1.0": {
            "over": sum(half_matrix[i][j] for i in range(6) for j in range(6) if i + j > 1.0),
            "under": sum(half_matrix[i][j] for i in range(6) for j in range(6) if i + j <= 1.0),
        },
    }

    specials = {
        "win_to_nil_home": sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) > 0 and int(score.split("-")[1]) == 0),
        "win_to_nil_away": sum(prob for score, prob in score_probs.items() if int(score.split("-")[1]) > 0 and int(score.split("-")[0]) == 0),
        "clean_sheet_home": sum(prob for score, prob in score_probs.items() if int(score.split("-")[1]) == 0),
        "clean_sheet_away": sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) == 0),
        "first_goal_home": sum(prob for score, prob in score_probs.items() if int(score.split("-")[0]) > int(score.split("-")[1])),
        "first_goal_away": sum(prob for score, prob in score_probs.items() if int(score.split("-")[1]) > int(score.split("-")[0])),
    }

    return MarketProbabilities(
        one_x_two=one_x_two,
        draw_no_bet=draw_no_bet,
        double_chance=double_chance,
        over_under=over_under,
        team_totals=team_totals,
        btts=btts,
        asian_handicap=asian_handicap,
        correct_score=top_scores,
        half_time=half_time,
        specials=specials,
    )


def asian_handicap_probability(score_probs: Dict[str, float], line: float, is_home: bool) -> float:
    adjusted = 0.0
    for score, prob in score_probs.items():
        home, away = map(int, score.split("-"))
        margin = home - away if is_home else away - home
        adjusted += prob * handicap_outcome(margin, line)
    return adjusted


def handicap_outcome(margin: int, line: float) -> float:
    """Return probability weight for an Asian handicap line."""

    split = line * 2
    if split.is_integer():
        handicap = int(split) / 2
        outcome = margin + handicap
        if outcome > 0:
            return 1.0
        if outcome == 0:
            return 0.5
        return 0.0
    else:
        lower = math.floor(split) / 2
        upper = lower + 0.5
        return 0.5 * (handicap_outcome(margin, lower) + handicap_outcome(margin, upper))


__all__ = [
    "PoissonParameters",
    "bivariate_poisson_matrix",
    "aggregate_markets",
    "MarketProbabilities",
]
