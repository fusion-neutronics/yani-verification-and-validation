#!/usr/bin/env python3
"""Fission decay heat: irradiate a fissioning system, then follow its heat down.

    run.py                                  # U235 thermal, Dickens pulse
    run.py --system U235_thermal --dataset Yarnell_20000
    run.py --list                           # every system and dataset
    run.py --all                            # every curve, one JSON out

A fissile sample is irradiated, the irradiation stops, and the decay power of
the fission products is measured as it falls. The benchmark reports that power
in **MeV per fission per second**: the decay power divided by the total number
of fissions the irradiation caused, which makes the answer independent of how
big the sample was and how hard it was driven.

This is the only benchmark here that exercises the fission-yield path. The
foils in the others carry no fissile material at all, so their yield settings
are configured and read by nothing.

## The archive tabulates t*f(t), not f(t)

The column header says `MeV/f/s`, which is the unit of the decay power per
fission f(t). The values are not f(t). They are **t*f(t)**, in MeV per
fission, which is the standard compressed presentation for fission decay heat:
f(t) falls roughly as t^-1.2 over many decades and multiplying by t turns that
into a nearly flat curve a reader can see structure in.

Measured rather than assumed. Against a yani pulse solve on U235 thermal,
32 points from 2.7 s to 12000 s:

    measured / calculated        median 102      spread 4393x
    measured / (calculated * t)  median 0.9944   spread 1.13x

A wrong constant would show as a flat offset. A spread of 4393x collapsing to
1.13x when divided by t is the t in the published quantity, not a coincidence,
and it holds across every thermal pulse dataset in the archive.

So the comparison is done in the archive's own space: the calculated f(t) is
multiplied by t and compared with the published number as it stands. Dividing
the measurement instead would leave a page whose numbers no longer match the
tables it came from.

## How the normalisation is done

yani returns decay heat in watts. The conversion is

    f(t) [MeV/fission/s]  =  heat [W] * 6.241509074e12 [MeV/J]  /  fissions

and `fissions` is taken from the run rather than assumed:
`get_reaction_rates()` reports a fission channel as an edge whose target is
`None`, because fission names no single product and its products come from the
yields. That rate is per parent atom per second, so

    fissions = fission_rate [1/s] * parent_atoms * irradiation_seconds

Taking it from the run is the point. Computing it from a cross section and a
flux outside the solve would be a second, independent calculation of the same
quantity, and a disagreement between the two would show up as a wrong answer
rather than as a failure.

## Why the flux is set from a fluence

The per-fission normalisation assumes the sample is a trace consumer of its own
inventory. A fixed flux does not hold that across the range of irradiations in
the archive: at the 1e22 the decks use for a microsecond burst, a 20000 s
irradiation reaches 1.2e5 fissions per atom and the sample is gone. So the
flux is set as a fluence divided by the irradiation, which holds the burnup at
5.9e-6 fissions per atom whatever the duration, and leaves a burst running at
exactly the 1e22 it would otherwise have used.

`burnup_fissions_per_atom` is recorded per curve so this is checkable rather
than asserted.

## What a pulse is

A "pulse" experiment is an instantaneous burst. It is run here as a short
irradiation rather than a true delta, short enough that nothing produced
decays appreciably within it. The archive's own FISPACT decks do the same,
with `TIME 1.0E-06`.

## What this does not have

The archive carries FISPACT-II and ORIGEN *inputs* but no calculated results,
so there is no second code's curve here. Every other benchmark on this site
compares two codes; this one compares yani with a measurement.
"""

import argparse
import json
import re
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import yani  # noqa: E402
from common import libraries  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data" / "fission_data.json"

MEV_PER_JOULE = 6.241509074e12

# Fission products span A of roughly 70 to 160; the actinide chain the parent
# captures its way up starts above 220. This separates them with a wide margin.
FISSION_PRODUCT_MAX_A = 200
_MASS_NUMBER = re.compile(r"^[A-Za-z]+(\d+)")

# Short enough that the shortest-lived products the measurement resolves do not
# decay appreciably within it, and the same order the archive's own FISPACT
# decks use for a burst.
PULSE_SECONDS = 1.0e-6

