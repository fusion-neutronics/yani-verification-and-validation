#!/usr/bin/env python3
"""What the spectrum's group structure costs an FNS decay-heat foil.

    group_structure.py                     # the default foils, every structure
    group_structure.py --case W --case Au
    group_structure.py --structure UKAEA-1102 XMAS-172
    group_structure.py --list              # the structures and their group counts

yani takes whatever ascending list of energy boundaries a spectrum happens to
use, of whatever length. Named structures are a convenience, never a
requirement, and nothing in the solver prefers one. This measures what that
freedom is worth: the same physical field, expressed on ten different
structures, run through the same foil.

The FNS archive publishes its spectra on CCFE-709, so that row is the input as
given and every other row is a rebin of it. That sets the direction of the
result. Rebinning onto a **finer** structure, UKAEA-1102 or ECCO-1968, cannot
recover detail the 709-group file never carried, so those rows should agree
with the native one to rebinning round-off, and a disagreement would mean the
rebin is lossy where it should not be. Rebinning onto a **coarser** one throws
resolution away, and the size of that loss is the number this is for.

The rebin conserves flux per unit lethargy within each source group, which is
the convention inventory codes use for exactly this. Total flux is conserved
exactly and asserted, so a row that drifts is a physics result rather than a
bookkeeping one. Energy outside the destination's range is reported rather than
folded back in.
"""

import argparse
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import yani  # noqa: E402
from common import libraries  # noqa: E402

import case as fns_case  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

DEFAULT_CASES = ["W", "Au", "Ta", "Fe", "Nb"]

# Every neutron structure the wheel ships, coarsest first. The native one is in
# here too and is the row everything else is measured against.
DEFAULT_STRUCTURES = [
    "XMAS-172", "VITAMIN-J-175", "SCALE-252", "TRIPOLI-315", "SHEM-361",
    "LLNL-616", "CCFE-709", "SCALE-999", "UKAEA-1102", "ECCO-1968",
]

NATIVE = fns_case.GROUP_STRUCTURE  # "CCFE-709"


def rebin(source_bounds, flux, dest_bounds):
    """Move group fluxes onto another structure, flat in lethargy per source group.

    Returns `(rebinned, underflow, overflow)`. A source group is spread across
    the destination groups it overlaps in proportion to the lethargy they share,
    which is the same convention the mesh paths of inventory codes use. Flux
    below the destination's first boundary or above its last is returned
    separately rather than folded into the end groups, because folding it in
    would put fast neutrons where there are none.
    """
    source_bounds = np.asarray(source_bounds, dtype=float)
    dest_bounds = np.asarray(dest_bounds, dtype=float)
    flux = np.asarray(flux, dtype=float)

    out = np.zeros(len(dest_bounds) - 1)
    under = over = 0.0

    for i, phi in enumerate(flux):
        if phi == 0.0:
            continue
        lo, hi = source_bounds[i], source_bounds[i + 1]
        width = np.log(hi / lo)
        if width <= 0:
            continue
        # The part of this source group below / above the destination range.
        if hi <= dest_bounds[0]:
            under += phi
            continue
        if lo >= dest_bounds[-1]:
            over += phi
            continue
        if lo < dest_bounds[0]:
            under += phi * np.log(dest_bounds[0] / lo) / width
            lo = dest_bounds[0]
        if hi > dest_bounds[-1]:
            over += phi * np.log(hi / dest_bounds[-1]) / width
            hi = dest_bounds[-1]

        first = max(np.searchsorted(dest_bounds, lo, side="right") - 1, 0)
        last = min(np.searchsorted(dest_bounds, hi, side="left"), len(dest_bounds) - 1)
        for j in range(first, last):
            a = max(lo, dest_bounds[j])
            b = min(hi, dest_bounds[j + 1])
            if b > a:
                out[j] += phi * np.log(b / a) / width
    return out, under, over


