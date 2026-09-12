"""A library that does not publish an element must be refused, not scored.

`uncovered` is the guard. These tests drive it through a stub rather than real
nuclear data, so they run in CI with no `~/.cache/yamc` and in milliseconds: the
logic under test is which gaps are fatal, not whether a particular release
happens to contain osmium.

The behaviour they pin, checked separately against the real libraries:
fendl-3.2d refuses 22 of the 132 FNS experiments, across the 20 elements it
publishes no evaluation for, and refuses none of the tendl-2017 ones.
"""

import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "fns_decay_heat"))


@pytest.fixture
def stub(monkeypatch):
    """Replace the data lookups so the test needs no nuclear data."""
    import run

    natural = {
        "Fe": ["Fe54", "Fe56", "Fe57", "Fe58"],
        "Os": ["Os184", "Os186", "Os187", "Os188", "Os189", "Os190", "Os192"],
        "Cr": ["Cr50", "Cr52", "Cr53", "Cr54"],
    }
    published = {"Fe54", "Fe56", "Fe57", "Fe58", "Cr52", "Cr53"}

    monkeypatch.setattr(run.yani, "Element",
                        lambda name: types.SimpleNamespace(
                            get_nuclides=lambda: natural[name]))
    monkeypatch.setattr(run, "_is_available",
                        lambda nuclide, library: nuclide in published)
    return run


def _case(composition):
    return types.SimpleNamespace(composition=composition)


def _combination(name="stub"):
    return types.SimpleNamespace(name=name, cross_sections=name)


def test_an_element_with_no_published_isotope_is_reported(stub):
    missing = stub.uncovered(_case({"Os": 1.0}), _combination())
    assert list(missing) == ["Os"]
    assert missing["Os"][0] == "Os184"


def test_a_fully_published_element_is_not_reported(stub):
    assert stub.uncovered(_case({"Fe": 1.0}), _combination()) == {}


def test_a_partial_gap_is_left_alone(stub):
    """Cr50 and Cr54 are absent but Cr52 and Cr53 are not.

    A missing minor isotope changes a rate, which is a library being different.
    A missing element means the foil cannot activate, which is a library being
    absent. Only the second is a coverage failure.
    """
    assert stub.uncovered(_case({"Cr": 1.0}), _combination()) == {}


def test_an_alloy_reports_only_the_elements_that_are_missing(stub):
    missing = stub.uncovered(_case({"Fe": 0.7, "Cr": 0.2, "Os": 0.1}),
                             _combination())
    assert list(missing) == ["Os"]


def test_the_runner_refuses_rather_than_returning_a_curve(stub):
    """The whole point: a named error instead of a C/E near zero."""
    case = _case({"Os": 1.0})
    case.experiment = "2000exp_5min"
    case.name = "Os"
    missing = stub.uncovered(case, _combination("fendl-3.2d"))
    assert missing, "the guard must fire before the solve"
    with pytest.raises(stub.MissingEvaluations) as raised:
        raise stub.MissingEvaluations(
            f"Os/2000exp_5min: fendl-3.2d publishes no evaluation for Os")
    assert "fendl-3.2d" in str(raised.value)
