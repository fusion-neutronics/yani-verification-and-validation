#!/usr/bin/env python3
"""Run one FNS decay-heat experiment with yani and score it against the measurement.

The FNS decay-heat experiments (JAEA Fusion Neutronics Source, distributed by the
IAEA as part of CoNDERC) hold a 1 g foil in a 14 MeV field of about 1e10 n/cm2/s,
pull it out, and measure the heat its activation products give off as it cools.

    run.py                                  # iron, the default
    run.py --case W
    run.py --case SS316 --experiment 1996exp_7hour
    run.py --case Nb --combination tendl-2025
    run.py --uncertainty                    # with a nuclear-data error bar
    run.py --list                           # every foil and its experiments

There is no neutron transport here. The benchmark publishes the spectrum the
foil actually saw, so that spectrum is the input and yani collapses it against
the cross sections to get one-group reaction rates, then solves the Bateman
system over the schedule.

The nuclear data is named by `--combination`, one of the entries in
`benchmarks/common/libraries.py`, and every one of yani's five data settings is
written from it. The default, `tendl-2017`, is the library FISPACT-II was run
with for the results published in the same archive, which is what makes the
comparison a statement about the two codes rather than about two libraries.

`--uncertainty` adds an error bar to the calculated curve, resampling the
activation cross sections from their ENDF MF=33 covariance and re-solving the
schedule per replica. It is off by default because it costs one solve per
replica rather than one in total, and because a run without it is bit-identical
to a run before the option existed.

The band is taken as the spread of decay heat over the ensemble, not from the
per-nuclide sigmas. Decay heat is a sum over the whole inventory and a parent
and its daughter do not move independently, so adding per-nuclide sigmas in
quadrature would assume away exactly the correlation the resampling exists to
keep.
"""

import argparse
import collections
import functools
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import yani  # noqa: E402
from common import libraries, uncertainty as unc  # noqa: E402

import case as fns_case  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

# How hard to try before giving up on reaching the data at all.
_COVERAGE_ATTEMPTS = 4
_COVERAGE_BACKOFF_S = 2.0


Solved = collections.namedtuple(
    "Solved", "heat breakdown elapsed sigma uncertainty_info replicas")


class ZeroActivation(Exception):
    """An irradiated foil came back with no activation products at all.

    A plain `Exception` and not `SystemExit`, because this is raised inside a
    `multiprocessing` pool worker by the sweep. CPython's `pool.worker` catches
    only `Exception`, so a `SystemExit` escapes it, kills the worker, and the
    task it was holding is never returned: `imap_unordered` then waits for a
    result that can no longer arrive and the sweep hangs on that foil forever
    rather than recording it as a failure.
    """


class MissingEvaluations(Exception):
    """The cross-section library has no evaluation for one of the foil's elements.

    Raised before the solve rather than after it, because the solve does not
    fail: a foil whose element the library does not publish comes back with
    almost no activation and a C/E near zero, which reads as a library being
    wrong about the physics rather than a library not containing the element.
    """


class CoverageUnknown(RuntimeError):
    """The library could not be asked whether it publishes a nuclide.

    Distinct from a library answering "no". A dropped connection or a
    truncated body means the question went unanswered, and answering it "no"
    anyway is how this benchmark came to report that TENDL-2017 publishes no
    evaluation for gold.
    """


# The release manifest answering. yani reads a library's manifest before any
# file it lists, and refuses a nuclide the manifest does not list with "Nuclide
# 'Os190' is not available in 'fendl-3.2d' (release ...)". That is the one
# answer that is about the library. Anything else, a 404 included, is the data
# failing to arrive: a library not yet published in the release layout
# (".../latest.json answers 404"), or a file the manifest lists and the origin
# does not serve ("404, but the release manifest lists ...").
_ABSENT_MARKERS = ("is not available in",)


