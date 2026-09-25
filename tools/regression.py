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

# A relative move in any point of the heat curve larger than this fails. 1e-3
# is far above the 1e-15 a re-run on the same machine reproduces, and far below
# anything a physics change would produce.
#
# The curve is checked as well as the headline because the headline is a mean
# over 21 points and a mean can sit still while the shape moves: a change that
# lifts the early points and drops the late ones by the same amount leaves it
# untouched. The curve is what the benchmark is actually about.
HEAT_TOLERANCE = 1.0e-3
# The headline is that mean, so it moves less than any single point.
DEVIATION_TOLERANCE_PP = 0.05

# Specific decay heat [uW/g] at each of the 21 measured times, from the same
# run as the pin above. Re-pin both together with --update.
REFERENCE_HEAT = [
    0.12351116013478924, 0.12070657844333908, 0.11820308380132237,
    0.11582158315988021, 0.11383266459037365, 0.11085960105249021,
    0.10754285039342014, 0.10494153749296158, 0.10208967230040944,
    0.09950274148272847, 0.09760655559338206, 0.09559930560586313,
    0.09370031209738286, 0.09215528154226274, 0.09017130604136775,
    0.08785855172145929, 0.08578405937104219, 0.08389213598498454,
    0.08089813393683153, 0.07705811299173046, 0.07353765914811973,
]


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
        print(f"heat curve  : {len(REFERENCE_HEAT)} points, "
              f"{HEAT_TOLERANCE:.0e} relative each")
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
        print()
        print("REFERENCE_HEAT = [")
        for value in solved.heat:
            print(f"    {float(value)!r},")
        print("]")
        return 0

    problems = []
    if points != REFERENCE["points"]:
        problems.append(
            f"the case now has {points} measured points, pinned at "
            f"{REFERENCE['points']}. The archive changed, or the loader did; "
            f"either way the comparison below is not like for like.")

    if len(solved.heat) != len(REFERENCE_HEAT):
        problems.append(
            f"the curve now has {len(solved.heat)} points, pinned at "
            f"{len(REFERENCE_HEAT)}.")
    else:
        worst, worst_at = 0.0, -1
        for i, (now, then) in enumerate(zip(solved.heat, REFERENCE_HEAT)):
            rel = abs(now - then) / abs(then) if then else 0.0
            if rel > worst:
                worst, worst_at = rel, i
        print(f"  heat curve worst point moved {worst:.2e} relative")
        if worst > HEAT_TOLERANCE:
            problems.append(
                f"the heat curve moved {worst:.3e} relative at point "
                f"{worst_at}, which is more than the {HEAT_TOLERANCE:.0e} this "
                f"allows. The mean deviation can sit still while the shape "
                f"moves, so this is the check that caught it.")

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
