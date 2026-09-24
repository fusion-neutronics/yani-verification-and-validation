# Fission decay heat

A fissile sample is irradiated, the irradiation stops, and the decay power of
the fission products is measured as it falls. The benchmark reports that power
per fission, which makes the answer independent of how large the sample was and
how hard it was driven.

**This is the only benchmark on this site that exercises the fission-yield
path.** The foils in the other two carry no fissile material at all, so their
yield settings are configured on every run and read by nothing.

It is also the only one here that is not a 14 MeV field.

!!! note "No second code to compare against"

    The archive carries FISPACT-II and ORIGEN *input decks* and 13 source
    papers, but no calculated curves. So unlike the other two benchmarks, this
    page is yani against a measurement, not yani against another code.

## The result

Thirteen irradiations across **six fissioning systems**, thermal and fast,
burst and finite, on TENDL-2017 cross sections with ENDF/B-VIII.1 yields and
decay data.

**Burst irradiations**, published as t·f(t):

| system | author | median C/E | mean deviation | within measurement sigma |
| --- | --- | ---: | ---: | ---: |
| U235 thermal | Dickens | 0.992 | 2.4% | 21/32 |
| U233 fast | Akiyama | 0.973 | 2.9% | 32/34 |
| Pu239 fast | Akiyama | 0.970 | 3.7% | 19/34 |
| U235 fast | Akiyama | 0.969 | 3.1% | 24/34 |
| Pu239 thermal | Tobias | 0.956 | 5.6% | 6/31 |
| U235 thermal | Tobias | 0.952 | 5.4% | 5/31 |
| Pu241 thermal | Dickens | 0.950 | 4.5% | 11/31 |
| U238 fast | Akiyama | 0.944 | 5.4% | 22/34 |

**Finite irradiations**, published per unit fission rate:

| system | author | irradiation | median C/E | mean deviation | within sigma |
| --- | --- | ---: | ---: | ---: | ---: |
| U235 thermal | Lott | 5000 s | 0.987 | 1.9% | 14/15 |
| U235 thermal | Lott | 1000 s | 0.978 | 2.6% | 11/13 |
| U235 thermal | Lott | 100 s | 0.965 | 4.2% | 7/11 |
| U233 thermal | Yarnell | 20000 s | 0.946 | 4.7% | 21/43 |
| Pu239 thermal | Yarnell | 20000 s | 0.930 | 8.1% | 4/50 |

**Every one of the thirteen runs low**, between 0.930 and 0.992. One direction
across six fissioning systems, two neutron fields, both irradiation shapes and
five independent experimenters. A single measurement leaning one way is noise;
thirteen leaning the same way is not, and it points at the yields or the decay
data rather than at any experiment. It is the most interesting number on this
page.

The Lott series is worth a second look on its own: 0.965 at 100 s, 0.978 at
1000 s, 0.987 at 5000 s, with the agreement improving as the irradiation
lengthens. A short irradiation weights the short-lived products hardest, so a
trend in that direction is a statement about where in the yield set the
disagreement sits.

## The archive uses two conventions and labels both MeV/f/s

**A burst is published as t·f(t)**, in MeV per fission. f falls roughly as
t^-1.2 over many decades, and multiplying by t turns that into a nearly flat
curve with readable structure. Measured rather than assumed, on U235 thermal
over 2.7 s to 12000 s:

| comparison | median | spread |
| --- | ---: | ---: |
| measured / calculated | 102 | 4393x |
| measured / (calculated × t) | 0.9944 | 1.13x |

**A finite irradiation is published per unit fission rate**, which is f
integrated over the irradiation window. This benchmark normalises by the total
number of fissions instead, so the two differ by exactly the irradiation
length.

That is a determination and not a fit. The ratio comes out at the irradiation
length across four durations spanning 200x, on three fissioning systems,
without that number being fitted to anything:

| dataset | irradiation | measured/calculated ÷ D | spread |
| --- | ---: | ---: | ---: |
| Lott | 100 s | 1.019 | 1.15x |
| Lott | 1000 s | 1.005 | 1.05x |
| Lott | 5000 s | 1.006 | 1.06x |
| U233 Yarnell | 20000 s | 1.044 | 1.07x |
| Pu239 Yarnell | 20000 s | 1.082 | 1.07x |

A spurious fit does not reproduce a number that varies by 200x across the set.

## Only the fission products are counted

