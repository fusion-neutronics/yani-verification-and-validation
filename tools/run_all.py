#!/usr/bin/env python3
"""Run everything, or say what running everything would cost.

    python tools/run_all.py --plan          # what would run, and roughly how long
    python tools/run_all.py                 # run it
    python tools/run_all.py --stage fns     # one stage
    python tools/run_all.py --workers 8     # a machine with cores to spare

This is the entry point for a full local run. Every stage underneath it
resumes, so this can be stopped with Ctrl-C and started again, and it will pick
up where it left off rather than redoing anything. Nothing here is a wrapper
around something you could not run yourself: `--plan` prints the exact commands,
and running them by hand does the same thing.

## The stages

| stage | what it does | rough cost |
| --- | --- | --- |
| `fns` | 132 FNS decay-heat experiments x 10 data combinations | the long one |
| `ecs` | 365 effective cross sections x 10 data combinations | medium |
| `openmc` | the FNS experiments again, through OpenMC | needs its own data |
| `site` | the result JSON into pages and figures | seconds |

`openmc` is skipped unless `--openmc-chain` is given, because it needs an
OpenMC install, a depletion chain and an HDF5 cross-section library that the
other stages do not. See `benchmarks/fns_decay_heat/run_openmc.py --list-chains`.

## Error bars

`--uncertainty` turns on nuclear-data uncertainty in the `fns` and `ecs`
stages, which resamples the activation cross sections from their covariance and
re-solves per replica. It multiplies the solve count by `--samples`, so it is
off by default and `--plan` folds it into the estimate rather than letting a
reader discover it. A short run with `--samples 32` on one combination is the
sensible way to start.

## What it will download

Nuclear data, once, into `~/.cache/yamc`. yani fetches the sections it needs on
first use, and a combination that names a library not yet cached will spend a
while getting it before the first solve. TENDL-2017 is about 13 GB. Ten
combinations do not mean ten downloads -- they name five libraries between them
-- but they do mean tens of gigabytes in that cache, so check the disk before
starting a full run rather than during one.
"""

import argparse
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from common import libraries  # noqa: E402

# Measured on four cores with three workers: about 0.75 minutes of wall clock
# per FNS solve. Only used for the estimate that --plan prints, so being wrong
# costs nothing but a wrong estimate.
FNS_MINUTES_PER_SOLVE = 0.75
ECS_MINUTES_PER_SOLVE = 0.5


def python():
    return sys.executable or "python3"


def uncertainty_flags(args):
    """The covariance flags a sweep stage inherits from this driver."""
    if not args.uncertainty:
        return []
    flags = ["--uncertainty", "--seed", str(args.seed)]
    if args.samples:
        flags += ["--samples", str(args.samples)]
    return flags


def stages(args):
    """(name, description, command) for everything that would run."""
    plan = []

    if "fns" in args.stage:
        command = [python(), str(ROOT / "benchmarks" / "fns_decay_heat" / "sweep.py"),
                   "--workers", str(args.workers)]
        if args.experiment:
            for experiment in args.experiment:
                command += ["--experiment", experiment]
        for name in args.combination:
            command += ["--combination", name]
        command += uncertainty_flags(args)
        plan.append(("fns", "FNS decay heat, every combination", command))

    if "ecs" in args.stage:
        for combination in libraries.resolve(args.combination):
            command = [python(),
                       str(ROOT / "benchmarks" / "effective_cross_sections" / "run.py"),
                       "--combination", combination.name]
            command += uncertainty_flags(args)
            plan.append((f"ecs:{combination.name}",
                         f"effective cross sections, {combination.name}", command))

    if "openmc" in args.stage and args.openmc_chain:
        command = [python(),
                   str(ROOT / "benchmarks" / "fns_decay_heat" / "run_openmc.py"),
                   "--chain", str(args.openmc_chain)]
        if args.openmc_chain_name:
            command += ["--chain-name", args.openmc_chain_name]
        for experiment in args.experiment:
            command += ["--experiment", experiment]
        plan.append(("openmc", "FNS decay heat through OpenMC", command))

    if "site" in args.stage:
        plan.append(("site", "pages and figures",
                     [python(), str(ROOT / "tools" / "build_site.py")]))
    return plan


