#!/usr/bin/env python3
"""How much resonance self-shielding moves an FNS decay-heat foil.

    self_shielding.py                       # the default foil set
    self_shielding.py --case Au --case Ta
    self_shielding.py --thickness 50 200    # micrometres
    self_shielding.py --list                # what the default set is, and why

The rest of this benchmark runs every foil dilute, which is what `transmute()`
does when a material carries no geometry. Inside a real foil the flux is
depressed wherever the total cross section is large, so a dilute run reads high
on anything with strong resonances, and the archive's own C/E is carrying that
error along with everything else.

**This does not validate self-shielding against the FNS measurement, and cannot.**
The archive publishes each foil's mass and density but not its dimensions, so
the chord length the correction needs is not in the data. What this does
instead is sweep the thickness and report how far the answer moves, which
separates two things the dilute run cannot:

* which foils are sensitive at all, and
* at what thickness the sensitivity starts to matter.

A foil whose heat curve does not move across the whole sweep is one whose
dilute C/E can be read as-is. A foil that moves by more than its measurement
uncertainty is one whose dilute C/E is partly a geometry error, and no amount
of work on the cross sections will fix it.

The dilute run's own screen is reported beside the sweep.
`get_self_shielding_info(id)["would_shield"]` is what yani says about a run that
skipped the correction: which resonance absorbers it left uncorrected and how
strongly their own resonances could bite. It carries no geometry, so it is an
indicator rather than a bound, and this sweep is the check on whether it points
at the right foils.
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

# Foils chosen to span the effect rather than to flatter it: strong resonance
# absorbers first, then four that should barely move. If a control moves, the
# correction is reaching further than it should and that is worth knowing.
ABSORBERS = ["Au", "Ta", "W", "In", "Co", "Nb"]
CONTROLS = ["Al", "Ti"]
DEFAULT_CASES = ABSORBERS + CONTROLS

# Micrometres. A 1 g activation foil spans roughly this range depending on its
# density and diameter. Two points rather than a fine sweep, because a shielded
# solve is expensive: the slowing-down solve runs per nuclide per group over
# the whole reachable network, which on a 14 MeV foil is a few thousand
# nuclides, and one measured at 807 s against 15 s for the same foil dilute.
# The pair brackets the range instead of resolving it, and --thickness takes
# whatever else is wanted.
DEFAULT_THICKNESS_UM = [100.0, 1000.0]


def solve(case, thickness_um, combination):
    """One FNS case, either dilute (`thickness_um is None`) or shielded."""
    spectrum = yani.NeutronSource(
        energy=yani.sources.Histogram(fns_case.GROUP_STRUCTURE, case.spectrum.tolist())
    )
    schedule = yani.PulseSchedule(
        [yani.Pulse(duration=(seconds, "s"), rate=flux, source=spectrum)
         for seconds, flux in case.irradiation]
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

    shape = None
    if thickness_um is not None:
        shape = yani.shapes.FoilLump(thickness=thickness_um * 1.0e-4)  # um -> cm

    started = time.time()
    results = material.transmute(schedule, self_shielding_shape=shape)
    elapsed = time.time() - started

    material_id = material.id or 0
    states = results.step_materials(material_id)
    heat = np.array([
        sum(state.decay_heat(by_nuclide=True).values()) / case.mass_g * 1e6
        for state in states[len(case.irradiation):]
    ])
    return heat, results.get_self_shielding_info(material_id), elapsed


def mean_deviation_percent(calculated, case):
    """The same headline this benchmark uses elsewhere: mean |C/E - 1|."""
    usable = case.measured > 0
    if not usable.any():
        return None
    ratio = calculated[usable] / case.measured[usable]
    return float(np.abs(ratio - 1.0).mean() * 100.0)


def study(name, experiment, thicknesses, combination):
    case = fns_case.load(name, experiment)
    dilute, dilute_info, elapsed = solve(case, None, combination)

    # `would_shield` is only filled on a dilute run: it is the screen, and a
    # shielded run reports what it actually did instead.
    would = (dilute_info or {}).get("would_shield") or {}
    record = {
        "case": case.name,
        "experiment": case.experiment,
        "mass_g": case.mass_g,
        "density_g_per_cm3": case.density,
        "dilute": {
            "heat_uW_per_g": dilute.tolist(),
            "mean_deviation_percent": mean_deviation_percent(dilute, case),
            "would_shield": {k: float(v) for k, v in would.items()},
            "solve_seconds": elapsed,
        },
        "measured_uW_per_g": case.measured.tolist(),
        "uncertainty_uW_per_g": case.uncertainty.tolist(),
        "shielded": {},
    }

    for thickness in thicknesses:
        heat, info, elapsed = solve(case, thickness, combination)
        # Relative move in the heat curve, over the points the measurement
        # constrains. A foil that does not move here needs no geometry.
        both = (dilute > 0) & (heat > 0)
        moved = float(np.abs(heat[both] / dilute[both] - 1.0).max() * 100.0) if both.any() else 0.0
        info = info or {}
        record["shielded"][f"{thickness:g}um"] = {
            "heat_uW_per_g": heat.tolist(),
            "mean_deviation_percent": mean_deviation_percent(heat, case),
            "max_move_vs_dilute_percent": moved,
            "method": info.get("method"),
            "chord_cm": info.get("chord_cm"),
            "strongest_factor": info.get("strongest_factor"),
            "shielded_nuclides": len(info.get("shielded") or {}),
            "solve_seconds": elapsed,
        }
    return record


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", dest="cases",
                    help="foil to study; repeatable. Defaults to the set in --list.")
    ap.add_argument("--experiment", default=None)
    ap.add_argument("--thickness", type=float, nargs="+", default=DEFAULT_THICKNESS_UM,
                    metavar="UM", help="foil thicknesses in micrometres")
    ap.add_argument("--combination", default=libraries.APPLES_TO_APPLES,
                    help="a name from benchmarks/common/libraries.py")
    ap.add_argument("--output", type=pathlib.Path,
                    default=HERE / "results" / "self_shielding.json")
    ap.add_argument("--list", action="store_true",
                    help="print the default foil set and stop")
    args = ap.parse_args()

    if args.list:
        print("resonance absorbers, expected to move:")
        print("  " + " ".join(ABSORBERS))
        print("controls, expected not to:")
        print("  " + " ".join(CONTROLS))
        print(f"thicknesses [um]: {' '.join(f'{t:g}' for t in DEFAULT_THICKNESS_UM)}")
        return 0

    combination = libraries.resolve([args.combination])[0]
    libraries.apply(combination, yani)

    cases = args.cases or DEFAULT_CASES
    records, failures = [], {}
    for name in cases:
        try:
            record = study(name, args.experiment, args.thickness, combination)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            failures[name] = f"{type(exc).__name__}: {exc}"
            print(f"  {name}: FAILED {type(exc).__name__}: {exc}", flush=True)
            continue
        records.append(record)
        worst = max((v["max_move_vs_dilute_percent"] for v in record["shielded"].values()),
                    default=0.0)
        print(f"  {name}: dilute {record['dilute']['mean_deviation_percent']:.1f}% deviation, "
              f"moves up to {worst:.1f}% across the sweep", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "yani_version": yani.__version__,
        "combination": libraries.as_dict(combination),
        "thicknesses_um": args.thickness,
        "absorbers": ABSORBERS,
        "controls": CONTROLS,
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
