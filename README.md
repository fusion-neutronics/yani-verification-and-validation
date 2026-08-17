# yani verification and validation

Every open benchmark we have found that tests a transmutation, activation or
inventory code, run against [yani][yani], with the scripts that produced the
numbers.

**The site is at
<https://fusion-neutronics.github.io/yani-verification-and-validation/>.**

[yani]: https://github.com/fusion-neutronics/yani

## The benchmarks

| benchmark | what is measured | cases | another code's results |
| --- | --- | ---: | --- |
| [FNS decay heat](benchmarks/fns_decay_heat) | specific decay heat after a 14 MeV irradiation | 132 | FISPACT-II, TENDL-2017 |
| [Effective cross sections](benchmarks/effective_cross_sections) | spectrum-averaged cross sections in 23 fields | 365 | FISPACT-II, TENDL-2017 |

Both are published by the IAEA through [CoNDERC][conderc], and both archives
carry FISPACT-II's own calculated results next to the measurements. That is
what makes the comparison a statement about codes rather than about libraries:
FISPACT-II was run with TENDL-2017, so yani is run with TENDL-2017 too, and on
that line the two codes are reading the same evaluations.

Everything else -- other libraries, other combinations of the five nuclear-data
subsections, OpenMC -- answers a different question and is labelled as such.

[conderc]: https://nds.iaea.org/conderc/

**If you know of an open benchmark that is not here,
[raise an issue](../../issues) and we will add it.** The list is the one we have
found, not the one that exists. See [docs/contributing.md](docs/contributing.md)
for what makes a benchmark usable on a site whose whole claim is that you can
re-run it.

## Running one

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python benchmarks/fns_decay_heat/run.py --case Fe
python benchmarks/fns_decay_heat/run.py --list
```

Nothing is fetched from the IAEA to reproduce a run: each benchmark's data is
distilled into a committed JSON by its own `build_data.py`, which is kept as the
record of how that JSON was derived. Nuclear data is downloaded and cached by
yani on first use, and no ENDF processing or NJOY is involved, because every
library these benchmarks use is a keyword yani resolves to converted data.

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
# just the comparison against FISPACT-II, all 132 experiments
python tools/run_all.py --stage fns --combination tendl-2017

# every combination, but only the campaign that covers all 73 foils
python tools/run_all.py --experiment 2000exp_5min

# a machine with cores to spare
python tools/run_all.py --workers 8

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

`tools/build_site.py` imports neither yani nor any nuclear data, so the site
builds in CI from the repository alone and a page can never quietly disagree
with the result file it displays.
