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

## What is not covered

Two gaps, stated here rather than left to be inferred from an absence.

**Fission yields are configured on every run and read by nothing.** None of the
73 FNS foils is fissionable, and no effective cross-section reaction has a
fissionable target, so `transmutation_fission_yields` is set on every
combination and never exercised. Nothing on this site is evidence about it.
Closing that needs a fission benchmark, which is
[issue #2](https://github.com/fusion-neutronics/yani-verification-and-validation/issues/2).

**Not every combination runs on every campaign.** `tendl-2017` and
`tendl-2025` cover all 132 FNS experiments; the other eight combinations cover
only `2000exp_5min`, the campaign that includes all 73 foils. That keeps the
sweep to about half a day and costs nothing on the comparison against
FISPACT-II, which is `tendl-2017` and is complete. What it does cost is the
long-cooling behaviour of the other eight, since `1996exp_7hour` is the only
campaign that follows a foil out to 400 days. Tracked as
[issue #1](https://github.com/fusion-neutronics/yani-verification-and-validation/issues/1).

**No calculated error bar has a non-zero value yet.** The runners propagate
cross-section covariance on request, but the published libraries carry no
covariance section, so every sigma comes back as 0. See
[Uncertainty on the calculated side](#uncertainty-on-the-calculated-side).

**Every benchmark here is 14 MeV.** JAEA-FNS, FNG and TUD are all DT
assemblies, so a cross section that folds correctly against a 14 MeV field and
badly against a fission spectrum is a failure this site cannot currently see.
[Issue #3](https://github.com/fusion-neutronics/yani-verification-and-validation/issues/3)
tracks adding IRDFF-II, whose reference fields include Cf-252 and U-235 fission
spectra.

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

## Uncertainty on the calculated side

Until recently only one side of a C/E here carried an error bar. The
measurements come with theirs, and the calculation was a single number. yani can
now propagate nuclear-data uncertainty, so the runners can put an error bar on
the calculated curve too, with `--uncertainty`:

```bash
python benchmarks/fns_decay_heat/run.py --case Fe --uncertainty --samples 32
python benchmarks/effective_cross_sections/run.py --uncertainty --samples 32
```

What it does is resample the activation cross sections from their ENDF MF=33
covariance, fold each replica against this benchmark's own spectrum, and
re-solve the schedule per replica. The reported sigma is then the spread over
that ensemble.

Two details matter for reading the result:

* **The band is an ensemble spread, not a sum of per-nuclide sigmas.** Decay
  heat is a function of the whole inventory, and a parent and its daughter do
  not move independently, so each replica's inventory is evaluated into a decay
  heat and the spread taken over those. Adding per-nuclide sigmas in quadrature
  would assume away the correlation that the resampling exists to keep.
* **It covers the activation cross sections and nothing else.** Half-lives,
  decay branching ratios, fission yields and the isomeric-branching overlay
  stay at their evaluated values, and every run prints which of those were left
  out rather than implying a total.

With a band on both sides, the agreement test becomes
|C − E| ≤ sqrt(sigmaC² + sigmaE²) rather than |C − E| ≤ sigmaE. Both are
reported per case, because a point can sit outside the measurement uncertainty
and still be consistent once the data it was calculated from is known to be
poorly determined. That is a different statement from a point that misses for
any other reason, and the two should not be scored the same.

### Why the bands on this site are currently zero

The capability is wired through the runners and the figures, but every sigma it
reports today is exactly 0. The published libraries these benchmarks download
do not yet carry a covariance section: yani records that per nuclide, and on
TENDL-2017, the library the FISPACT-II comparison uses, every nuclide fetched so
far is marked as having none.

This is stated here rather than shown as a zero-width band because a zero sigma
is ambiguous, and the two things it can mean are opposite. A well-known cross
section and an evaluation that publishes no covariance at all both report zero.
The runners print the split, so a run says how many nuclides were actually
perturbed and how many had nothing to perturb from:

```
covariance:  0 nuclide(s) perturbed, 462 with none published
```

Nothing on this site is evidence about nuclear-data uncertainty until that
number is non-zero. What lands here is the machinery and the honest report of
its coverage, so that republishing the libraries with their covariance sections
is the only remaining step.

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
