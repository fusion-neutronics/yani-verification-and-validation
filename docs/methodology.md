# How the comparisons are made

Every number on this site comes from a script in this repository, run against a
benchmark archive published by somebody else. This page says what is being
compared, against what, and what a given figure is and is not evidence for.

## The apples-to-apples rule

A code comparison and a library comparison are different experiments, and
running them together produces a number that means neither.

The CoNDERC archives make it possible to keep them apart, because they publish
**FISPACT-II's own results next to the measurements**, and they say which
library those results were produced with: TENDL-2017. The FNS input decks are
literally named `TENDL-2017_2000exp_5min.i`.

So the default combination everywhere on this site is **TENDL-2017**, and on
that line yani and FISPACT-II are reading the same evaluations, with the same
cross sections, the same reaction topology and the same isomeric branching. A
difference between them is a difference between two codes.

Every other combination on a page is a second question -- *given a free choice
of data, how close can this get?* -- and is labelled as such. Those lines are
not comparisons with FISPACT.

## What varies, and what does not

yani sources five things independently, so "which library" is five choices
rather than one:

| setting | supplies |
| --- | --- |
| `cross_section_data` | continuous-energy cross sections for the rate collapse |
| `transmutation_reactions` | which reaction on which nuclide gives which product |
| `transmutation_branch_ratios` | which product is left in a metastable state |
| `transmutation_decay_data` | half-lives, decay modes, mean decay energies |
| `transmutation_fission_yields` | fission product yields |

A combination on this site names all five, and the runners write all five on
every run. A setting left at whatever the previous run put there is how a sweep
silently reports the wrong provenance.

TENDL publishes no decay sublibrary, so a TENDL combination always borrows
decay data from ENDF/B-VIII.1 or JEFF-4.0. That is not a workaround; it is the
most of a library swap TENDL can express, and it has a consequence worth
stating outright:

> Decay heat at time *t* is a sum over products of *N(t) × λ × Q*. The library
> under test sets *N*, how much of each product got made. The decay library sets
> *λ* and *Q*. **A C/E on the decay-heat benchmark is therefore a statement
> about production rates, measured against fixed decay data.**

Which is why the sweep includes combinations that move only the decay data:
they separate how much of a deviation belongs to the decay library rather than
to the neutron one.

## What each benchmark actually tests

These are the accuracy claims yani makes in [its own
documentation](https://fusion-neutronics.github.io/yani/why_yani/), each paired
with the benchmark on this site that puts a number on it.

**Continuous-energy cross sections, not a multigroup collapse.**

> A multigroup library has already averaged the cross section over each group
> using someone else's assumed spectrum shape, and resonance structure inside a
> group is gone before you ever see it. YANI folds your actual spectrum against
> the pointwise cross section directly, at the energy resolution the evaluation
> was measured at, so the only averaging is the one your own spectrum implies.

Tested by [effective cross sections](benchmarks/effective-cross-sections.md),
which is exactly this operation and nothing else: 365 measured
spectrum-averaged cross sections, each one a single fold of a cross section
against a published field.

**Isomeric branching is tracked, not folded into the ground state, and it is
flux-weighted rather than a fixed number.**

> The branching fraction itself is stored as a curve against incident energy,
> not a single evaluation-average ratio, and is folded against your actual
> spectrum at rate-compute time, so two calculations with different spectra but
> the same target nuclide can legitimately get different branching fractions,
> because they should.

Tested twice. 89 of the effective cross sections measure an isomeric state
directly, so the branching fraction is the answer rather than a correction to
it. And on [FNS decay heat](benchmarks/fns-decay-heat.md) the foils whose heat
runs through a metastable product -- niobium through `Nb94_m1`, tungsten
through `W185_m1`, silver through `Ag110_m1` -- are the ones where a code that
lumps isomers into the ground state cannot get the right answer at all.

**The chain that gets built is exactly the one your material can reach.**

> Rather than truncating the transmutation network at a fixed number of
> reaction or decay steps, a value that silently drops real nuclides if set too
> low and loads data no calculation needs if set too high, YANI computes a
> provable upper bound on the density every candidate nuclide could reach.

Not directly measured by any benchmark here, and it should not be claimed as
though it were. What the benchmarks show is the absence of its failure mode: a
truncated chain shows up as heat that is systematically low at long cooling
times, and the 7.6-hour FNS campaign, which follows foils out to 400 days, is
where that would appear.

## Scoring

The headline number for a decay-heat curve is the **mean deviation**, the
average of |C/E − 1| over the measured points.

It is preferred to a median C/E because a curve that runs high early and low
late can hold a median C/E of 1.000 while matching nothing, and because the
quantity worth judging is agreement rather than bias. Both are reported, along
with the measurement's own uncertainty, because a deviation smaller than the
measurement's scatter is not a result.

For effective cross sections the score is C/E per reaction, and the summary is
the fraction of reactions inside 10% and inside 20%, which is how the source
publication reports its own.

## Reproducing any of it

Every page names the exact command that produced its numbers. From a clean
checkout:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python benchmarks/fns_decay_heat/run.py --case Fe
```

The benchmark data is committed, so nothing is fetched from the IAEA to
reproduce a run. Nuclear data is downloaded and cached by yani on first use.

Versions are recorded in every result file the runners write, and printed on
each benchmark page, because a C/E without a version is not reproducible.
