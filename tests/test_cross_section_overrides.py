"""Per-nuclide cross-section overrides must be applied and recorded.

A combination that silently used a different evaluation for one nuclide would
be worse than no override at all, so the two properties worth pinning are that
`apply` writes the entry and that `as_dict` reports it. Both run against a stub
yani, so no nuclear data is needed.
"""

import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from common import libraries  # noqa: E402


class _Yani:
    """Enough of the yani module surface for `libraries.apply` to run."""

    def __init__(self):
        self.entries = {}
        self.cross_section_data = None
        self.transmutation_reactions = None
        self.transmutation_branch_ratios = None
        self.transmutation_decay_data = None
        self.transmutation_fission_yields = None

    def set_cross_section_data_entry(self, nuclide, source):
        self.entries[nuclide] = source


def test_only_the_in115_combination_carries_an_override():
    carrying = [c.name for c in libraries.COMBINATIONS if c.cross_section_overrides]
    assert carrying == ["tendl-2017+in115-2025"]


def test_apply_writes_the_global_default_and_then_the_override():
    stub = _Yani()
    libraries.apply(libraries.BY_NAME["tendl-2017+in115-2025"], stub)
    assert stub.cross_section_data == "tendl-2017"
    assert stub.entries == {"In115": "tendl-2025"}


def test_a_combination_without_overrides_writes_none():
    stub = _Yani()
    libraries.apply(libraries.BY_NAME["tendl-2017"], stub)
    assert stub.entries == {}


def test_the_override_is_recorded_in_the_result_provenance():
    """A run has to be able to say which evaluation each nuclide came from."""
    recorded = libraries.as_dict(libraries.BY_NAME["tendl-2017+in115-2025"])
    assert recorded["cross_sections"] == "tendl-2017"
    assert recorded["cross_section_overrides"] == {"In115": "tendl-2025"}


def test_every_combination_reports_the_field_even_when_empty():
    for combination in libraries.COMBINATIONS:
        recorded = libraries.as_dict(combination)
        assert "cross_section_overrides" in recorded
        assert isinstance(recorded["cross_section_overrides"], dict)


def test_the_override_combination_is_marked_diagnostic():
    """It must not be able to win a headline it was built from."""
    assert libraries.BY_NAME["tendl-2017+in115-2025"].diagnostic is True
    assert libraries.as_dict(
        libraries.BY_NAME["tendl-2017+in115-2025"])["diagnostic"] is True


def test_scoreable_excludes_diagnostic_combinations():
    names = [c.name for c in libraries.scoreable()]
    assert "tendl-2017+in115-2025" not in names
    assert "tendl-2017+decay-2012" in names
    assert len(names) == len(libraries.COMBINATIONS) - 1


def test_no_ordinary_combination_is_diagnostic():
    ordinary = [c for c in libraries.COMBINATIONS
                if c.name != "tendl-2017+in115-2025"]
    assert not any(c.diagnostic for c in ordinary)
