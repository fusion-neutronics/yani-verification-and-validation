#!/usr/bin/env python3
"""Which library agrees best with each measurement, and what explains the rest.

A score on its own says a library is wrong without saying what is wrong with
it, which is the part an evaluator can act on. This joins three things that
each know a piece of the answer:

* the sweep's results, which give every library's agreement with each foil and
  the radionuclides that carried the heat;
* the isomeric completeness survey from the data pipeline, which says whether
  a library lists the metastable final state a heat carrier is produced in at
  all;
* each library's own decay provenance, written by the converter, which says
  whether a heat carrier's mean decay energy is a Q/3 placeholder rather than
  an evaluated scheme, and whether its decay record is internally inconsistent.

The two established cases come out of that join without special-casing. On the
FNS osmium foil the heat after five minutes is Os190m, and TENDL-2017 does not
list the 1706 keV state in `Os190(n,n')`, so no code can make it and the foil
sits at a third of the measurement. On the tin foil the carrier is Sn111, whose
ENDF/B-VIII.1 decay record books a third of its electron-capture Q to the
electrons where the measured value is 0.42 of that, so the heat is high by the
same factor.

## What this deliberately does not do

It does not rank libraries by how many gaps the survey found. Most gaps are
marginal channels or a second route to one isomer, and they weigh the same in a
count as a state carrying a whole disagreement. Only gaps touching a foil's own
heat carriers are reported here, which is the weighting the raw survey cannot
do because it knows nothing about any measurement.

    python attribute.py --results results/                     # every library present
    python attribute.py --results results/ --library jeff-4.0  # one library's story
"""

from __future__ import annotations

import argparse
import json
import pathlib

#: A library counts as beaten on a foil when its mean deviation is worse than
#: the best by more than this, in percentage points. Below it the two agree as
#: well as the measurement can distinguish, and calling either a winner reads
#: more into the benchmark than it holds.
TIE_POINTS = 0.5

#: A foil is reported as poor when every library's deviation exceeds this
#: multiple of the measurement's own median uncertainty.
#:
#: Rank alone hides the case that matters most for improving a library. On the
#: FNS osmium foil TENDL-2017 is the best of the field at 78% mean deviation
#: against a measurement good to a few percent: being least wrong is not being
#: right, and reporting only the shortfall against the best said nothing there.
#: Scaled by the experiment's own uncertainty rather than a fixed percentage,
#: because a foil measured to 30% cannot indict a library at 20%.
POOR_SIGMA_MULTIPLE = 2.0


def load_results(directory):
    """{combination: {experiment: result}} for every sweep file present."""
    out = {}
    for path in sorted(pathlib.Path(directory).glob("*.json")):
        document = json.loads(path.read_text())
        if "results" not in document or "combination" not in document:
            continue
        out[document["combination"]["name"]] = document
    return out


def ranking(results, experiment):
    """Every combination that solved this experiment, best agreement first."""
    scored = []
    for name, document in results.items():
        case = document["results"].get(experiment)
        if case:
            scored.append((case["metrics"]["mean_deviation_percent"], name, case))
    return sorted(scored, key=lambda row: row[0])


def element_of(nuclide):
    """The element symbol in a nuclide name, as a whole symbol.

    `Cs134_m1` is caesium, not carbon. Comparing symbols with `startswith` puts
    every one-letter element in front of every two-letter one that begins with
    the same character, so a gap on a carbon channel matched a caesium carrier,
    a boron gap matched barium and bismuth, and a sulphur gap matched tin,
    strontium and antimony. Taking the leading run of letters and comparing it
    whole removes the collision.
    """
    symbol = ""
    for character in nuclide:
        if not character.isalpha():
            break
        symbol += character
    return symbol


def gaps_for(survey, library, leaders):
    """Survey gaps in `library` whose omitted state could be a heat carrier.

    Matched on the product rather than the channel, since a foil's leaders are
    named nuclides and a gap names the state a reaction leaves behind. A
    leader's name carries its isomeric ordinal (`Os190_m1`) and the survey has
    only an excitation energy, so the join is on the ground-state name and any
    metastable leader of that nuclide counts. Loose in the safe direction: it
    can suggest a gap that did not matter, and cannot hide one that did.
    """
    if not survey:
        return []
    grounds = {name.split("_")[0] for name in leaders if "_m" in name}
    out = []
    for gap in survey.get("gaps", []):
        if library not in gap["omitted_by"]:
            continue
        # "Os190 (n,n')" -> the parent is Os190; the product is what the
        # reaction makes, which the survey does not name, so fall back to
        # whether any metastable leader shares the channel's element.
        parent = gap["channel"].split()[0]
        element = element_of(parent)
        if any(element_of(name) == element for name in grounds):
            out.append(gap)
    return out