# One gram-ish of the fissile nuclide. The answer is per fission so the amount
# cancels, and this only has to be large enough that the inventory is not
# round-off and small enough that the sample does not burn appreciably.
SAMPLE_VOLUME_CM3 = 1.0
SAMPLE_DENSITY = 19.0

# Total fluence over the irradiation, rather than a flux, so that every
# irradiation length burns the sample by the same negligible amount.
#
# A fixed flux does not survive the range of irradiations here. At 1e22, which
# is what the archive's FISPACT decks use for a microsecond burst, a 20000 s
# irradiation reaches a burnup of 1.2e5 fissions per atom: the sample is gone
# many times over, the trace assumption the per-fission normalisation rests on
# is false, and the answer is meaningless. Holding fluence constant instead
# gives 5.9e-6 fissions per atom at every duration.
#
# 1e16 n/cm2 is chosen so that a burst, at 1e-6 s, still runs at the 1e22 the
# decks use, which leaves the pulse results bit-identical to a fixed-flux run.
IRRADIATION_FLUENCE = 1.0e16

# The curves this benchmark currently stands behind: burst irradiations whose
# published t*f(t) is reproduced across the whole measured range, so the
# comparison is a result rather than a convention question.
#
# Everything else in the archive is excluded for a stated reason, not quietly
# dropped. See `EXCLUDED` and the page.
VALIDATED = [
    ("U235_thermal", "Dickens_pulse"),
    ("U235_thermal", "Tobias_pulse"),
    ("U235_fast", "Akiyama_pulse"),
    ("U233_fast", "Akiyama_pulse"),
    ("U238_fast", "Akiyama_pulse"),
    ("Pu239_thermal", "Tobias_pulse"),
    ("Pu239_fast", "Akiyama_pulse"),
    ("Pu241_thermal", "Dickens_pulse"),
]

# Why each of the rest is out. Running them is a flag away; believing them is
# not, and the distinction is the point of keeping this list in the code.
EXCLUDED = {
    "finite": (
        "Finite-irradiation curves (Yarnell, Jurney, Lott, Baumung, McNair, "
        "MacMahon, Scobie, Murphy, Fisher, Lowell) do not follow the pulse "
        "t*f(t) convention: the ratio to a yani solve runs from 1e2 to 1e7 "
        "and is not flat in time, so their normalisation is a different one "
        "and has not been established."),
    "no_total": (
        "Th232_fast and several others publish beta or gamma but no total "
        "column, so there is nothing for the current scoring to compare "
        "against. Scoring the components separately would bring them in."),
}


def document(path=None):
    return json.loads((path or DATA).read_text())


def mass_number(nuclide):
    """The A in a name like `Cs137` or `Ag110_m1`, or None if unparseable."""
    match = _MASS_NUMBER.match(nuclide)
    return int(match.group(1)) if match else None


def fission_product_heat(breakdown):
    """Decay heat from the fission products alone, in watts.

    What the benchmark measures is fission-product decay heat, not everything
    an irradiated sample makes. The archive's own FISPACT decks say so by
    suppressing the parent's capture route (`OVER U235 / ACROSS U236 0.0`),
    and below a fission threshold that distinction is the whole answer rather
    than a refinement: at the archive's 400 keV fast field, U238 captures 405
    times more than it fissions and Th232 15749 times, so an unfiltered
    inventory is mostly U239 and Np239 and has almost nothing to do with
    fission.

    Measured effect, median C/E and spread over the curve:

        U235 thermal, Dickens   1.0056 / 1.13x  ->  1.0056 / 1.13x   unchanged
        U238 fast,    Akiyama  27.5626 / 38.16x ->  0.9615 / 1.12x
        U233 fast,    Akiyama   1.0177 / 2.95x  ->  0.9913 / 1.09x
        Pu239 fast,   Akiyama   1.3195 / 23.48x ->  0.9922 / 1.07x

    The control is untouched, because for U235 thermal the actinide chain
    carries nothing measurable, which is why this went unnoticed while only
    thermal cases were looked at.

    A nuclide whose name will not parse is kept rather than dropped: losing
    heat silently is worse than counting a little too much, and the totals are
    reported beside this so the difference is visible.
    """
    return sum(watts for nuclide, watts in breakdown.items()
               if (mass_number(nuclide) or 0) < FISSION_PRODUCT_MAX_A)


