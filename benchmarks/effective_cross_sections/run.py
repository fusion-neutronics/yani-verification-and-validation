#!/usr/bin/env python3
"""Effective cross sections from yani, against the CoNDERC measurements.

    run.py                                   # every reaction, apples-to-apples data
    run.py --spectrum JAEA-FNS-pos3
    run.py --reaction "Fe-56(n,p)Mn-56"
    run.py --combination tendl-2025
    run.py --uncertainty                     # with a nuclear-data error bar

## What is being computed

A measured effective cross section comes from irradiating a foil in a known
field and counting the product afterwards: it is the production rate of one
nuclide, per target atom, per unit total flux. So that is what is extracted
here, rather than an integral done separately in numpy:

    a pure target nuclide is irradiated for one short pulse of the measured
    spectrum, and the product atoms that appear are divided by the target atoms
    and by the fluence.

Everything on the path from the evaluation file to the number -- reading the
pointwise cross section, folding it against this spectrum, and, where the
product is metastable, splitting the rate between the ground and isomeric
states by an energy-dependent branching ratio -- is yani's own. Doing the
collapse integral here in Python instead would test the data and skip the code.

## Why the pulse is short and the flux is large

Neither is physical, and neither needs to be: an effective cross section does
not depend on the flux magnitude, so the two are chosen for arithmetic rather
than for realism.

* **Short** (1e-4 s) so that no product decays away appreciably during the
  pulse, and so that the target is not measurably depleted. Both effects are
  then far below the 5%-ish uncertainty on the measurements.
* **Large** (1e21 n/cm2/s) so that the product-to-target atom ratio lands
  around 1e-8 rather than around 1e-18, where double precision has no
  significant figures left to give.

`--check-linearity` re-runs each reaction at a tenth of the fluence and reports
the largest change, which is how the choice above is kept honest rather than
merely asserted.

## The error bar

`--uncertainty` resamples the activation cross sections from their ENDF MF=33
covariance and re-solves each pulse per replica, so the reported sigma is the
spread of the effective cross section itself. This benchmark is where that
number is easiest to read: an effective cross section is one fold of one
evaluated cross section against one spectrum, so its sigma is close to a direct
statement about how well that evaluation is known in this field, with none of
the chain effects that a decay-heat curve mixes in.
"""

import argparse
import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import yani  # noqa: E402
from common import libraries, uncertainty as unc  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "data" / "rr_data.json"

# See the module docstring: chosen for numerical headroom, not for realism.
PULSE_SECONDS = 1e-4
PULSE_FLUX = 1e21
BARN = 1e-24

# A stand-in density and volume. Every quantity used is a ratio of atom
# densities within one material, so neither affects the answer.
DENSITY = 1.0
VOLUME = 1.0
TEMPERATURE = 294.0


def load(path=None):
    path = pathlib.Path(path) if path else DEFAULT_DATA
    if not path.is_file():
        raise SystemExit(f"no benchmark data at {path}. Run build_data.py first.")
    return json.loads(path.read_text())


def source_for(spectrum):
    """A yani source carrying this field's shape, on its own boundaries.

    The spectra arrive on whatever structure the code that generated them used,
    175 groups for most and 211 for one, and neither is a named structure. That
    is not a problem to work around: yani takes the boundaries themselves.
    """
    return yani.NeutronSource(
        energy=yani.sources.Histogram(spectrum["boundaries_eV"],
                                      spectrum["flux_n_per_cm2_s"])
    )


# The two JAEA-FNS fields in the effective-cross-section archive are the same
# physical fields as positions 3 and 7 of the decay-heat archive: the 175-group
# spectra here and the 709-group spectra there integrate to the same total
# (1.1168e10 and 1.0509e10 n/cm2/s). What differs is the resolution they are
# published at.
FNS_POSITION = {"JAEA-FNS-pos3": "3", "JAEA-FNS-pos7": "7"}