def solve(case, bounds, flux):
    """Specific decay heat [uW/g] at each measured time, from one spectrum.

    Returns `(heat, elapsed, data_releases)`, the last being which
    nuclear-data release each library came from.
    """
    spectrum = yani.NeutronSource(
        energy=yani.sources.Histogram(list(bounds), list(flux))
    )
    schedule = yani.PulseSchedule(
        [yani.Pulse(duration=(seconds, "s"), rate=rate, source=spectrum)
         for seconds, rate in case.irradiation]
        + [yani.Cooldown(duration=(seconds, "s")) for seconds in case.cooling_steps]
    )
    material = yani.Material(
        composition=case.composition,
        fraction_type="mass",
        density=case.density,
        volume=case.mass_g / case.density,
        temperature=fns_case.TEMPERATURE,
        name=f"{case.name} foil",
    )
    started = time.time()
    results = material.transmute(schedule)
    elapsed = time.time() - started
    states = results.step_materials(material.id or 0)
    heat = np.array([
        sum(state.decay_heat(by_nuclide=True).values()) / case.mass_g * 1e6
        for state in states[len(case.irradiation):]
    ])
    return heat, elapsed, results.data_releases


def mean_deviation_percent(calculated, case):
    usable = case.measured > 0
    if not usable.any():
        return None
    return float(np.abs(calculated[usable] / case.measured[usable] - 1.0).mean() * 100.0)


def study(name, experiment, structures, releases):
    case = fns_case.load(name, experiment)
    native_bounds = yani.group_structure(NATIVE)
    total = float(case.spectrum.sum())

    record = {
        "case": case.name,
        "experiment": case.experiment,
        "native_structure": NATIVE,
        "measured_uW_per_g": case.measured.tolist(),
        "uncertainty_uW_per_g": case.uncertainty.tolist(),
        "rows": {},
    }

    native_heat = None
    for structure in structures:
        bounds = yani.group_structure(structure)
        if structure == NATIVE:
            flux, under, over = case.spectrum.copy(), 0.0, 0.0
        else:
            flux, under, over = rebin(native_bounds, case.spectrum, bounds)

        kept = float(flux.sum())
        closure = abs(kept + under + over - total) / total if total else 0.0
        if closure > 1e-10:
            raise SystemExit(
                f"{name}/{structure}: rebin lost flux, closure {closure:.3e}. "
                f"That is a bug in this script, not a result.")

        heat, elapsed, read = solve(case, bounds, flux)
        releases.read(read)
        if structure == NATIVE:
            native_heat = heat
        record["rows"][structure] = {
            "groups": len(bounds) - 1,
            "heat_uW_per_g": heat.tolist(),
            "mean_deviation_percent": mean_deviation_percent(heat, case),
            "flux_below_range_fraction": (under / total) if total else 0.0,
            "flux_above_range_fraction": (over / total) if total else 0.0,
            "rebin_closure": closure,
            "solve_seconds": elapsed,
        }

    for row in record["rows"].values():
        heat = np.array(row["heat_uW_per_g"])
        both = (native_heat > 0) & (heat > 0)
        row["max_move_vs_native_percent"] = (
            float(np.abs(heat[both] / native_heat[both] - 1.0).max() * 100.0)
            if both.any() else 0.0)
    return record


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", dest="cases", help="foil; repeatable")
    ap.add_argument("--experiment", default=None)
    ap.add_argument("--structure", nargs="+", default=DEFAULT_STRUCTURES)
    ap.add_argument("--combination", default=libraries.APPLES_TO_APPLES)
    ap.add_argument("--output", type=pathlib.Path,
                    default=HERE / "results" / "group_structure.json")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for structure in yani.group_structure_names():
            print(f"{structure}: {len(yani.group_structure(structure)) - 1} groups")
        return 0

    combination = libraries.resolve([args.combination])[0]
    libraries.apply(combination, yani)

    records, failures = [], {}
    releases = libraries.DataReleases(combination, args.output)
    for name in args.cases or DEFAULT_CASES:
        try:
            record = study(name, args.experiment, args.structure, releases)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            failures[name] = f"{type(exc).__name__}: {exc}"
            print(f"  {name}: FAILED {type(exc).__name__}: {exc}", flush=True)
            continue
        records.append(record)
        finer = [r["max_move_vs_native_percent"] for s, r in record["rows"].items()
                 if r["groups"] > record["rows"][NATIVE]["groups"]]
        coarser = [r["max_move_vs_native_percent"] for s, r in record["rows"].items()
                   if r["groups"] < record["rows"][NATIVE]["groups"]]
        print(f"  {name}: finer structures move up to {max(finer or [0]):.2f}%, "
              f"coarser up to {max(coarser or [0]):.2f}%", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "yani_version": yani.__version__,
        "combination": libraries.as_dict(combination, releases),
        "native_structure": NATIVE,
        "structures": args.structure,
        "cases": records,
        "failures": failures,
    }
    tmp = args.output.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n")
    tmp.replace(args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
