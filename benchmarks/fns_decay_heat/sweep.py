#!/usr/bin/env python3
"""Run every FNS experiment against every nuclear-data combination.

    sweep.py                                  # 132 experiments x every combination
    sweep.py --combination tendl-2017         # just the apples-to-apples one
    sweep.py --experiment 2000exp_5min        # just the campaign covering all 73 foils
    sweep.py --case Fe --case W --case Nb     # a few foils, all combinations

Writes one JSON per combination into `results/`, holding every foil's calculated
curve, the measurement, FISPACT-II's published curve where the archive has one,
and the scores. That is what the site's pages and plots are generated from.

Each combination runs in its own process. The parsed nuclear data for a library
stays resident once loaded, which is what makes the second foil fast, but it
also means holding two libraries at once for no reason; a fresh process per
combination gives the memory back. Restarting is cheap: `--resume` skips a
combination whose output is already complete.
"""

import argparse
import json
import multiprocessing
import pathlib
import sys
import time
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from common import libraries  # noqa: E402

import case as fns_case  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def _run_combination(combination_name, selection, data_path, output_dir, queue):
    """One combination over the selected experiments, in a process of its own."""
    import yani

    import run as fns_run

    combination = libraries.BY_NAME[combination_name]
    results, failures = {}, {}
    started = time.time()

    for index, (name, experiment) in enumerate(selection, start=1):
        key = f"{name}/{experiment}"
        try:
            case = fns_case.load(name, experiment, data_path)
            calculated, breakdown, elapsed = fns_run.run(case, combination)
            metrics = fns_case.score(calculated, case)
            entry = {
                "case": name,
                "experiment": experiment,
                "time_unit": case.time_unit,
                "times": case.times.tolist(),
                "measured_uW_per_g": case.measured.tolist(),
                "measured_uncertainty_uW_per_g": case.uncertainty.tolist(),
                "yani_uW_per_g": calculated.tolist(),
                "metrics": metrics,
                "solve_seconds": elapsed,
                "leaders": fns_run.leaders(breakdown),
                "composition_mass_fraction": case.composition,
            }
            if case.fispact is not None:
                entry["fispact_uW_per_g"] = case.fispact.tolist()
                entry["fispact_library"] = case.fispact_library
                entry["fispact_metrics"] = fns_case.score(case.fispact, case)
            results[key] = entry
            queue.put(("progress", combination_name, index, len(selection), key,
                       metrics["mean_deviation_percent"]))
        except Exception:
            # One foil that will not solve must not cost the other 131. The
            # traceback is kept in the output so a failure is visible on the
            # site rather than only absent from it.
            failures[key] = traceback.format_exc()
            queue.put(("failed", combination_name, index, len(selection), key, None))

    document = {
        "benchmark": "fns_decay_heat",
        "combination": libraries.as_dict(combination),
        "yani_version": getattr(yani, "__version__", "unknown"),
        "experiments": len(selection),
        "solved": len(results),
        "failed": len(failures),
        "wall_seconds": time.time() - started,
        "results": results,
        "failures": failures,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{combination_name}.json"
    destination.write_text(json.dumps(document, indent=1, sort_keys=True))
    queue.put(("done", combination_name, len(results), len(failures),
               str(destination), time.time() - started))


def complete(path, expected):
    """Is this combination's output already there and covering everything asked?"""
    if not path.is_file():
        return False
    try:
        document = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    return set(document.get("results", {})) >= expected


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
    parser.add_argument("--resume", action="store_true",
                        help="skip combinations already written in full")
    args = parser.parse_args()

    combinations = libraries.resolve(args.combination)
    selection = [
        (name, experiment) for name, experiment in fns_case.every(args.data)
        if (not args.case or name in args.case)
        and (not args.experiment or experiment in args.experiment)
    ]
    if not selection:
        raise SystemExit("no experiments matched --case/--experiment")

    print(f"{len(selection)} experiments x {len(combinations)} combinations "
          f"= {len(selection) * len(combinations)} solves")
    expected = {f"{name}/{experiment}" for name, experiment in selection}

    # 'spawn' rather than fork: yani's data cache is process-wide state in a
    # compiled extension, and inheriting a half-loaded copy of it is not
    # something to rely on.
    context = multiprocessing.get_context("spawn")
    summary = []

    for combination in combinations:
        destination = args.output / f"{combination.name}.json"
        if args.resume and complete(destination, expected):
            print(f"\n{combination.name}: already complete, skipping")
            continue

        print(f"\n{combination.name}: xs {combination.cross_sections}, "
              f"reactions {combination.reactions}, "
              f"branching {combination.branching}, decay {combination.decay}")
        queue = context.Queue()
        worker = context.Process(
            target=_run_combination,
            args=(combination.name, selection, args.data, args.output, queue))
        worker.start()

        while True:
            message = queue.get()
            if message[0] == "done":
                _, name, solved, failed, path, seconds = message
                print(f"  {name}: {solved} solved, {failed} failed, "
                      f"{seconds / 60:.1f} min -> {path}")
                summary.append((name, solved, failed))
                break
            _, name, index, total, key, deviation = message
            if message[0] == "failed":
                print(f"  [{index}/{total}] {key}: FAILED")
            else:
                print(f"  [{index}/{total}] {key}: {deviation:.1f}%")
        worker.join()

    print("\nsummary")
    for name, solved, failed in summary:
        print(f"  {name:30s} {solved:4d} solved  {failed:3d} failed")


if __name__ == "__main__":
    main()
