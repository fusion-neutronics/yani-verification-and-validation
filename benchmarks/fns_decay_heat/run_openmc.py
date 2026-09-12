#!/usr/bin/env python3
"""The same FNS experiments, run with OpenMC's depletion module.

    run_openmc.py --chain chain_endfb81_fast.xml               # every foil
    run_openmc.py --chain chain_endfb81_fast.xml --case Fe
    run_openmc.py --list-chains                                # where to get one

This is a third line on the plot, not a rerun of the yani one. OpenMC solves
the same problem -- a known multigroup flux, a known schedule, decay heat
afterwards -- through `openmc.deplete.IndependentOperator`, which is the
transport-free entry point, so no geometry is built and no particles are
tracked here either.

## What OpenMC needs that yani does not

Three things, and each is worth stating because each is a real difference
rather than an inconvenience:

* **A pre-built depletion chain file.** OpenMC does not assemble the network
  from evaluations at run time; it reads an XML chain. The pre-generated chains
  published at [openmc.org/data](https://openmc.org/data) are ENDF/B-VII.1,
  ENDF/B-VIII.0, ENDF/B-VIII.1, JEFF-4.0 and JENDL-5. **There is no TENDL
  chain**, which is why OpenMC cannot appear on this benchmark's
  apples-to-apples line: FISPACT-II's published results are TENDL-2017, and
  OpenMC cannot be pointed at TENDL-2017.

* **A choice between two fixed sets of capture branching ratios.** Every
  pre-generated chain is published in exactly two forms, described on
  openmc.org as having "spectrum-averaged capture branching ratios ... one
  based on a thermal flux spectrum and one based on a fast flux spectrum".
  Neither is a 14 MeV DT spectrum. The ratio is a number baked into the chain
  file, not a function of energy, so the branching a foil gets in this 14 MeV
  field is one somebody else averaged over a different spectrum. `--chain`
  takes whichever file you point it at, and the choice is recorded in the
  output, because on an isomer-dominated foil it is most of the answer.

* **An HDF5 cross-section library**, set through `OPENMC_CROSS_SECTIONS`.

None of this is a criticism of OpenMC, which is a transport code that also
depletes. It is the reason the numbers differ, and a comparison that did not
say so would be worth nothing.

## Normalisation

`IndependentOperator` computes a per-atom reaction rate as

    sum_g sigma_g [b] * flux_g [n-cm/src] * source_rate / (1e24 * V [cm3])

so passing `flux_g = phi_g * V`, with phi_g the benchmark's absolute group flux
in n/cm2/s, and `source_rate = 1.0`, gives `sum_g sigma_g [cm2] * phi_g`, which
is the same one-group rate yani collapses. Cooling steps are `source_rate = 0`.
"""

import argparse
import json
import os
import pathlib
import sys
import tempfile
import time
import traceback

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import case as fns_case  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
BOUNDARIES = HERE / "data" / "ccfe_709_boundaries.json"

# Room temperature, matching the yani runs. The HDF5 libraries carry 294 K as
# 293.6 K, which is the value OpenMC expects to be asked for.
TEMPERATURE = 293.6

CHAIN_SOURCES = """
Pre-generated depletion chains, from https://openmc.org/data

  ENDF/B-VII.1    thermal  https://anl.box.com/shared/static/os1u896bwsbopurpgas72bi6aij2zzdc.xml
                  fast     https://anl.box.com/shared/static/9058zje1gm0ekd93hja542su50pccvj0.xml
  ENDF/B-VIII.0   thermal  https://anl.box.com/shared/static/nyezmyuofd4eqt6wzd626lqth7wvpprr.xml
                  fast     https://anl.box.com/shared/static/x3kp739hr5upmeqpbwx9zk9ep04fnmtg.xml
  ENDF/B-VIII.1   thermal  https://anl.box.com/shared/static/q6ev8pl7xct179ke7kq148smde8gzni6.xml
                  fast     https://anl.box.com/shared/static/n0pkqe66uotskoljr93szvjyvtvycgze.xml
  JEFF-4.0        thermal  https://anl.box.com/shared/static/qpcfyrctoffb34m4dwyxz2vgp8tim8e7.xml
                  fast     https://anl.box.com/shared/static/p6cettxz3ovbp151qg7bc3k9ov0zt3wm.xml
  JENDL-5         thermal  https://anl.box.com/shared/static/zgn4gkwxnl3tyh45vrig429yze24sy9d.xml
                  fast     https://anl.box.com/shared/static/yw4bsaf86d1vhva42wzurwstlp1ynhe5.xml

The fast-spectrum file is the closer of the two to a 14 MeV field, which is not
the same as being right for one. There is no TENDL chain published.

Cross sections: an HDF5 library from the same page, with OPENMC_CROSS_SECTIONS
pointing at its cross_sections.xml.
""".strip()


def group_boundaries():
    if not BOUNDARIES.is_file():
        raise SystemExit(f"no group boundaries at {BOUNDARIES}")
    return json.loads(BOUNDARIES.read_text())["boundaries_eV"]