def fns_709_source(name, fns_data_path=None):
    """The same field as `name`, on CCFE-709 instead of 175 groups.

    This exists because the comparison is otherwise not like for like. The
    FISPACT-II column published in the reaction table was produced by
    collapsing the `tal2017-n/gxs-709` library against the CCFE-709 form of
    these fields, the same collapse the decay-heat decks use; matching 119
    JAEA-FNS-pos3 rows against FISPACT's own printed 709-group collapse agrees
    to better than 1% on 115 of them. Folding yani against the 175-group form
    therefore compares two different integrals and calls the difference a code
    difference.

    Measured rather than predicted, over the 184 JAEA-FNS reactions: the swap is
    a no-op on 177 of them, and every one of the 9 rows that moves by more than
    0.5% is radiative capture (MT=102). The largest shift on any non-capture row
    anywhere is 0.366%, so the threshold reactions are not the sensitive ones.
    Capture moves by +0.46% to +19.45%, which is the 1/v tail being averaged
    over groups too coarse to resolve it.

    Every one of those 9 rows lands on the published FISPACT-II value once the
    group structure matches: Dy-164(n,g)Dy-165 goes from C/E 4.486 to 5.343
    against FISPACT's 5.340, Lu-175(n,g)Lu-176m from 1.283 to 1.330 against
    1.330, Rh-103(n,g)Rh-104 from 2.398 to 2.447 against 2.450. That is the
    evidence that the group structure was the asymmetry.

    It is worth being clear about what this does not do. Agreement with the
    measurement gets worse, not better: over the JAEA capture rows the median
    |C/E - 1| goes from 35.4% to 39.1%. Both codes are simply far from those
    measurements, and this run makes yani wrong in the same way FISPACT is
    rather than less wrong. The comparison is what becomes honest, not the
    physics.

    Returns None for a field that has no CCFE-709 counterpart, which is every
    field except the two JAEA-FNS ones; those keep their published boundaries.
    """
    position = FNS_POSITION.get(name)
    if position is None:
        return None
    path = pathlib.Path(fns_data_path) if fns_data_path else (
        HERE.parent / "fns_decay_heat" / "data" / "fns_data.json")
    if not path.is_file():
        raise SystemExit(
            f"--group-structure ccfe-709 needs the decay-heat benchmark data at "
            f"{path}, which holds these fields on CCFE-709. Run "
            f"benchmarks/fns_decay_heat/build_data.py.")
    flux = json.loads(path.read_text())["spectra_by_position"][position]
    return yani.NeutronSource(energy=yani.sources.Histogram("CCFE-709", flux))


def _extract(atoms, target, products, fluence):
    """One inventory -> one effective cross section [barns]."""
    target_atoms = atoms.get(target)
    if not target_atoms:
        raise ValueError(f"no {target} left in the inventory, which cannot be right")
    produced = sum(atoms.get(product, 0.0) for product in products)
    return produced / target_atoms / fluence / BARN


