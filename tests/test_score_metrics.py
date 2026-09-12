"""`|C/E - 1|` is asymmetric, so the score reports its symmetric counterpart too.

A calculation of zero scores 100% and cannot score worse. One that is a factor
of two high also scores 100%, and one a factor of ten high scores 900%. So the
metric is bounded below, unbounded above, and systematically kinder to whichever
code runs lower. `|ln C/E|` treats a factor either way alike.
"""

import pathlib
import sys
import types

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "fns_decay_heat"))

import case as fns_case  # noqa: E402


def _case(measured, uncertainty=None):
    measured = np.array(measured, dtype=float)
    if uncertainty is None:
        uncertainty = measured * 0.05
    return types.SimpleNamespace(measured=measured,
                                 uncertainty=np.array(uncertainty, dtype=float))


def test_the_old_metric_treats_a_factor_of_two_asymmetrically():
    case = _case([1.0, 1.0])
    high = fns_case.score(np.array([2.0, 2.0]), case)
    low = fns_case.score(np.array([0.5, 0.5]), case)
    assert high["mean_deviation_percent"] == 100.0
    assert low["mean_deviation_percent"] == 50.0


def test_the_log_metric_treats_it_symmetrically():
    case = _case([1.0, 1.0])
    high = fns_case.score(np.array([2.0, 2.0]), case)
    low = fns_case.score(np.array([0.5, 0.5]), case)
    assert np.isclose(high["mean_log_deviation_percent"],
                      low["mean_log_deviation_percent"])


def test_a_perfect_calculation_scores_zero_on_both():
    case = _case([3.0, 4.0])
    metrics = fns_case.score(np.array([3.0, 4.0]), case)
    assert metrics["mean_deviation_percent"] == 0.0
    assert np.isclose(metrics["mean_log_deviation_percent"], 0.0)


def test_points_the_measurement_does_not_constrain_are_counted_separately():
    """Two good points and two whose quoted sigma is most of their value."""
    case = _case([1.0, 1.0, 1.0, 1.0], uncertainty=[0.05, 0.05, 0.9, 0.9])
    metrics = fns_case.score(np.array([1.0, 1.0, 3.0, 3.0]), case)
    assert metrics["points"] == 4
    assert metrics["points_constrained"] == 2
    # The two noisy points carry all the deviation, so restricting removes it.
    assert metrics["mean_deviation_percent"] == 100.0
    assert metrics["mean_deviation_constrained_percent"] == 0.0


def test_a_zero_calculation_does_not_break_the_log_metric():
    case = _case([1.0, 1.0])
    metrics = fns_case.score(np.array([0.0, 1.0]), case)
    assert metrics["mean_deviation_percent"] == 50.0
    # The zero point is excluded from the log metric rather than becoming -inf.
    assert np.isfinite(metrics["mean_log_deviation_percent"])
    assert np.isclose(metrics["mean_log_deviation_percent"], 0.0)


def test_a_measured_zero_is_still_excluded_from_everything():
    case = _case([0.0, 2.0])
    metrics = fns_case.score(np.array([1.0, 2.0]), case)
    assert metrics["points"] == 1
    assert metrics["mean_deviation_percent"] == 0.0
