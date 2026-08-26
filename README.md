# YANI verification and validation

This repository hosts simulation results and repository scripts for running YANI and compare the results with open benchmarks

**The site showing the results is at
<https://fusion-neutronics.github.io/yani-verification-and-validation/>.**

[yani]: https://github.com/fusion-neutronics/yani

## The benchmarks

| benchmark | what is measured | cases | another code's results |
| --- | --- | ---: | --- |
| [FNS decay heat](benchmarks/fns_decay_heat) | specific decay heat after a 14 MeV irradiation | 132 | yes, TENDL-2017 |
| [Effective cross sections](benchmarks/effective_cross_sections) | spectrum-averaged cross sections in 23 fields | 365 | yes, TENDL-2017 |

Both are published by the IAEA through [CoNDERC][conderc]. What makes these
archives worth building on is that each one carries three things, not one:

* **The measurement.** Decay heat measured at FNS after a 14 MeV irradiation,
  and effective cross sections measured by foil activation, each with its
  experimental uncertainty. This is the part that makes a run validation rather
  than a code comparison.
* **The conditions needed to reproduce it.** The neutron field as group fluxes,
  and for the decay-heat cases the foil composition and mass and the irradiation
  and cooling schedule. So a case is defined by the archive itself rather than by
  our reading of a paper.
* **Another code's calculated results for the same cases**, produced with
  FISPACT-II. So every plot here shows the measurement, yani, and an independent
  inventory code, and a disagreement can be attributed rather than just noted.

Those published calculations used TENDL-2017, so TENDL-2017 is also the default
library for the yani runs, which keeps the comparison like for like.

[conderc]: https://nds.iaea.org/conderc/

**If you know of an open benchmark that is not here,
[raise an issue](../../issues) and we will add it.**

## Running one

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python benchmarks/fns_decay_heat/run.py --case Fe
python benchmarks/fns_decay_heat/run.py --list
```

## Error bars on the calculated side

yani can propagate nuclear-data uncertainty, so both benchmarks take
`--uncertainty`: the activation cross sections are resampled from their ENDF
MF=33 covariance, folded against the benchmark's own spectrum, and the schedule
re-solved per replica.

```bash
python benchmarks/fns_decay_heat/run.py --case Fe --uncertainty --samples 32
```

It is off by default because it costs one solve per replica rather than one in
total. **Every sigma it reports today is zero**, because the published libraries
do not yet carry a covariance section, and a run says so explicitly rather than
letting a zero read as "well known":

```
covariance:  0 nuclide(s) perturbed, 462 with none published
```

So what is in the repository is the machinery and its coverage report, not yet a
result. [The methodology page](docs/methodology.md) says what it covers, why the
band is an ensemble spread rather than a quadrature sum, and what is still held
at its evaluated value.


## Running all of it

```bash
python tools/run_all.py --plan      # what would run, and roughly how long
python tools/run_all.py             # run it
```

`--plan` prints the exact commands and an estimate, and checks the things worth
knowing before starting rather than three hours in: whether yani is installed,
whether the benchmark data is there, and whether the disk can hold the nuclear
data a full run caches. It runs nothing.

**Every stage resumes.** Sweeps write after each solve, through a temporary file
and a rename, and skip what is already in their output. So Ctrl-C is safe, a run
can be split across days, and re-running after a crash costs only the solve that
was in flight. Nothing needs to be finished in one sitting.

Useful shapes for a long run:

```bash
# just the like-for-like library, all 132 decay-heat experiments
python tools/run_all.py --stage fns --combination tendl-2017

# every combination, but only the campaign that covers all 73 foils
python tools/run_all.py --experiment 2000exp_5min

# a machine with cores to spare
python tools/run_all.py --workers 8

# with nuclear-data error bars; --plan folds the replica count into the estimate
python tools/run_all.py --plan --uncertainty --samples 32

# rebuild the pages from results already on disk, solving nothing
python tools/run_all.py --stage site
```

A solve is single-threaded and takes a couple of minutes, most of it spent
reducing a 2800-nuclide network down to what one foil can reach, so `--workers`
is close to a linear speed-up. It costs about 1.6 GB of memory per worker, which
is what sets the sensible ceiling rather than the core count.

The OpenMC comparison is a stage of its own and stays off unless you point it at
a depletion chain, since it needs an OpenMC install and an HDF5 cross-section
library the rest does not:

```bash
python benchmarks/fns_decay_heat/run_openmc.py --list-chains
python tools/run_all.py --stage openmc --openmc-chain chain_endfb81_fast.xml
```

### Disk

yani caches nuclear data under `~/.cache/yamc`, fetching what a calculation
needs on first use. TENDL-2017 comes to about 13 GB. The ten combinations name
five libraries between them, so a full run is tens of gigabytes in that cache.
`--plan` checks for headroom and says so if there is not any.

## Layout

```
benchmarks/<name>/build_data.py    the published archive -> committed JSON
benchmarks/<name>/data/            that JSON
benchmarks/<name>/run.py           one case
benchmarks/<name>/sweep.py         every case x every data combination
benchmarks/<name>/results/         what the sweeps wrote; the site reads these
benchmarks/common/libraries.py     the nuclear-data combinations, shared
tools/build_site.py                results -> docs pages and figures
```
