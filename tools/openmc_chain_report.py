#!/usr/bin/env python3
"""What an OpenMC depletion chain can and cannot represent.

    python tools/openmc_chain_report.py chain_endfb81_fast.xml

Reads a chain XML and reports how isomeric production is handled in it, then
checks that against the reactions the effective cross-section benchmark
actually measures. Needs nothing but the standard library and the chain file:
no OpenMC install, no nuclear data.

This exists so that a statement on the site about OpenMC's isomeric branching is
something a reader can re-derive from the same file rather than something they
have to take on trust. It is a report on a data file, and it says nothing about
the OpenMC code, which reads whatever chain it is given.

## What it is looking for

A depletion chain names, for each parent, which reactions it undergoes and what
each produces. Where a reaction can leave the product in a metastable state, the
chain has to say so by listing the isomer as a separate target with a
`branching_ratio`. Two things follow that are worth measuring:

* **Which reaction types ever do that.** openmc.org describes its pre-generated
  chains as carrying "spectrum-averaged capture branching ratios", and the
  report shows whether that is literally true -- whether capture is the only
  reaction that can reach an isomer.
* **Whether the ratio is a number or a function.** It is an XML attribute, so
  it is a number: one value, averaged over whichever spectrum the chain was
  generated for, applied whatever spectrum the calculation actually uses.
"""

import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RR_DATA = ROOT / "benchmarks" / "effective_cross_sections" / "data" / "rr_data.json"

NUCLIDE = re.compile(r'<nuclide name="([^"]+)"')
REACTION = re.compile(r'<reaction\s+type="([^"]+)"[^>]*?target="([^"]+)"[^>]*?>')
REACTION_WITH_RATIO = re.compile(
    r'<reaction\s+type="([^"]+)"[^>]*?target="([^"]+)"[^>]*?branching_ratio="([^"]+)"')
METASTABLE = re.compile(r"_m\d+$")


def report(chain_path):
    text = chain_path.read_text(encoding="utf-8", errors="replace")

    nuclides = set(NUCLIDE.findall(text))
    reactions = REACTION.findall(text)
    with_ratio = REACTION_WITH_RATIO.findall(text)

    isomeric_targets = [(kind, target) for kind, target in reactions
                        if METASTABLE.search(target)]
    by_kind = collections.Counter(kind for kind, _ in isomeric_targets)
    reachable = {target for _, target in isomeric_targets}

    metastable_nuclides = {name for name in nuclides if METASTABLE.search(name)}
    unreachable = sorted(metastable_nuclides - reachable)

    print(f"{chain_path.name}")
    print(f"  {len(nuclides)} nuclides, {len(reactions)} reactions")
    print(f"  {len(metastable_nuclides)} metastable nuclides in the chain")
    print()
    print(f"  reaction types that can produce a metastable state:")
    if by_kind:
        for kind, count in by_kind.most_common():
            print(f"    {kind:12s} {count:4d}")
    else:
        print("    none")
    print()
    print(f"  {len(with_ratio)} reactions carry a branching_ratio, and every one "
          f"of them is a fixed number in the file rather than a function of "
          f"incident energy.")
    print(f"  {len(reachable)} metastable states are reachable by any reaction.")
    print(f"  {len(unreachable)} metastable nuclides are in the chain but no "
          f"reaction produces them.")
    if unreachable:
        print(f"    e.g. {' '.join(unreachable[:12])}")
    return by_kind, reachable


def against_benchmark(by_kind, reachable):
    """How many of the benchmark's isomeric measurements this chain can express."""
    if not RR_DATA.is_file():
        print(f"\n  (no {RR_DATA}, skipping the benchmark cross-check)")
        return

    document = json.loads(RR_DATA.read_text())
    isomeric = [row for row in document["reactions"]
                if row["product_state"] in ("m", "n")]
    if not isomeric:
        return

    # The benchmark names the channel the way FISPACT does; the chain names it
    # the way ENDF does. Only the mapping for channels that appear in the
    # benchmark is needed.
    channel_names = {
        "g": "(n,gamma)", "2n": "(n,2n)", "3n": "(n,3n)", "p": "(n,p)",
        "d": "(n,d)", "t": "(n,t)", "a": "(n,a)", "np": "(n,np)",
        "na": "(n,na)", "pa": "(n,pa)", "n": "(n,n')",
    }
    representable, missing = [], []
    for row in isomeric:
        product = row["products"][0]
        kind = channel_names.get(row["channel"], row["channel"])
        if product in reachable and by_kind.get(kind):
            representable.append(row)
        else:
            missing.append((row, kind, product))

    print()
    print(f"  against the {len(isomeric)} isomeric measurements in the effective "
          f"cross-section benchmark:")
    print(f"    {len(representable)} could be produced by this chain")
    print(f"    {len(missing)} could not, and would come out as exactly zero")
    channels = collections.Counter(kind for _, kind, _ in missing)
    for kind, count in channels.most_common():
        print(f"      {kind:12s} {count:3d}")
    if missing:
        print("    examples:")
        for row, kind, product in missing[:6]:
            print(f"      {row['reaction']:26s} needs {kind} -> {product}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("chain", type=pathlib.Path,
                        help="an OpenMC depletion chain XML")
    args = parser.parse_args()
    if not args.chain.is_file():
        raise SystemExit(f"{args.chain} is not a file. "
                         f"benchmarks/fns_decay_heat/run_openmc.py --list-chains "
                         f"says where to get one.")
    by_kind, reachable = report(args.chain)
    against_benchmark(by_kind, reachable)


if __name__ == "__main__":
    main()
