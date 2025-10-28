from autobet_bl.modeling.calibrator import TemperatureCalibrator
from autobet_bl.modeling.poisson import (
    PoissonParameters,
    aggregate_markets,
    bivariate_poisson_matrix,
)


def test_bivariate_poisson_matrix_sums_to_one():
    params = PoissonParameters(1.5, 1.2, 0.05)
    matrix = bivariate_poisson_matrix(params, max_goals=6)
    total = sum(sum(row) for row in matrix)
    assert abs(total - 1.0) < 1e-6


def test_aggregate_markets_probabilities_within_bounds():
    params = PoissonParameters(1.5, 1.0, 0.03)
    matrix = bivariate_poisson_matrix(params, max_goals=6)
    probs = aggregate_markets(matrix, TemperatureCalibrator(1.0), max_goals=6)

    for value in probs.one_x_two.values():
        assert 0 <= value <= 1

    for line in probs.over_under.values():
        assert 0 <= line["over"] <= 1
        assert 0 <= line["under"] <= 1

    assert len(probs.correct_score) == 5
