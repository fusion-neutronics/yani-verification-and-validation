"""The group-structure study rebins a spectrum, so the rebin has to be exact.

Every row of that study is the same physical field on a different structure, so
any flux the rebin loses or invents shows up as a physics result that is not
one. These are the properties that make the rows comparable: flux is conserved,
rebinning onto the structure a spectrum already uses returns it unchanged, and
flux outside the destination's range is reported rather than folded into the
end groups.

That last one matters more than it looks. ECCO-1968 has more groups than
CCFE-709 but a *lower* top boundary, so "finer" does not imply "wider", and a
rebin that folded the overflow back in would put 14 MeV neutrons into a group
that does not reach them.
"""

import pathlib
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "fns_decay_heat"))

from group_structure import rebin  # noqa: E402


def _log_bounds(low, high, n):
    return np.geomspace(low, high, n + 1)


def test_flux_is_conserved_across_any_regrouping():
    source = _log_bounds(1.0e-5, 2.0e7, 400)
    dest = _log_bounds(1.0e-5, 2.0e7, 37)
    rng = np.random.default_rng(0)
    flux = rng.random(400) * 1.0e12

    out, under, over = rebin(source, flux, dest)

    assert under == 0.0 and over == 0.0
    assert out.sum() == pytest.approx(flux.sum(), rel=1e-12)


def test_rebinning_onto_its_own_structure_returns_the_input():
    bounds = _log_bounds(1.0e-3, 1.0e7, 120)
    rng = np.random.default_rng(1)
    flux = rng.random(120) * 3.0e11

    out, under, over = rebin(bounds, flux, bounds)

    assert under == 0.0 and over == 0.0
    np.testing.assert_allclose(out, flux, rtol=1e-12)


def test_one_group_spread_over_many_keeps_its_flux_and_its_place():
    """A single populated source group must land entirely inside its own span."""
    source = np.array([1.0, 10.0, 100.0])
    dest = _log_bounds(1.0, 100.0, 20)
    flux = np.array([0.0, 7.0])

    out, under, over = rebin(source, flux, dest)

    assert under == 0.0 and over == 0.0
    assert out.sum() == pytest.approx(7.0, rel=1e-12)
    # Nothing below 10 eV, since the populated group starts there.
    below = dest[1:] <= 10.0
    assert out[below].sum() == pytest.approx(0.0, abs=1e-12)


def test_flux_outside_the_destination_is_reported_not_folded_in():
    source = np.array([1.0, 10.0, 100.0, 1000.0])
    dest = np.array([10.0, 100.0])
    flux = np.array([5.0, 3.0, 11.0])

    out, under, over = rebin(source, flux, dest)

    assert out.sum() == pytest.approx(3.0, rel=1e-12)
    assert under == pytest.approx(5.0, rel=1e-12)
    assert over == pytest.approx(11.0, rel=1e-12)
    # The whole input is accounted for somewhere.
    assert out.sum() + under + over == pytest.approx(flux.sum(), rel=1e-12)


def test_a_group_straddling_the_edge_is_split_by_lethargy():
    """Half a decade in and half out splits the group's flux in the same ratio."""
    source = np.array([1.0, 100.0])
    dest = np.array([10.0, 1000.0])
    flux = np.array([8.0])

    out, under, over = rebin(source, flux, dest)

    # ln(10/1) of ln(100/1) is below the destination: exactly half.
    assert under == pytest.approx(4.0, rel=1e-12)
    assert out.sum() == pytest.approx(4.0, rel=1e-12)
    assert over == 0.0


def test_zero_groups_contribute_nothing_and_cost_nothing():
    source = _log_bounds(1.0e-5, 2.0e7, 50)
    dest = _log_bounds(1.0e-5, 2.0e7, 9)
    flux = np.zeros(50)

    out, under, over = rebin(source, flux, dest)

    assert out.sum() == 0.0 and under == 0.0 and over == 0.0
