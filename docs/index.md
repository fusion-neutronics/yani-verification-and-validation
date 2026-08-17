# YANI verification and validation

Every open benchmark we have found that tests a transmutation, activation or
inventory code, run against [YANI][yani], with the scripts that produced the
numbers.

[yani]: https://fusion-neutronics.github.io/yani/

## The benchmarks

| benchmark | measures | cases | another code's published results |
| --- | --- | ---: | --- |
| [FNS decay heat](benchmarks/fns-decay-heat.md) | specific decay heat after a 14 MeV irradiation | 132 | FISPACT-II, TENDL-2017 |
| [Effective cross sections](benchmarks/effective-cross-sections.md) | spectrum-averaged cross sections in 23 neutron fields | 365 | FISPACT-II, TENDL-2017 |

Both come from the IAEA [CoNDERC][conderc] collection, and both archives carry
FISPACT-II's own calculated results next to the measurements. That is rarer
than it sounds, and it is what lets these pages compare two codes rather than
two libraries: FISPACT-II was run with TENDL-2017, so YANI is run with
TENDL-2017 too, and on that line the two are reading the same evaluations.

[conderc]: https://nds.iaea.org/conderc/

## What a comparison here is, and is not

**The apples-to-apples line is a verification result.** Two independently
written codes, given identical evaluations, should land on the same answer. When
they do, that is evidence both implementations are right. A large "win" on
identical data would be evidence that one of them is wrong, and it should be
read that way rather than celebrated.

**The other lines are a different question.** FISPACT-II's published results
exist for TENDL-2017 and nothing else. YANI can be pointed at TENDL-2025,
JEFF-4.0, ENDF/B-VIII.1 or a mixture assembled subsection by subsection, and
where one of those tracks the measurement better, that is a statement about
data rather than about code. Both are worth knowing; they are not the same
claim, and every page keeps them apart.

**Where a deviation is shared, it belongs to neither code.** Several foils are
tens or hundreds of percent from the measurement in *both* codes at once. That
is the evaluation, not the solver, and no amount of work on either code will
move it.

## Reproducing any of it

```bash
git clone https://github.com/fusion-neutronics/yani-verification-and-validation
cd yani-verification-and-validation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python benchmarks/fns_decay_heat/run.py --case Fe
```

Benchmark data is committed, so nothing is fetched from the IAEA to reproduce a
run, and no ENDF processing or NJOY is involved: every library these pages use
is a keyword YANI resolves to already-converted data.

For the whole thing rather than one foil, `python tools/run_all.py --plan` says
what would run and roughly how long it would take before running any of it.
[How the comparisons are made](methodology.md) covers what varies between
runs, what is held fixed, and what these benchmarks do not cover.

## Something missing?

**If you know of an open benchmark that is not here,
[raise an issue][issues] and we will add it.** The list is the one we have
found, not the one that exists. [Add a benchmark](contributing.md) says what
makes one usable on a site whose whole claim is that you can re-run it.

[issues]: https://github.com/fusion-neutronics/yani-verification-and-validation/issues