def run_case(case, chain_file, boundaries):
    """Specific decay heat [uW/g] at each measured time, from OpenMC."""
    import openmc
    import openmc.deplete

    volume = case.mass_g / case.density
    material = openmc.Material(name=f"{case.name} foil")
    for element, fraction in case.composition.items():
        material.add_element(element, fraction, percent_type="wo")
    material.set_density("g/cm3", case.density)
    material.volume = volume
    material.depletable = True

    # phi_g * V, so that source_rate = 1.0 makes the per-atom rate come out as
    # sum_g sigma_g [cm2] * phi_g. See the module docstring.
    flux = np.asarray(case.spectrum, dtype=float) * volume

    micro = openmc.deplete.MicroXS.from_multigroup_flux(
        energies=boundaries,
        multigroup_flux=case.spectrum.tolist(),
        chain_file=chain_file,
        temperature=TEMPERATURE,
    )

    operator = openmc.deplete.IndependentOperator(
        materials=openmc.Materials([material]),
        fluxes=[flux],
        micros=[micro],
        chain_file=chain_file,
        normalization_mode="source-rate",
    )

    # The irradiation pulses first, then one cooling step per measured time, so
    # the results land exactly on the measurement grid, as the yani runs do.
    timesteps = [seconds for seconds, _ in case.irradiation] + case.cooling_steps
    source_rates = [1.0 for _ in case.irradiation] + [0.0 for _ in case.cooling_steps]

    started = time.time()
    # A predictor integrator with beginning-of-step rates, which is the same
    # stepping yani documents, so the comparison is not a comparison of
    # integrators.
    integrator = openmc.deplete.PredictorIntegrator(
        operator, timesteps, source_rates=source_rates, timestep_units="s")

    # `get_decay_heat` reads decay energies from the chain, and it looks for the
    # chain in the global config rather than taking the one the operator was
    # built with. Without this every case integrates successfully and then dies
    # on "A depletion chain file must be specified with
    # openmc.config['chain_file'] in order to load decay data", which is the
    # last statement in the run and so costs the whole solve.
    openmc.config["chain_file"] = str(chain_file)

    # Depletion writes its results to the working directory, so each case gets a
    # scratch one rather than clobbering the last.
    with tempfile.TemporaryDirectory() as scratch:
        previous = pathlib.Path.cwd()
        os.chdir(scratch)
        try:
            integrator.integrate()
            results = openmc.deplete.Results("depletion_results.h5")
            _times, heat = results.get_decay_heat(str(material.id), units="W/g")
        finally:
            os.chdir(previous)
    elapsed = time.time() - started

    # One entry per step plus the initial state, so the measurement starts after
    # the irradiation pulses and the leading entry.
    heat = np.asarray(heat)[1 + len(case.irradiation):] * 1e6
    if heat.size != case.times.size:
        raise ValueError(
            f"{heat.size} decay-heat points against {case.times.size} measured")
    return heat, elapsed


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--chain", type=pathlib.Path,
                        help="OpenMC depletion chain XML")
    parser.add_argument("--chain-name", help="how to label this chain in the "
                                             "output (default: the filename)")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--experiment", action="append", default=[])
    parser.add_argument("--data", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=HERE / "results")
    parser.add_argument("--list-chains", action="store_true")
    args = parser.parse_args()

    if args.list_chains:
        print(CHAIN_SOURCES)
        return
    if args.chain is None or not args.chain.is_file():
        raise SystemExit(
            f"--chain is required and must exist. Run --list-chains for where "
            f"to get one.")
    if "OPENMC_CROSS_SECTIONS" not in os.environ:
        raise SystemExit(
            "OPENMC_CROSS_SECTIONS is not set. OpenMC needs an HDF5 library; "
            "run --list-chains for where to get one.")

    import openmc

    label = args.chain_name or args.chain.stem
    boundaries = group_boundaries()
    selection = [
        (name, experiment) for name, experiment in fns_case.every(args.data)
        if (not args.case or name in args.case)
        and (not args.experiment or experiment in args.experiment)
    ]
    print(f"openmc {openmc.__version__}, chain {label}")
    print(f"cross sections {os.environ['OPENMC_CROSS_SECTIONS']}")
    print(f"{len(selection)} experiments\n")

    results, failures = {}, {}
    started = time.time()
    for index, (name, experiment) in enumerate(selection, start=1):
        key = f"{name}/{experiment}"
        try:
            case = fns_case.load(name, experiment, args.data)
            heat, elapsed = run_case(case, args.chain, boundaries)
            metrics = fns_case.score(heat, case)
            results[key] = {
                "case": name,
                "experiment": experiment,
                "time_unit": case.time_unit,
                "times": case.times.tolist(),
                "measured_uW_per_g": case.measured.tolist(),
                "measured_uncertainty_uW_per_g": case.uncertainty.tolist(),
                "openmc_uW_per_g": heat.tolist(),
                "metrics": metrics,
                "solve_seconds": elapsed,
            }
            print(f"[{index}/{len(selection)}] {key}: "
                  f"{metrics['mean_deviation_percent']:.1f}%")
        except Exception as exc:
            failures[key] = traceback.format_exc()
            print(f"[{index}/{len(selection)}] {key}: FAILED {exc}")

    args.output.mkdir(parents=True, exist_ok=True)
    destination = args.output / f"openmc-{label}.json"
    destination.write_text(json.dumps({
        "benchmark": "fns_decay_heat",
        "code": "openmc",
        "openmc_version": openmc.__version__,
        "chain_file": str(args.chain),
        "chain_label": label,
        "cross_sections": os.environ["OPENMC_CROSS_SECTIONS"],
        "temperature": TEMPERATURE,
        "solved": len(results),
        "failed": len(failures),
        "wall_seconds": time.time() - started,
        "results": results,
        "failures": failures,
    }, indent=1, sort_keys=True))
    print(f"\n{len(results)} solved, {len(failures)} failed -> {destination}")


if __name__ == "__main__":
    main()
