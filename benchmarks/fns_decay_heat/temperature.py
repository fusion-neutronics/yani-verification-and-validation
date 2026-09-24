#!/usr/bin/env python3
"""How much the evaluated temperature moves an FNS decay-heat foil.

    temperature.py                    # tungsten, every temperature the library has
    temperature.py --case Ta --case W
    temperature.py --list             # what temperatures are available

Doppler broadening widens and flattens a resonance without changing the area
under it, so a spectrum-averaged reaction rate moves with temperature wherever
resonance structure sits under flux. How far it moves is a property of the
evaluation and of the spectrum, not something that can be read off the
material.

The FNS foils were irradiated at room temperature, so **this is a sensitivity
study and not a validation**: the 294 K row is the one with a measurement
behind it, and the rest say what the same foil would have done hotter. That is
the question a fusion component asks, where tungsten sits at several hundred
degrees rather than at 294 K, and where the activation library is usually still
read at room temperature because that is the only temperature a multigroup
activation library ships.

Tungsten is the default because it is the plasma-facing material the question
is usually asked about, and because W186 carries the resonance structure to
show an effect. 600 C, the temperature a first wall runs near, is 873 K, which
sits between the 600 K and 900 K the evaluations carry; both are reported
rather than interpolated, since the library is what it is.
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

DEFAULT_CASES = ["W", "Ta"]

# The room-temperature row, and the one every other row is compared against.
# It is also what the rest of this benchmark runs at.
REFERENCE_K = "294"


def available_temperatures(case):
    """The temperature labels every nuclide in the foil actually carries.

    The intersection, not the union: a foil is solved at one temperature, so a
    label one of its nuclides lacks is a label the foil cannot be run at.
    """
    common = None
    for element in case.composition:
        for nuclide_name in yani.Element(element).get_nuclides():
            nuclide = yani.Nuclide(nuclide_name)
            try:
                nuclide.read_nuclear_data()
            except Exception:  # noqa: BLE001 - absent evaluations are not this script's business
                continue
            labels = set(nuclide.available_temperatures or [])
            common = labels if common is None else (common & labels)
    return sorted(common or [], key=float)


def solve(case, temperature):
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
        temperature=float(temperature),
        name=f"{case.name} foil at {temperature} K",
    )
    started = time.time()
    results = material.transmute(schedule)
    elapsed = time.time() - started

    states = results.step_materials(material.id or 0)
    heat = np.array([
        sum(state.decay_heat(by_nuclide=True).values()) / case.mass_g * 1e6
        for state in states[len(case.irradiation):]
    ])
    return heat, elapsed


def mean_deviation_percent(calculated, case):
    usable = case.measured > 0
    if not usable.any():
        return None
    return float(np.abs(calculated[usable] / case.measured[usable] - 1.0).mean() * 100.0)


def study(name, experiment, temperatures=None):
    case = fns_case.load(name, experiment)
    labels = temperatures or available_temperatures(case)
    if REFERENCE_K not in labels:
        raise SystemExit(
            f"{name}: no {REFERENCE_K} K evaluation, so there is nothing to "
            f"compare the hot rows against. Available: {' '.join(labels)}")

    record = {
        "case": case.name,
        "experiment": case.experiment,
        "temperatures_K": labels,
        "reference_K": REFERENCE_K,
        "measured_uW_per_g": case.measured.tolist(),
        "uncertainty_uW_per_g": case.uncertainty.tolist(),
        "rows": {},
    }

    reference = None
    for label in labels:
        heat, elapsed = solve(case, label)
        if label == REFERENCE_K:
            reference = heat
        record["rows"][label] = {
            "heat_uW_per_g": heat.tolist(),
            "mean_deviation_percent": mean_deviation_percent(heat, case),
            "solve_seconds": elapsed,
        }

    for label, row in record["rows"].items():
        heat = np.array(row["heat_uW_per_g"])
        both = (reference > 0) & (heat > 0)
        row["max_move_vs_294K_percent"] = (
            float(np.abs(heat[both] / reference[both] - 1.0).max() * 100.0)
            if both.any() else 0.0)
    return record


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", dest="cases", help="foil; repeatable")
    ap.add_argument("--experiment", default=None)
    ap.add_argument("--temperature", nargs="+", default=None, metavar="K",
                    help="temperature labels; default is every one the foil carries")
    ap.add_argument("--combination", default=libraries.APPLES_TO_APPLES)
    ap.add_argument("--output", type=pathlib.Path,
                    default=HERE / "results" / "temperature.json")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    combination = libraries.resolve([args.combination])[0]
    libraries.apply(combination, yani)

    if args.list:
        for name in args.cases or DEFAULT_CASES:
            case = fns_case.load(name, args.experiment)
            print(f"{name}: {' '.join(available_temperatures(case))} K")
        return 0

    records, failures = [], {}
    for name in args.cases or DEFAULT_CASES:
        try:
            record = study(name, args.experiment, args.temperature)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            failures[name] = f"{type(exc).__name__}: {exc}"
            print(f"  {name}: FAILED {type(exc).__name__}: {exc}", flush=True)
            continue
        records.append(record)
        worst = max(r["max_move_vs_294K_percent"] for r in record["rows"].values())
        print(f"  {name}: {len(record['rows'])} temperatures, "
              f"heat moves up to {worst:.2f}% against 294 K", flush=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "yani_version": yani.__version__,
        "combination": libraries.as_dict(combination),
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