def effective_cross_section(target, products, source, seconds=PULSE_SECONDS,
                            flux=PULSE_FLUX, uncertainty=None):
    """Spectrum-averaged cross section [barns] for making `products` from `target`.

    Returns `(value, sigma)`, where sigma is None unless `uncertainty` is a
    `yani.DataUncertainty`. The value is the total over the listed products,
    which is what the measurement covers: a bare product name in the benchmark
    means the sum over the ground and isomeric states, and a named state means
    just that one.

    The sigma is the spread of the ratio over the ensemble, taken by extracting
    a cross section from each replica's whole inventory rather than by
    combining a sigma on the product with a sigma on the target. Both come out
    of the same perturbed solve and move together.
    """
    material = yani.Material(
        composition={target: 1.0},
        fraction_type="atom",
        density=DENSITY,
        volume=VOLUME,
        temperature=TEMPERATURE,
        name=target,
    )
    schedule = yani.PulseSchedule(
        [yani.Pulse(duration=(seconds, "s"), rate=flux, source=source)])
    results = material.transmute(schedule, data_uncertainty=uncertainty)

    material_id = material.id or 0
    final = results.get_final_material(material_id)
    fluence = flux * seconds
    value = _extract(final.get_atoms_per_barn_cm(), target, products, fluence)

    if uncertainty is None:
        return value, None, None

    # One pulse, so the final state is step 1; step 0 is the unirradiated input.
    inventories = results.get_uncertainty_inventories(
        material_id=material_id, step=results.num_steps)
    if not inventories or len(inventories) < 2:
        return value, None, results.data_uncertainty_info
    spread = np.array(
        [_extract(inventory, target, products, fluence)
         for inventory in inventories], dtype=float)
    return value, float(spread.std(ddof=1)), results.data_uncertainty_info


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--combination", default=libraries.APPLES_TO_APPLES_ECS)
    parser.add_argument("--spectrum", action="append", default=[])
    parser.add_argument("--reaction", action="append", default=[])
    parser.add_argument("--data", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=HERE / "results")
    parser.add_argument("--check-linearity", action="store_true",
                        help="re-run at a tenth of the fluence and report the drift")
    parser.add_argument("--redo", action="store_true",
                        help="re-solve reactions already in the output file")
    parser.add_argument("--uncertainty", action="store_true",
                        help="propagate cross-section covariance onto each value")
    parser.add_argument("--samples", type=int,
                        help="fixed replica count (default: until the sigmas settle)")
    parser.add_argument("--seed", type=int, default=42,
                        help="covariance sampling seed (default: 42)")
    parser.add_argument("--group-structure", choices=["published", "ccfe-709"],
                        default="published",
                        help="which form of the field to fold against. "
                             "'published' uses the 175-group spectra shipped "
                             "with the reaction table; 'ccfe-709' substitutes "
                             "the CCFE-709 form of the two JAEA-FNS fields, "
                             "which is what FISPACT-II's published column was "
                             "collapsed on and so is the like-for-like choice "
                             "for those 184 reactions")
    args = parser.parse_args()

    combination = libraries.resolve([args.combination])[0]
    document = load(args.data)
    rows = [row for row in document["reactions"]
            if (not args.spectrum or row["spectrum"] in args.spectrum)
            and (not args.reaction or row["reaction"] in args.reaction)]
    if not rows:
        raise SystemExit("no reactions matched --spectrum/--reaction")

    args.output.mkdir(parents=True, exist_ok=True)
    # A different group structure is a different run, not a resumable
    # continuation of the published-structure one, so it gets its own file.
    suffix = "" if args.group_structure == "published" else "+ccfe-709"
    destination = args.output / f"{combination.name}{suffix}.json"

    # A full run is 365 solves and takes hours, so it resumes rather than
    # starting over, the same way the decay-heat sweep does.
    results, failures = [], {}
    if destination.is_file() and not args.redo:
        try:
            previous = json.loads(destination.read_text())
            results = previous.get("results", [])
            failures = previous.get("failures", {})
        except json.JSONDecodeError:
            pass
    done = {(row["reaction"], row["spectrum"]) for row in results}

    libraries.apply(combination, yani)
    uncertainty = None
    if args.uncertainty:
        uncertainty = yani.DataUncertainty(seed=args.seed, samples=args.samples)
    print(f"combination: {combination.name} (xs {combination.cross_sections}, "
          f"branching {combination.branching})", flush=True)
    if uncertainty is not None:
        print(f"uncertainty: cross-section covariance, seed {args.seed}, "
              f"{args.samples or 'adaptive'} replicas", flush=True)
    print(f"{len(rows)} reactions across "
          f"{len({row['spectrum'] for row in rows})} spectra"
          + (f", {len(done)} already done" if done else ""), flush=True)

    # One source per field, built once: the rows are grouped by spectrum so that
    # a field's collapse is not rebuilt for each of its reactions.
    sources = {}
    drift = 0.0
    started = time.time()

    def save():
        # Written aside and moved, so a run killed mid-write leaves a whole file
        # rather than a truncated one.
        scratch = destination.with_suffix(".json.part")
        scratch.write_text(json.dumps({
            "benchmark": "effective_cross_sections",
            "combination": libraries.as_dict(combination),
            "yani_version": getattr(yani, "__version__", "unknown"),
            # Which form of each field was folded against. Recorded because it
            # decides whether the FISPACT column beside these numbers is a
            # like-for-like comparison or a different integral.
            "group_structure": args.group_structure,
            "pulse_seconds": PULSE_SECONDS,
            "pulse_flux": PULSE_FLUX,
            "uncertainty": ({"seed": args.seed, "samples": args.samples}
                            if uncertainty is not None else None),
            "wall_seconds": time.time() - started,
            "results": results,
            "failures": failures,
        }, indent=1, sort_keys=True))
        scratch.replace(destination)

    todo = [row for row in sorted(rows, key=lambda r: r["spectrum"])
            if (row["reaction"], row["spectrum"]) not in done]

    for index, row in enumerate(todo, start=1):
        name = row["spectrum"]
        if name not in sources:
            substitute = (fns_709_source(name)
                          if args.group_structure == "ccfe-709" else None)
            sources[name] = substitute or source_for(document["spectra"][name])
            if substitute is not None:
                print(f"  {name}: folding against CCFE-709 rather than the "
                      f"published 175 groups", flush=True)
        try:
            calculated, sigma, info = effective_cross_section(
                row["target"], row["products"], sources[name],
                uncertainty=uncertainty)
            if args.check_linearity:
                tenth, _, _ = effective_cross_section(
                    row["target"], row["products"], sources[name],
                    flux=PULSE_FLUX / 10.0)
                if calculated > 0:
                    drift = max(drift, abs(tenth / calculated - 1.0))
        except Exception as exc:
            failures[row["reaction"] + " @ " + name] = str(exc)
            print(f"[{index}/{len(todo)}] {row['reaction']:26s} {name:16s} "
                  f"FAILED: {exc}", flush=True)
            save()
            continue

        ratio = calculated / row["measured_barns"] if row["measured_barns"] else None
        entry = {**row, "yani_barns": calculated, "yani_ce": ratio}
        if uncertainty is not None:
            entry["yani_sigma_barns"] = sigma
            # Kept as a fraction as well, because that is what a reader compares
            # against the measurement's own quoted percentage.
            entry["yani_sigma_percent"] = (
                sigma / calculated * 100.0
                if sigma is not None and calculated > 0 else None)
            # Recorded even when no sigma came out, because "no covariance
            # published" is the answer to why there is no band and has to
            # survive into the result file to be readable there.
            entry["data_uncertainty_info"] = unc.summarise(info)
        results.append(entry)
        fispact = (f"  FISPACT C/E {row['fispact_ce']:5.2f}"
                   if row["fispact_ce"] is not None else "")
        band = (f" +/- {entry['yani_sigma_percent']:4.1f}%"
                if entry.get("yani_sigma_percent") is not None else "")
        print(f"[{index}/{len(todo)}] {row['reaction']:26s} {name:16s} "
              f"yani {calculated:9.3e} b{band}  "
              f"measured {row['measured_barns']:9.3e} b  "
              f"C/E {ratio:5.2f}{fispact}", flush=True)
        save()

    save()
    elapsed = time.time() - started
    # `is not None` and not truthiness: a C/E of exactly 0.0 is a result, and
    # dropping it hides the failures that matter most. Every one of the 24
    # zeros on endf-b8.1 is an isomeric-state measurement the library has no
    # branching route to, which is precisely what this benchmark exists to
    # test.
    scored = [row for row in results if row["yani_ce"] is not None]
    produced_nothing = [row for row in scored if row["yani_ce"] == 0.0]
    yani_ce = np.array([row["yani_ce"] for row in scored])
    paired = [row for row in scored if row["fispact_ce"] is not None]
    fispact_ce = np.array([row["fispact_ce"] for row in paired])

    print(f"\n{len(results)} reactions in {elapsed / 60:.1f} min, "
          f"{len(failures)} failed")
    if produced_nothing:
        print(f"{len(produced_nothing)} reaction(s) produced none of the named "
              f"product, so their C/E is exactly zero. They are scored, not "
              f"dropped: a library with no route to the product is a gap worth "
              f"seeing.")
        for row in produced_nothing[:10]:
            print(f"  {row['reaction']:26s} {row['spectrum']:16s} "
                  f"products {row['products']}")
    print(f"yani     median C/E {np.median(yani_ce):.3f}, "
          f"within 10%: {int(np.sum(np.abs(yani_ce - 1) <= 0.1))}/{len(yani_ce)}, "
          f"within 20%: {int(np.sum(np.abs(yani_ce - 1) <= 0.2))}/{len(yani_ce)}")
    if len(paired):
        pair_yani = np.array([row["yani_ce"] for row in paired])
        print(f"FISPACT  median C/E {np.median(fispact_ce):.3f}, "
              f"within 10%: {int(np.sum(np.abs(fispact_ce - 1) <= 0.1))}/{len(fispact_ce)}, "
              f"within 20%: {int(np.sum(np.abs(fispact_ce - 1) <= 0.2))}/{len(fispact_ce)}"
              f"   (on the {len(paired)} reactions both calculated)")
        print(f"yani     on the same {len(paired)}: "
              f"median C/E {np.median(pair_yani):.3f}, "
              f"within 10%: {int(np.sum(np.abs(pair_yani - 1) <= 0.1))}/{len(pair_yani)}, "
              f"within 20%: {int(np.sum(np.abs(pair_yani - 1) <= 0.2))}/{len(pair_yani)}")
    if uncertainty is not None:
        banded = [row for row in results if row.get("yani_sigma_percent")]
        print(f"\nuncertainty: {len(banded)}/{len(results)} reactions came back "
              f"with a non-zero band")
        # Taken from the last reaction solved: the coverage report is per
        # target, and printing 365 of them would bury the one line that
        # matters, which is whether anything was perturbed at all.
        last = next((row["data_uncertainty_info"] for row in reversed(results)
                     if row.get("data_uncertainty_info")), None)
        for line in unc.describe(last):
            print(f"  {line}")
        if not banded:
            print("  every band is zero: the libraries these runs download "
                  "carry no covariance section yet")
    if args.check_linearity:
        print(f"linearity: largest change at a tenth of the fluence {drift * 100:.4f}%")

    print(f"\nwrote {destination}")


if __name__ == "__main__":
    main()