@functools.lru_cache(maxsize=None)
def _is_available(nuclide, library):
    """Can `library` supply cross sections for `nuclide`?

    Memoised because a sweep asks the same question for the same 73 foils in
    every worker, and the answer is a property of the library rather than of
    the case. The load itself is what a solve would do anyway, so on a warm
    cache this costs a parse and no download.

    This used to be `except Exception: return False`, which folded every way of
    failing to reach the data into the one answer that reads as a statement
    about the library. A sweep with sixteen workers against one origin drops
    connections, and a dropped connection became "tendl-2017 publishes no
    evaluation for Au (Au197)" in the results file, for an evaluation that is
    published and that the same process reads without complaint a minute later.
    Twenty of 132 experiments failed that way in one run, and nothing in the
    output said they had.

    So the release manifest not listing the nuclide answers False, and
    everything else retries and then raises. A 404 is no longer an answer:
    since yani 0.21.0 the manifest says what a release holds, and a 404 is the
    origin not serving what it promised, which is how a library not yet
    published in the release layout would otherwise read as "tendl-2017
    publishes no evaluation for Fe".
    """
    last = None
    for attempt in range(_COVERAGE_ATTEMPTS):
        try:
            yani.Nuclide(nuclide).read_nuclear_data(library)
            return True
        except Exception as exc:  # noqa: BLE001 - re-raised below unless the manifest answered
            message = str(exc).lower()
            if any(marker in message for marker in _ABSENT_MARKERS):
                return False
            last = exc
            if attempt + 1 < _COVERAGE_ATTEMPTS:
                time.sleep(_COVERAGE_BACKOFF_S * (attempt + 1))
    raise CoverageUnknown(
        f"could not determine whether {library} publishes {nuclide}, after "
        f"{_COVERAGE_ATTEMPTS} attempts: {type(last).__name__}: {last}. "
        f"This is a failure to reach the data, not a gap in the library, and "
        f"is raised rather than recorded as one."
    ) from last


def uncovered(case, combination):
    """Foil elements the cross-section library cannot represent at all.

    Returns `{element: [its natural nuclides]}` for every element where not one
    naturally occurring isotope is published. A partial gap is left alone: a
    missing minor isotope changes a rate, which is a library being different,
    while a missing element means the foil cannot activate at all, which is a
    library being absent.
    """
    library = combination.cross_sections
    missing = {}
    for element in sorted(case.composition):
        nuclides = yani.Element(element).get_nuclides()
        if nuclides and not any(_is_available(n, library) for n in nuclides):
            missing[element] = list(nuclides)
    return missing


def _replica_heat(results, material_id, step, case):
    """Specific decay heat [uW/g] for every replica at one schedule step.

    `step` indexes the way `get_material` does, where 0 is the initial
    composition, so it is one ahead of the `step_materials` index.

    Each replica is a full inventory, and decay heat is evaluated once per
    replica from it. That keeps the correlation between a parent and its
    daughter, which is the whole reason the ensemble is handed back rather than
    a set of per-nuclide sigmas.
    """
    inventories = results.get_uncertainty_inventories(
        material_id=material_id, step=step)
    if not inventories:
        return None
    heats = []
    for inventory in inventories:
        replica = yani.Material.from_atom_densities(
            inventory,
            volume=case.mass_g / case.density,
            temperature=fns_case.TEMPERATURE,
        )
        heats.append(replica.decay_heat() / case.mass_g * 1e6)
    return np.array(heats, dtype=float)


