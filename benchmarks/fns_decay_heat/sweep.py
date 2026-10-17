#!/usr/bin/env python3
"""Run every FNS experiment against every nuclear-data combination.

    sweep.py                                  # 132 experiments x every combination
    sweep.py --combination tendl-2017+decay-2012   # just the apples-to-apples one
    sweep.py --experiment 2000exp_5min        # the campaign covering all 73 foils
    sweep.py --case Fe --case W --case Nb     # a few foils, all combinations
    sweep.py --workers 3
    sweep.py --uncertainty --samples 32       # with nuclear-data error bars

Writes one JSON per combination into `results/`, holding every foil's calculated
curve, the measurement, FISPACT-II's published curve where the archive has one,
and the scores. That is what the site's pages and plots are generated from.

## Why it is shaped like this

A solve is single-threaded and takes a couple of minutes, most of it spent
reducing a 2800-nuclide network down to what one foil can reach, so 132 of them
in series is a long afternoon. They are independent, so they run in a pool.

Each worker loads the library once and keeps it, which is the whole reason for
a pool of long-lived processes rather than a process per case: the parse is
paid `--workers` times instead of 132 times. It also sets the memory bill, at
something like 1.6 GB resident per worker, so `--workers` defaults to leaving a
core and its share of memory alone rather than to the core count.

Results are written as they arrive rather than at the end. A sweep that dies on
case 130 used to lose 129 good answers.

`--uncertainty` costs one solve per replica instead of one per case, so it
multiplies the wall time by the replica count. Give `--samples` a number when
sweeping: left adaptive, each case chooses its own replica count and the sweep
stops being able to say how long it will take.
"""

import argparse
import json
import multiprocessing
import pathlib
import sys
import time
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common import libraries, uncertainty as unc  # noqa: E402

import case as fns_case  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent

# Set once per worker process, so the library is parsed on the first case that
# worker handles and reused for every case after it.
_STATE = {}


def _init(combination_name, data_path, uncertainty):
    import yani

    import run as fns_run

    combination = libraries.BY_NAME[combination_name]
    libraries.apply(combination, yani)
    _STATE["combination"] = combination
    _STATE["data_path"] = data_path
    _STATE["run"] = fns_run
    _STATE["yani"] = yani
    # Built inside the worker: a DataUncertainty is a compiled object and the
    # pool is spawned, so the seed and the replica count travel instead of it.
    _STATE["uncertainty"] = (
        yani.DataUncertainty(seed=uncertainty["seed"],
                             samples=uncertainty["samples"])
        if uncertainty else None)


def _solve(selection_entry):
    """One experiment, in whichever worker picks it up.

    Returns `(key, entry, failure, data_releases)`: the result, or the
    traceback of the failure, and which nuclear-data release each library the
    solve read came from, which only the worker can see.
    """
    name, experiment = selection_entry
    key = f"{name}/{experiment}"
    try:
        case = fns_case.load(name, experiment, _STATE["data_path"])
        solved = _STATE["run"].run(
            case, _STATE["combination"], _STATE["uncertainty"])
        calculated = solved.heat
        entry = {
            "case": name,
            "experiment": experiment,
            "time_unit": case.time_unit,
            "times": case.times.tolist(),
            "measured_uW_per_g": case.measured.tolist(),
            "measured_uncertainty_uW_per_g": case.uncertainty.tolist(),
            "yani_uW_per_g": calculated.tolist(),
            "yani_sigma_uW_per_g": (solved.sigma.tolist()
                                    if solved.sigma is not None else None),
            "data_uncertainty_info": unc.summarise(solved.uncertainty_info),
            "uncertainty_replicas": solved.replicas,
            "metrics": fns_case.score(calculated, case, solved.sigma),
            "solve_seconds": solved.elapsed,
            "leaders": _STATE["run"].leaders(solved.breakdown),
            "composition_mass_fraction": case.composition,
        }
        if case.fispact is not None:
            entry["fispact_uW_per_g"] = case.fispact.tolist()
            entry["fispact_library"] = case.fispact_library
            entry["fispact_metrics"] = fns_case.score(case.fispact, case)
        return key, entry, None, solved.data_releases
    except Exception:
        # One foil that will not solve must not cost the other 131. The
        # traceback is kept in the output so a failure is visible on the site
        # rather than only absent from it.
        return key, None, traceback.format_exc(), None


def existing(path):
    """What a previous run of this combination already got through.

    `(results, failures, document)`, the last being the whole file, or empty
    ones when there is no readable file.
    """
    if not path.is_file():
        return {}, {}, {}
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}, {}, {}
    return document.get("results", {}), document.get("failures", {}), document


