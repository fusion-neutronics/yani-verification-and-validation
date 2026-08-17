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
