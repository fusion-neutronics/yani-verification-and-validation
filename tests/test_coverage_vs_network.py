"""A library saying "no" and the network failing to ask are different answers.

`uncovered()` decides whether a foil is skipped because its library does not
publish the element. That is a statement about the library, and it reaches the
results file as one: "tendl-2017 publishes no evaluation for Au (Au197)".

The check used to be `except Exception: return False`, so any way of failing to
reach the data produced that same statement. A sweep with sixteen workers
against one origin drops connections, and in one run twenty of 132 experiments
were recorded as library gaps for evaluations that are published and that the
same process read without complaint a minute later. Nothing in the output said
so, which is the part that makes it worth a test.

These pin the distinction without touching the network: a 404 is an answer,
anything else is not.
"""

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "fns_decay_heat"))

import run as fns_run  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_memo():
    """The answer is memoised, so each test needs a clean table."""
    fns_run._is_available.cache_clear()
    yield
    fns_run._is_available.cache_clear()


class _Nuclide:
    """Stands in for yani.Nuclide, raising whatever the test asks for."""

    raises = None
    calls = 0

    def __init__(self, name):
        self.name = name

    def read_nuclear_data(self, library):
        type(self).calls += 1
        if self.raises is not None:
            raise self.raises


def _patch(monkeypatch, exc, attempts_sleep=True):
    _Nuclide.raises = exc
    _Nuclide.calls = 0
    monkeypatch.setattr(fns_run.yani, "Nuclide", _Nuclide)
    if attempts_sleep:
        monkeypatch.setattr(fns_run.time, "sleep", lambda _s: None)


def test_a_404_is_the_library_answering_no(monkeypatch):
    _patch(monkeypatch, ValueError(
        "Failed to download https://example.invalid/lib/neutron/Xx999.arrow/"
        "version.json: 404 Not Found"))

    assert fns_run._is_available("Xx999", "lib") is False
    # Answered on the first ask; no point retrying a definite no.
    assert _Nuclide.calls == 1


def test_a_present_nuclide_is_available(monkeypatch):
    _patch(monkeypatch, None)

    assert fns_run._is_available("Fe56", "lib") is True
    assert _Nuclide.calls == 1


def test_a_transport_error_raises_rather_than_reporting_a_gap(monkeypatch):
    _patch(monkeypatch, ValueError("error decoding response body"))

    with pytest.raises(fns_run.CoverageUnknown) as caught:
        fns_run._is_available("Au197", "tendl-2017")

    # The message has to say which way round it failed, because the whole
    # point is that this is not a statement about tendl-2017.
    assert "not a gap in the library" in str(caught.value)
    assert _Nuclide.calls == fns_run._COVERAGE_ATTEMPTS


def test_a_transient_error_that_clears_is_not_a_gap(monkeypatch):
    """The retry exists so a single dropped connection costs a pause, not a case."""
    state = {"left": 2}

    class _Flaky(_Nuclide):
        def read_nuclear_data(self, library):
            type(self).calls += 1
            if state["left"]:
                state["left"] -= 1
                raise ValueError("connection reset by peer")

    _Flaky.calls = 0
    monkeypatch.setattr(fns_run.yani, "Nuclide", _Flaky)
    monkeypatch.setattr(fns_run.time, "sleep", lambda _s: None)

    assert fns_run._is_available("Au197", "tendl-2017") is True
    assert _Flaky.calls == 3


def test_a_five_hundred_is_not_an_answer_either(monkeypatch):
    """Only 404 means absent. A server error is the origin having a bad day."""
    _patch(monkeypatch, ValueError(
        "Failed to download https://example.invalid/a.arrow: 503 Service Unavailable"))

    with pytest.raises(fns_run.CoverageUnknown):
        fns_run._is_available("Nb93", "tendl-2017")