def fission_rate(results, material_id, parent, step=0):
    """Fissions per parent atom per second, as the solve drove them.

    A fission edge is reported with a target of `None`, because fission names
    no single product. Summed over kinds in case an evaluation splits it.
    """
    rates = results.get_reaction_rates(material_id, step)
    if not rates or parent not in rates:
        return 0.0
    total = 0.0
    for edges in rates[parent].values():
        for target, rate in edges:
            if target is None:
                total += rate
    return total


def solve(case, combination):
    fields = document()["fields"]
    field = fields[case["field"]]
    boundaries = yani.group_structure(field["group_structure"])

    parent = case["nuclide"]
    material = yani.Material(
        {parent: 1.0},
        density=SAMPLE_DENSITY,
        volume=SAMPLE_VOLUME_CM3,
        transmutable=True,
        name=f"{parent} sample",
    )
    material_id = material.id or 0
    parent_atoms = (
        material.get_atoms_per_barn_cm()[parent] * SAMPLE_VOLUME_CM3 * 1.0e24
    )

    source = yani.NeutronSource(
        energy=yani.sources.Histogram(boundaries, field["flux"])
    )
    irradiation = case["irradiation_s"] or PULSE_SECONDS
    flux = IRRADIATION_FLUENCE / irradiation

    times = case["times_s"]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise SystemExit(f"{case['source_file']}: measured times are not increasing")
    cooldowns = [times[0]] + [b - a for a, b in zip(times, times[1:])]

    schedule = yani.PulseSchedule(
        [yani.Pulse(rate=flux, duration=(irradiation, "s"), source=source)]
        + [yani.Cooldown(duration=(dt, "s")) for dt in cooldowns]
    )

    started = time.time()
    results = material.transmute(schedule=schedule)
    elapsed = time.time() - started

    rate = fission_rate(results, material_id, parent)
    fissions = rate * parent_atoms * irradiation
    if fissions <= 0:
        raise SystemExit(
            f"{case['source_file']}: the solve drove no fissions on {parent}. "
            f"Either the library publishes no fission channel for it, or the "
            f"field does not reach one. Nothing can be normalised per fission.")

    # step_materials excludes the initial composition, so entry 0 is the end of
    # the irradiation and entries 1.. are the measured times.
    states = results.step_materials(material_id)[1:]
    if len(states) != len(times):
        raise SystemExit(
            f"{case['source_file']}: {len(states)} cooling states for "
            f"{len(times)} measured times")

    breakdowns = [state.decay_heat(by_nuclide=True) for state in states]
    heat_all = np.array([sum(b.values()) for b in breakdowns])
    heat = np.array([fission_product_heat(b) for b in breakdowns])
    f_of_t = heat * MEV_PER_JOULE / fissions
    return {
        # f(t) itself, in MeV per fission per second.
        "calculated_MeV_per_fission_s": f_of_t.tolist(),
        # t*f(t), in MeV per fission, which is what the archive tabulates and
        # therefore what the scores below compare.
        "calculated_t_f_MeV_per_fission": (f_of_t * np.array(times)).tolist(),
        # Everything the sample makes, for comparison with the line above.
        # Where these differ the parent's capture chain is contributing, which
        # is not what the measurement counted.
        "calculated_all_nuclides_MeV_per_fission_s":
            (heat_all * MEV_PER_JOULE / fissions).tolist(),
        "fission_rate_per_atom_s": rate,
        "parent_atoms": parent_atoms,
        "fissions": fissions,
        "irradiation_s": irradiation,
        "flux_n_per_cm2_s": flux,
        "burnup_fissions_per_atom": rate * irradiation,
        "solve_seconds": elapsed,
    }


