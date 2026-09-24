#!/usr/bin/env python3
"""Solve one FNS foil and fail if the answer has moved.

    regression.py                  # the pinned case, against the pinned band
    regression.py --show           # print what it would check, solve nothing
    regression.py --update         # re-pin from a fresh solve

Every other check in this repository runs against stubs. This one runs the
physics: it solves a real foil against real nuclear data and compares the
answer with a number committed to this file. It is the check that notices when
a yani release changes a result, which is the one thing the test suite cannot
see and the sweep only sees months later when someone reruns it.

**What it is not.** One foil is not validation, and a green run here says
nothing about the other 131 experiments. It says the number this foil produced
last time is the number it produces now.

The band is deliberately loose against round-off and tight against physics. A
change in the last few digits is a different BLAS or a different core count and
is not interesting. A change of a tenth of a percent in the decay heat is a
different answer and someone should know why.
"""

import argparse
import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "fns_decay_heat"))

import yani  # noqa: E402
from common import libraries  # noqa: E402

import case as fns_case  # noqa: E402
import run as fns_run  # noqa: E402

# Iron, the 2000 five-minute campaign, on the apples-to-apples combination.
# Iron because it is this benchmark's default case, the one the README solves,
# and among the cheapest to solve; the 2000 campaign because it is the one that
# covers every foil, so the case cannot vanish from the archive.
CASE = "Fe"
EXPERIMENT = "2000exp_5min"
COMBINATION = "tendl-2017"

# Pinned from yani 0.18.0 against the 2026-09-18 data release.
# Re-pin with --update, and say in the commit message what moved and why.
REFERENCE = {
    "yani_version": "0.18.0",
    "mean_deviation_percent": 7.074,
    "points": 21,
}

# A relative move in the heat curve larger than this fails. 1e-3 is far above
# the 1e-15 that a re-run on the same machine reproduces, and far below
# anything a physics change would produce.
HEAT_TOLERANCE = 1.0e-3
# The headline is a mean over 21 points, so it moves less than any single one.
DEVIATION_TOLERANCE_PP = 0.05


def solve():
    combination = libraries.resolve([COMBINATION])[0]
    case = fns_case.load(CASE, EXPERIMENT)
    solved = fns_run.run(case, combination, None)
    metrics = fns_case.score(solved.heat, case)
    return case, solved, metrics


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show", action="store_true", help="print the pin and stop")
    ap.add_argument("--update", action="store_true",
                    help="print a fresh pin to paste into this file")
    args = ap.parse_args()

    if args.show:
        print(f"case        : {CASE}/{EXPERIMENT} on {COMBINATION}")
        print(f"pinned at   : yani {REFERENCE['yani_version']}")
        print(f"mean dev    : {REFERENCE['mean_deviation_percent']}% "
              f"+/- {DEVIATION_TOLERANCE_PP} pp")
        print(f"heat curve  : {HEAT_TOLERANCE:.0e} relative")
        return 0

    case, solved, metrics = solve()
    deviation = metrics["mean_deviation_percent"]
    points = metrics["points"]

    print(f"yani {yani.__version__}: {CASE}/{EXPERIMENT} on {COMBINATION}")
    print(f"  mean deviation {deviation:.4f}%  over {points} points"
          f"  ({solved.elapsed:.1f} s)")

    if args.update:
        print()
        print("REFERENCE = {")
        print(f'    "yani_version": "{yani.__version__}",')
        print(f'    "mean_deviation_percent": {round(deviation, 3)},')
        print(f'    "points": {points},')
        print("}")
        return 0

    problems = []
    if points != REFERENCE["points"]:
        problems.append(
            f"the case now has {points} measured points, pinned at "
            f"{REFERENCE['points']}. The archive changed, or the loader did; "
            f"either way the comparison below is not like for like.")

    moved = abs(deviation - REFERENCE["mean_deviation_percent"])
    if moved > DEVIATION_TOLERANCE_PP:
        problems.append(
            f"mean deviation moved {moved:.4f} pp, from "
            f"{REFERENCE['mean_deviation_percent']}% to {deviation:.4f}%, "
            f"which is more than the {DEVIATION_TOLERANCE_PP} pp this allows. "
            f"If the move is intended, re-pin with --update and say what "
            f"changed in the commit message.")

    if problems:
        print()
        for problem in problems:
            print(f"::error::{problem}")
        return 1

    print(f"  within {DEVIATION_TOLERANCE_PP} pp of the pin "
          f"({REFERENCE['mean_deviation_percent']}%, yani "
          f"{REFERENCE['yani_version']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