def estimate(args):
    """Rough wall-clock minutes, so --plan can say whether this is a coffee or a day."""
    combinations = len(libraries.resolve(args.combination))
    experiments = 132 if not args.experiment else 73 * len(args.experiment)
    # One solve per replica rather than one per case, so the replica count
    # multiplies straight through. Adaptive sampling has no number to use, so
    # 100 stands in for it, which is the point of saying so in --plan.
    replicas = 1
    if args.uncertainty:
        replicas = args.samples or 100
    fns = (experiments * combinations * replicas
           * FNS_MINUTES_PER_SOLVE / max(1, args.workers))
    ecs = (365 * combinations * replicas
           * ECS_MINUTES_PER_SOLVE / max(1, args.workers))
    total = 0.0
    if "fns" in args.stage:
        total += fns
    if "ecs" in args.stage:
        total += ecs
    return total


def check_environment(args):
    """Say what is missing before spending hours discovering it."""
    problems = []
    try:
        import yani  # noqa: F401
    except ImportError:
        problems.append("yani is not installed: pip install -r requirements.txt")
    try:
        import matplotlib  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        problems.append("matplotlib/numpy missing: pip install -r requirements.txt")

    for benchmark, filename in (("fns_decay_heat", "fns_data.json"),
                                ("effective_cross_sections", "rr_data.json")):
        path = ROOT / "benchmarks" / benchmark / "data" / filename
        if not path.is_file():
            problems.append(f"{path} missing: run "
                            f"benchmarks/{benchmark}/build_data.py")

    free_gb = shutil.disk_usage(pathlib.Path.home()).free / 1e9
    if free_gb < 20 and "fns" in args.stage:
        problems.append(
            f"{free_gb:.0f} GB free on the volume holding ~/.cache/yamc. A full "
            f"run caches tens of GB of nuclear data; 20 GB is a floor and not a "
            f"recommendation.")
    return problems


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", action="append", default=[],
                        choices=["fns", "ecs", "openmc", "site"],
                        help="repeatable; default is all of them")
    parser.add_argument("--combination", action="append", default=[],
                        help="repeatable; default is every combination")
    parser.add_argument("--experiment", action="append", default=[],
                        help="restrict the FNS stages to these campaigns")
    parser.add_argument("--workers", type=int, default=0,
                        help="parallel FNS solves; 0 leaves one core alone")
    parser.add_argument("--openmc-chain", type=pathlib.Path,
                        help="enables the openmc stage")
    parser.add_argument("--openmc-chain-name")
    parser.add_argument("--plan", action="store_true",
                        help="print the commands and the estimate, run nothing")
    parser.add_argument("--keep-going", action="store_true",
                        help="carry on to the next stage when one fails")
    parser.add_argument("--uncertainty", action="store_true",
                        help="propagate cross-section covariance in the fns/ecs stages")
    parser.add_argument("--samples", type=int,
                        help="replica count for --uncertainty (recommended)")
    parser.add_argument("--seed", type=int, default=42,
                        help="covariance sampling seed (default: 42)")
    args = parser.parse_args()

    if not args.stage:
        args.stage = ["fns", "ecs", "openmc", "site"]
    if not args.workers:
        import multiprocessing
        args.workers = max(1, (multiprocessing.cpu_count() or 2) - 1)

    plan = stages(args)
    minutes = estimate(args)

    print(f"{len(plan)} stage(s), {args.workers} workers")
    if args.uncertainty:
        print(f"uncertainty on: {args.samples or 'adaptive'} replicas per solve, "
              f"seed {args.seed}")
        if not args.samples:
            print("  no --samples, so each case picks its own replica count and "
                  "the estimate below assumes 100")
    if minutes:
        print(f"rough estimate {minutes / 60:.1f} h of solving, resumable "
              f"throughout\n")
    for name, description, command in plan:
        print(f"  {name:22s} {description}")
        print(f"  {'':22s} {' '.join(command)}")
    print()

    if "openmc" in args.stage and not args.openmc_chain:
        print("openmc stage skipped: no --openmc-chain given\n")

    problems = check_environment(args)
    if problems:
        print("before this will run:")
        for problem in problems:
            print(f"  - {problem}")
        print()
        if not args.plan:
            raise SystemExit(1)

    if args.plan:
        return

    failed = []
    for name, _description, command in plan:
        print(f"\n=== {name} ===", flush=True)
        started = time.time()
        result = subprocess.run(command)
        print(f"=== {name}: exit {result.returncode}, "
              f"{(time.time() - started) / 60:.1f} min ===", flush=True)
        if result.returncode != 0:
            failed.append(name)
            if not args.keep_going:
                raise SystemExit(f"{name} failed; --keep-going to carry on anyway")
    if failed:
        raise SystemExit(f"failed: {' '.join(failed)}")
    print("\nall stages finished")


if __name__ == "__main__":
    main()