def score(calculated, measured, uncertainty):
    """C/E over the points the curve actually carries."""
    pairs = [(c, m, u) for c, m, u in zip(calculated, measured, uncertainty)
             if m is not None and m > 0]
    if not pairs:
        return None
    ratio = np.array([c / m for c, m, _ in pairs])
    within = [abs(c - m) <= (u if u else 0.0) for c, m, u in pairs]
    return {
        "points": len(pairs),
        "median_ce": float(np.median(ratio)),
        "mean_deviation_percent": float(np.abs(ratio - 1.0).mean() * 100.0),
        "max_deviation_percent": float(np.abs(ratio - 1.0).max() * 100.0),
        "points_within_measurement_sigma": int(sum(within)),
    }


def run_case(system, dataset, combination):
    doc = document()
    case = dict(doc["cases"][system][dataset])
    case.setdefault("field", system.split("_", 1)[1])
    case.setdefault("nuclide", system.split("_", 1)[0])
    solved = solve(case, combination)
    scores = {}
    for component in case["components"]:
        scores[component] = score(
            solved["calculated_t_f_MeV_per_fission"],
            case[f"{component}_MeV_per_fission_s"],
            case[f"{component}_uncertainty"],
        ) if component == "total" else None
    return case, solved, scores


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--system", default="U235_thermal")
    ap.add_argument("--dataset", default="Dickens_pulse")
    ap.add_argument("--combination", default=libraries.APPLES_TO_APPLES)
    ap.add_argument("--all", action="store_true",
                    help="every validated curve (see --list for what that is)")
    ap.add_argument("--unvalidated", action="store_true",
                    help="with --all, also run the curves this benchmark does "
                         "not stand behind, for working on them")
    ap.add_argument("--list", action="store_true")
    # Hyphens, not underscores: .gitignore excludes
    # `benchmarks/*/results/*_*_*.json` to keep single-case scratch files out,
    # and `fission_decay_heat.json` matches that by accident, so the sweep
    # output would never have been committed.
    ap.add_argument("--output", type=pathlib.Path,
                    default=HERE / "results" / "fission-decay-heat.json")
    args = ap.parse_args()

    doc = document()
    if args.list:
        validated = set(VALIDATED)
        print("validated, run by --all:")
        for system, dataset in VALIDATED:
            print(f"  {system}/{dataset}")
        print("\nin the archive but not validated, run by --all --unvalidated:")
        for system in sorted(doc["cases"]):
            for dataset in sorted(doc["cases"][system]):
                if (system, dataset) not in validated:
                    print(f"  {system}/{dataset}")
        print()
        for reason, text in EXCLUDED.items():
            print(f"[{reason}] {text}\n")
        return 0

    combination = libraries.resolve([args.combination])[0]
    libraries.apply(combination, yani)

    if args.all and args.unvalidated:
        todo = [(s, d) for s in sorted(doc["cases"]) for d in sorted(doc["cases"][s])]
    elif args.all:
        todo = list(VALIDATED)
    else:
        todo = [(args.system, args.dataset)]

    records, failures = [], {}
    for system, dataset in todo:
        key = f"{system}/{dataset}"
        try:
            case, solved, scores = run_case(system, dataset, combination)
        except Exception as exc:  # noqa: BLE001 - recorded, not swallowed
            failures[key] = f"{type(exc).__name__}: {exc}"
            print(f"  {key}: FAILED {exc}", flush=True)
            continue
        total = scores.get("total")
        summary = (f"median C/E {total['median_ce']:.3f}, "
                   f"mean deviation {total['mean_deviation_percent']:.1f}%, "
                   f"{total['points_within_measurement_sigma']}/{total['points']} "
                   f"within measurement sigma") if total else "no total component"
        print(f"  {key} ({case['author']}, {case['irradiation']}): {summary}", flush=True)
        records.append({"system": system, "dataset": dataset, **case,
                        **solved, "scores": scores})

    if args.all:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "yani_version": yani.__version__,
            "combination": libraries.as_dict(combination),
            "validated": [f"{s}/{d}" for s, d in VALIDATED],
            "excluded_reasons": EXCLUDED,
            "includes_unvalidated": bool(args.unvalidated),
            "curves": records,
            "failures": failures,
        }
        tmp = args.output.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=1) + "\n")
        tmp.replace(args.output)
        print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