def run(case, combination, uncertainty=None):
    """Specific decay heat [uW/g] at each measured time, and its breakdown.

    Pass a `yani.DataUncertainty` as `uncertainty` and the result also carries
    a standard deviation per measured point, plus yani's own report of what the
    covariance did and did not cover.
    """
    libraries.apply(combination, yani)

    missing = uncovered(case, combination)
    if missing:
        detail = "; ".join(f"{element} ({', '.join(nuclides)})"
                           for element, nuclides in missing.items())
        raise MissingEvaluations(
            f"{case.name}/{case.experiment}: {combination.cross_sections} "
            f"publishes no evaluation for {detail}. The foil cannot activate, "
            f"so this is a gap in the library's coverage and not a measure of "
            f"how well it describes the physics.\n"
            f"  combination: {combination.name}\n"
            f"  cross sections: {combination.cross_sections}")

    # The histogram carries the shape; the pulse rate carries the magnitude.
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

    started = time.time()
    results = material.transmute(schedule, data_uncertainty=uncertainty)
    elapsed = time.time() - started

    material_id = material.id or 0
    # `step_materials` is the list transmute() used to return on its own: one
    # state per schedule step with no initial entry, so the irradiation pulses
    # come first and the measurement starts after them.
    states = results.step_materials(material_id)
    cooling_from = len(case.irradiation)

    heat, breakdown, sigma = [], [], []
    replica_count = None
    for offset, state in enumerate(states[cooling_from:]):
        contributions = state.decay_heat(by_nuclide=True)
        heat.append(sum(contributions.values()) / case.mass_g * 1e6)
        breakdown.append({nuclide: watts / case.mass_g * 1e6
                          for nuclide, watts in contributions.items()})
        if uncertainty is not None:
            # +1 because step 0 is the initial composition, which step_materials
            # leaves out.
            replicas = _replica_heat(
                results, material_id, cooling_from + offset + 1, case)
            if replicas is None:
                sigma.append(0.0)
                continue
            replica_count = replicas.size
            sigma.append(float(replicas.std(ddof=1)) if replicas.size > 1 else 0.0)
    heat = np.array(heat)

    # An irradiated foil always activates, so heat that is identically zero
    # means the network produced nothing at all. Reported as C/E 0.000 it reads
    # like a physics result rather than the wiring mistake it invariably is, and
    # a sweep would log it foil after foil without ever failing.
    if not heat.any():
        raise ZeroActivation(
            f"{case.name}/{case.experiment}: every cooling step came out at zero "
            f"decay heat, so the transmutation produced no activation products.\n"
            f"  combination: {combination.name}\n"
            f"  cross sections: {combination.cross_sections}, "
            f"reactions: {combination.reactions}"
        )
    return Solved(
        heat=heat,
        breakdown=breakdown,
        elapsed=elapsed,
        sigma=np.array(sigma) if sigma else None,
        uncertainty_info=results.get_data_uncertainty_info(material_id),
        replicas=replica_count,
    )