def write(path, combination, results, failures, selection, seconds, version,
          releases, uncertainty=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "benchmark": "fns_decay_heat",
        "combination": libraries.as_dict(combination, releases),
        "yani_version": version,
        "uncertainty": uncertainty,
        "experiments": len(selection),
        "solved": len(results),
        "failed": len(failures),
        "wall_seconds": seconds,
        "results": results,
        "failures": failures,
    }
    # Written aside and moved, so a sweep killed mid-write does not leave a
    # truncated file that the site generator would happily read.
    scratch = path.with_suffix(".json.part")
    scratch.write_text(json.dumps(payload, indent=1, sort_keys=True))
    scratch.replace(path)


def yani_version():
    try:
        import yani
        return getattr(yani, "__version__", "unknown")
    except ImportError:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--combination", action="append", default=[],
                        help="repeatable; default is every combination")
    parser.add_argument("--case", action="append", default=[],
                        help="repeatable; default is all 73 foils")
    parser.add_argument("--experiment", action="append", default=[],
                        help="repeatable; default is all three campaigns")
    parser.add_argument("--data", type=pathlib.Path, help="benchmark JSON")
    parser.add_argument("--output", type=pathlib.Path, default=HERE / "results")
    parser.add_argument("--workers", type=int, default=0,
                        help="parallel solves; 0 picks one fewer than the cores")
    parser.add_argument("--redo", action="store_true",
                        help="re-solve cases already in the output file")
    parser.add_argument("--uncertainty", action="store_true",
                        help="propagate cross-section covariance onto the curves")
    parser.add_argument("--samples", type=int,
                        help="fixed replica count (recommended with --uncertainty)")
    parser.add_argument("--seed", type=int, default=42,
                        help="covariance sampling seed (default: 42)")
    args = parser.parse_args()

    combinations = libraries.resolve(args.combination)
    selection = [
        (name, experiment) for name, experiment in fns_case.every(args.data)
        if (not args.case or name in args.case)
        and (not args.experiment or experiment in args.experiment)
    ]
    if not selection:
        raise SystemExit("no experiments matched --case/--experiment")

    workers = args.workers or max(1, (multiprocessing.cpu_count() or 2) - 1)
    uncertainty = ({"seed": args.seed, "samples": args.samples}
                   if args.uncertainty else None)
    print(f"{len(selection)} experiments x {len(combinations)} combinations "
          f"= {len(selection) * len(combinations)} solves, {workers} workers")
    if uncertainty:
        print(f"  uncertainty on, seed {args.seed}, "
              f"{args.samples or 'adaptive'} replicas per solve: expect the "
              f"wall time to scale with that")

    version = yani_version()
    # 'spawn' rather than fork: yani's nuclear-data cache is process-wide state
    # in a compiled extension, and inheriting a half-loaded copy of it is not
    # something to rely on.
    context = multiprocessing.get_context("spawn")
    summary = []

    for combination in combinations:
        destination = args.output / f"{combination.name}.json"
        results, failures, previous = (
            ({}, {}, {}) if args.redo else existing(destination))
        todo = [entry for entry in selection
                if f"{entry[0]}/{entry[1]}" not in results]

        print(f"\n{combination.name}: xs {combination.cross_sections}, "
              f"reactions {combination.reactions}, "
              f"branching {combination.branching}, decay {combination.decay}")
        if not todo:
            print(f"  already complete ({len(results)} experiments)")
            summary.append((combination.name, len(results), len(failures)))
            continue
        if len(todo) < len(selection):
            print(f"  resuming: {len(selection) - len(todo)} already done")
        releases = libraries.DataReleases.resumed(
            combination, destination, previous, len(results))

        started = time.time()
        done = 0
        with context.Pool(processes=min(workers, len(todo)), initializer=_init,
                          initargs=(combination.name, args.data,
                                    uncertainty)) as pool:
            for key, entry, failure, read in pool.imap_unordered(_solve, todo):
                done += 1
                if entry is None:
                    failures[key] = failure
                    print(f"  [{done}/{len(todo)}] {key}: FAILED")
                else:
                    releases.read(read)
                    results.pop(key, None)
                    failures.pop(key, None)
                    results[key] = entry
                    print(f"  [{done}/{len(todo)}] {key}: "
                          f"{entry['metrics']['mean_deviation_percent']:.1f}%",
                          flush=True)
                # Written every time: a solve costs minutes and a write costs
                # milliseconds, so there is nothing to batch for.
                write(destination, combination, results, failures, selection,
                      time.time() - started, version, releases, uncertainty)

        print(f"  {combination.name}: {len(results)} solved, {len(failures)} "
              f"failed, {(time.time() - started) / 60:.1f} min -> {destination}")
        summary.append((combination.name, len(results), len(failures)))

    print("\nsummary")
    for name, solved, failed in summary:
        print(f"  {name:30s} {solved:4d} solved  {failed:3d} failed")


if __name__ == "__main__":
    main()