What the benchmark measures is fission-product decay heat, not everything an
irradiated sample makes. The archive's own FISPACT decks say so by suppressing
the parent's capture route (`OVER U235 / ACROSS U236 0.0`).

Below a fission threshold that stops being a refinement and becomes the whole
answer. At the archive's 400 keV fast field, U238 captures **405 times** more
than it fissions and Th232 **15749 times**, so an unfiltered inventory is
mostly U239 and Np239 and has almost nothing to do with fission. Dividing that
heat by a near-zero fission count produces a number with no meaning.

So the score counts nuclides with A below 200, which separates fission
products (A roughly 70 to 160) from the actinide chain (above 220) with a wide
margin. The effect, as median C/E and spread across the curve:

| case | everything | fission products only |
| --- | --- | --- |
| U235 thermal, Dickens | 1.0056, 1.13x | 1.0056, 1.13x |
| U233 fast, Akiyama | 1.0177, 2.95x | 0.9913, 1.09x |
| Pu239 fast, Akiyama | 1.3195, 23.48x | 0.9922, 1.07x |
| U238 fast, Akiyama | 27.5626, 38.16x | 0.9615, 1.12x |

The first row is the control and it does not move at all, because for U235
thermal the actinide chain carries nothing measurable. That is why this went
unnoticed while only thermal cases were looked at, and it is why the filter
can be applied to every case rather than only to the ones that need it.

The unfiltered total is kept in the results file beside the scored one, so the
size of the difference is visible per curve rather than taken on trust.

## One file contradicts itself

 `U235_thermal/Yarnell_20000.csv` declares
`Author: Akiyama` and `Irradiation: Pulse` in its header, against a filename
saying Yarnell and 20000 s. It is the only one of the 48 where the header and
the filename disagree, so this is an isolated error in the archive rather than
a pattern, but it means the header cannot be trusted without the filename
beside it.

## How a curve is calculated

yani returns decay heat in watts, and the benchmark wants MeV per fission per
second, so the number of fissions has to come from somewhere.

It comes from the run. `get_reaction_rates()` reports a fission channel as an
edge whose target is `None`, because fission names no single product and its
products arrive from the yields instead. That rate is per parent atom per
second, so

```
fissions = fission_rate [1/s] × parent_atoms × irradiation_seconds
```

Taking it from the solve is the point. Computing it outside from a cross
section and a flux would be a second, independent calculation of the same
quantity, and the two disagreeing would look like a wrong answer rather than
like a failure.

**The flux is set from a fluence, not fixed.** The per-fission normalisation
assumes the sample consumes a negligible part of itself. A fixed flux does not
hold that across the range of irradiations in the archive: at the 1e22 the
archive's own decks use for a microsecond burst, a 20000 s irradiation reaches
**1.2e5 fissions per atom** and the sample is long gone. Holding the fluence
constant instead gives 5.9e-6 fissions per atom at every duration, and leaves a
burst running at exactly the 1e22 it would otherwise have used.
`burnup_fissions_per_atom` is recorded per curve so this is checkable.

## What is not here yet

The archive holds 48 curves and this page stands behind 13. The rest are
excluded for stated reasons rather than quietly dropped, and
`run.py --list` prints them:

- **Baumung 200 s**, a finite irradiation published in the *burst* convention
  instead, fitting t·f(t) at 1.054 with 1.09x spread against 248x for the
  finite one. One dataset disagreeing with the other six is a question for its
  source paper, not a reason to switch convention per curve.
- **Jurney 20000 s**, which follows the finite convention in shape, 1.37x
  spread, but sits 42% low. That is a disagreement about the physics or the
  data rather than about units, and pulling it in would hide it.
- **Curves with no total column.** Th232 fast and several others publish beta
  or gamma but not their sum, so the current scoring has nothing to compare
  against. Scoring the components separately would bring them in.

## Reproducing it

```bash
python benchmarks/fission_decay_heat/build_data.py   # downloads fission.zip, 28 MB
python benchmarks/fission_decay_heat/run.py --list
python benchmarks/fission_decay_heat/run.py --all
python benchmarks/fission_decay_heat/run.py --all --unvalidated   # the rest, to work on
```

Results land in `benchmarks/fission_decay_heat/results/fission-decay-heat.json`
with the full curve, the fission rate and burnup each solve drove, and both
f(t) and t·f(t).
