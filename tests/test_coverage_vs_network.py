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

These pin the distinction without touching the network: the release manifest
not listing a nuclide is an answer, anything else is not, a 404 included.
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


def test_the_manifest_not_listing_it_is_the_library_answering_no(monkeypatch):
    # yani 0.21.0's wording, listing what the release does publish after it.
    _patch(monkeypatch, ValueError(
        "Nuclide 'Os190' is not available in 'fendl-3.2d' (release "
        "2026-10-12.1).\n\nAvailable under neutron/:\nAg107, Ag109, Al27"))

    assert fns_run._is_available("Os190", "fendl-3.2d") is False
    # Answered on the first ask; no point retrying a definite no.
    assert _Nuclide.calls == 1


def test_an_unpublished_library_is_not_a_gap(monkeypatch):
    """A 404 on the release pointer is the library missing, not the nuclide.

    Read as an answer, it refused the iron foil as "tendl-2017 publishes no
    evaluation for Fe" while the CDN still served a cached 404 for
    tendl-2017/latest.json.
    """
    _patch(monkeypatch, ValueError(
        "'tendl-2017' has not been published in the release layout yet: "
        "https://example.invalid/tendl-2017/latest.json answers 404."))

    with pytest.raises(fns_run.CoverageUnknown):
        fns_run._is_available("Fe56", "tendl-2017")
    assert _Nuclide.calls == fns_run._COVERAGE_ATTEMPTS


def test_a_file_the_manifest_lists_but_the_origin_lacks_is_not_a_gap(monkeypatch):
    _patch(monkeypatch, ValueError(
        "https://example.invalid/jeff-4.0/2026-10-10.1/neutron/Fe56.arrow/"
        "nuclide.arrow: 404, but the release manifest lists "
        "neutron/Fe56.arrow/nuclide.arrow (3082 bytes)"))

    with pytest.raises(fns_run.CoverageUnknown):
        fns_run._is_available("Fe56", "jeff-4.0")


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
    """A server error is the origin having a bad day."""
    _patch(monkeypatch, ValueError(
        "Failed to download https://example.invalid/a.arrow: 503 Service Unavailable"))

    with pytest.raises(fns_run.CoverageUnknown):
        fns_run._is_available("Nb93", "tendl-2017")