def leaders(breakdown, count=3):
    """The nuclides carrying most of the heat, summed over the cooling."""
    totals = {}
    for step in breakdown:
        for nuclide, value in step.items():
            totals[nuclide] = totals.get(nuclide, 0.0) + value
    return sorted(totals, key=totals.get, reverse=True)[:count]


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", default="Fe", help="FNS foil (default: Fe)")
    parser.add_argument("--experiment", help="which campaign (default: 2000exp_5min)")
    parser.add_argument("--combination", default=libraries.APPLES_TO_APPLES,
                        help=f"nuclear data (default: {libraries.APPLES_TO_APPLES})")
    parser.add_argument("--data", type=pathlib.Path, help="benchmark JSON")
    parser.add_argument("--uncertainty", action="store_true",
                        help="propagate cross-section covariance onto the curve")
    parser.add_argument("--samples", type=int,
                        help="fixed replica count (default: adaptive, until each "
                             "sigma is known to 5%%, at least 128 replicas)")
    parser.add_argument("--seed", type=int, default=42,
                        help="covariance sampling seed (default: 42)")
    parser.add_argument("--output", type=pathlib.Path, default=HERE / "results",
                        help="where the result JSON goes")
    parser.add_argument("--list", action="store_true",
                        help="list the foils and their experiments, then exit")
    args = parser.parse_args()

    if args.list:
        for name in fns_case.cases(args.data):
            print(f"{name:8s} {' '.join(fns_case.experiments(name, args.data))}")
        return

    combination = libraries.resolve([args.combination])[0]
    case = fns_case.load(args.case, args.experiment, args.data)
    print(f"case:        {case.describe()}")
    print(f"spectrum:    {fns_case.GROUPS} groups, {case.spectrum.sum():.4g} n/cm2/s")
    print(f"combination: {combination.name}")
    print(f"             xs {combination.cross_sections}, "
          f"reactions {combination.reactions}, branching {combination.branching}, "
          f"decay {combination.decay}")

    uncertainty = None
    if args.uncertainty:
        uncertainty = yani.DataUncertainty(seed=args.seed, samples=args.samples)
        print(f"uncertainty: cross-section covariance, seed {args.seed}, "
              f"{args.samples or 'adaptive'} replicas")

    solved = run(case, combination, uncertainty)
    calculated, breakdown, elapsed = solved.heat, solved.breakdown, solved.elapsed
    metrics = fns_case.score(calculated, case, solved.sigma)
    print(f"solve:       {elapsed:.1f} s"
          + (f" over {solved.replicas} replicas" if solved.replicas else ""))

    header = f"\n{case.time_unit:>9}  {'measured':>10}  {'yani':>10}"
    if solved.sigma is not None:
        header += f"  {'+/-':>9}"
    header += f"  {'C/E':>6}"
    if case.fispact is not None:
        header += f"  {'FISPACT':>10}  {'C/E':>6}"
    print(header)
    for index, time_point in enumerate(case.times):
        line = (f"{time_point:9.2f}  {case.measured[index]:10.3e}  "
                f"{calculated[index]:10.3e}")
        if solved.sigma is not None:
            line += f"  {solved.sigma[index]:9.2e}"
        line += f"  {metrics['ratio'][index]:6.3f}"
        if case.fispact is not None:
            line += (f"  {case.fispact[index]:10.3e}  "
                     f"{case.fispact[index] / case.measured[index]:6.3f}")
        print(line)

    print(f"\nyani     mean deviation {metrics['mean_deviation_percent']:5.1f}%, "
          f"median C/E {metrics['median_ratio']:.3f}")
    if case.fispact is not None:
        fispact_metrics = fns_case.score(case.fispact, case)
        print(f"FISPACT  mean deviation "
              f"{fispact_metrics['mean_deviation_percent']:5.1f}%, "
              f"median C/E {fispact_metrics['median_ratio']:.3f}  "
              f"({case.fispact_library}, as published in the archive)")
    print(f"measurement sigma {metrics['median_measurement_sigma_percent']:.1f}% "
          f"(median), {metrics['points_within_sigma']}/{metrics['points']} yani "
          f"points inside it")
    if solved.sigma is not None:
        print(f"nuclear-data sigma on yani "
              f"{metrics['median_calculated_sigma_percent']:.1f}% (median), "
              f"{metrics['points_within_combined_sigma']}/{metrics['points']} "
              f"points agreeing within the two combined")
        for line in unc.describe(solved.uncertainty_info):
            print(line)
    print(f"heat carried by: {' '.join(leaders(breakdown))}")

    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f"{case.name}_{case.experiment}_{combination.name}.json"
    destination.write_text(json.dumps({
        "case": case.name,
        "experiment": case.experiment,
        "combination": libraries.as_dict(combination),
        "yani_version": getattr(yani, "__version__", "unknown"),
        "time_unit": case.time_unit,
        "times": case.times.tolist(),
        "measured_uW_per_g": case.measured.tolist(),
        "measured_uncertainty_uW_per_g": case.uncertainty.tolist(),
        "yani_uW_per_g": calculated.tolist(),
        "yani_sigma_uW_per_g": (solved.sigma.tolist()
                                if solved.sigma is not None else None),
        "data_uncertainty_info": unc.summarise(solved.uncertainty_info),
        "uncertainty_replicas": solved.replicas,
        "fispact_uW_per_g": case.fispact.tolist() if case.fispact is not None else None,
        "fispact_library": case.fispact_library,
        "metrics": metrics,
        "solve_seconds": elapsed,
        "by_nuclide_uW_per_g": breakdown,
    }, indent=2))
    print(f"\nwrote {destination}")


if __name__ == "__main__":
    main()