def decay_notes(provenance, leaders):
    """What a library's decay provenance says about these heat carriers."""
    if not provenance:
        return {}
    placeholders = set(
        provenance.get("decay_energy_placeholders", {}).get("nuclides", []))
    # A build that filled its placeholders no longer lists them as such, and
    # the fact a reader needs is the same one: this record had no evaluated
    # scheme. So the fill report counts too, and says what the number moved
    # from and to, which is the size of the error the placeholder carried.
    filled = {}
    for row in provenance.get("decay_energy_fill", {}).get("replaced", []):
        filled[row["nuclide"]] = (row["before_eV"], row["after_eV"],
                                  provenance["decay_energy_fill"].get("library", "?"))
    inconsistent = {}
    found = provenance.get("decay_inconsistencies", {})
    for kind, entries in found.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            inconsistent.setdefault(entry.get("nuclide"), []).append(kind)
    notes = {}
    for name in leaders:
        reasons = []
        if name in placeholders:
            reasons.append("mean decay energy is a Q/3 placeholder, not an "
                           "evaluated scheme")
        if name in filled:
            before, after, source = filled[name]
            reasons.append(
                f"mean decay energy was a Q/3 placeholder, replaced from "
                f"{source}: {before / 1e6:.2f} MeV -> {after / 1e6:.2f} MeV "
                f"({after / before:.2f}x)" if before else "placeholder replaced")
        for kind in inconsistent.get(name, []):
            reasons.append(f"decay record inconsistent: {kind}")
        if reasons:
            notes[name] = reasons
    return notes


def report(results, survey, provenances, library):
    """One block per experiment: the ranking, then what explains a shortfall."""
    experiments = sorted({e for d in results.values() for e in d["results"]})
    lines, wins, losses = [], [], []
    for experiment in experiments:
        rows = ranking(results, experiment)
        if len(rows) < 2:
            continue
        best_score, best_name, _ = rows[0]
        lines.append(f"\n{experiment}")
        for score, name, case in rows:
            marker = "  <-- best" if name == best_name else ""
            lines.append(f"  {name:28s} mean |dev| {score:7.2f}%{marker}")

        if library is None:
            continue
        mine = next((row for row in rows if row[1] == library), None)
        if mine is None:
            lines.append(f"  {library} did not solve this experiment")
            continue
        score, _, case = mine
        leaders = case.get("leaders", [])
        sigma = case["metrics"].get("median_measurement_sigma_percent") or 0.0
        # Beyond what the experiment's own scatter can excuse, whatever the
        # rank: a library that leads a field of three where all three are
        # twice the measurement uncertainty out has room to improve, and that
        # is the case an evaluator wants pointed at.
        poor = sigma > 0.0 and score > POOR_SIGMA_MULTIPLE * sigma
        behind = score - best_score > TIE_POINTS
        if not behind:
            wins.append(experiment)
        else:
            losses.append(experiment)
        if not behind and not poor:
            lines.append(f"  {library} is best or level with it. Carriers: {', '.join(leaders)}")
            continue
        if behind:
            lines.append(f"  {library} is behind {best_name} by {score - best_score:.2f} points."
                         f" Carriers: {', '.join(leaders)}")
        else:
            lines.append(f"  {library} leads, and every library is poor here:"
                         f" {score:.1f}% against a measurement good to {sigma:.1f}%."
                         f" Carriers: {', '.join(leaders)}")
        for gap in gaps_for(survey, library, leaders):
            lines.append(f"    missing state: {gap['channel']} at {gap['state_keV']} keV,"
                         f" carried by {', '.join(gap['carried_by'])}")
        for name, reasons in decay_notes(provenances.get(library), leaders).items():
            for reason in reasons:
                lines.append(f"    {name}: {reason}")
    return lines, wins, losses


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=pathlib.Path,
                        default=pathlib.Path(__file__).parent / "results",
                        help="directory of sweep result JSON files")
    parser.add_argument("--survey", type=pathlib.Path, default=None,
                        help="isomer_completeness.json from the data pipeline")
    parser.add_argument("--library", default=None,
                        help="the library to explain; omit for the ranking alone")
    parser.add_argument("--decay-provenance", action="append", default=[],
                        metavar="LIBRARY=PATH",
                        help="a library's decay subsection provenance.json, "
                             "which names its placeholder and inconsistent records")
    args = parser.parse_args()

    results = load_results(args.results)
    if not results:
        raise SystemExit(f"no sweep results under {args.results}. Run sweep.py first.")

    survey = json.loads(args.survey.read_text()) if args.survey else None
    provenances = {}
    for item in args.decay_provenance:
        if "=" not in item:
            parser.error(f"--decay-provenance wants LIBRARY=PATH, got {item!r}")
        name, path = item.split("=", 1)
        provenances[name] = json.loads(pathlib.Path(path).read_text())

    if args.library and args.library not in results:
        parser.error(f"no results for {args.library}; have {sorted(results)}")

    lines, wins, losses = report(results, survey, provenances, args.library)
    print(f"{len(results)} libraries: {', '.join(sorted(results))}")
    if not survey:
        print("no --survey given, so a missing final state cannot be reported")
    if args.library and not provenances.get(args.library):
        print(f"no --decay-provenance for {args.library}, so a placeholder "
              f"mean energy cannot be reported")
    print("\n".join(lines))
    if args.library:
        print(f"\n{args.library}: best or level on {len(wins)}, behind on {len(losses)}")
        print(f"tie threshold {TIE_POINTS} percentage points; a foil is called poor"
              f" above {POOR_SIGMA_MULTIPLE} times its own measurement uncertainty")


if __name__ == "__main__":
    main()
