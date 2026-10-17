# Group structure on the FNS foils

yani takes whatever ascending list of energy boundaries a spectrum happens to
use, of whatever length. Named structures are a convenience and never a
requirement, and nothing in the solver prefers one. This measures what that
freedom is worth: the same physical field, expressed on ten different
structures, run through the same foil.

The FNS archive publishes its spectra on CCFE-709, so that row is the input as
given and every other row is a rebin of it, conserving flux per unit lethargy
within each source group. Total flux is conserved exactly and asserted, so a
row that drifts is a physics result rather than a bookkeeping one.

## The result

Tungsten, the largest relative change in its decay-heat curve against the
native CCFE-709 row:

| structure | groups | move vs CCFE-709 |
| --- | ---: | ---: |
| XMAS-172 | 172 | 12.84% |
| VITAMIN-J-175 | 175 | 0.97% |
| SCALE-252 | 252 | 7.11% |
| TRIPOLI-315 | 315 | 1.62% |
| **SHEM-361** | 361 | **43.63%** |
| LLNL-616 | 616 | 1.02% |
| CCFE-709 | 709 | reference |
| SCALE-999 | 999 | 0.46% |
| **UKAEA-1102** | 1102 | **0.00%** |
| ECCO-1968 | 1968 | 0.16% |

Across five foils, the worst move on a structure finer than the native one and
on a structure coarser than it:

| foil | finer, worst | coarser, worst |
| --- | ---: | ---: |
| Au | 1.56% | 521.82% |
| W  | 0.46% | 43.63% |
| Nb | 0.29% | 20.91% |
| Ta | 0.23% | 10.68% |
| Fe | 0.14% | 6.40% |

## What it says

**Going finer costs nothing, which is the check that the rebin is sound.**
SCALE-999, UKAEA-1102 and ECCO-1968 all land within half a percent of the
native row on tungsten, and within 1.6% on the worst of the five foils. They
should: rebinning onto a finer structure cannot recover detail the 709-group
file never carried, so agreement is the expected answer and a disagreement
would have meant the rebin was lossy where it should not be.

**Going coarser costs a great deal, and unevenly.** Gold moves by a factor of
six on the worst coarse structure. Iron moves by 6%. Which foil suffers depends
on where its cross section has structure, and a coarse group smears that
structure across a bin before the fold ever sees it.

**Group count does not determine adequacy. Where the groups are does.** This is
the result worth carrying away. SHEM-361 has more than twice the groups of
XMAS-172 and is nearly four times worse on this problem: 43.6% against 12.8%.
SHEM is a thermal-reactor structure, with its resolution concentrated in the
thermal and resonance region and comparatively little above 1 MeV. That is
exactly the wrong place for a 14 MeV field, where the activation runs through
threshold reactions at the top of the range. VITAMIN-J-175, with only three more
groups than XMAS-172, is thirteen times better than it for the same reason in
reverse.

So "how many groups" is the wrong question to ask of a structure, and a table
of group counts is not a ranking. The right question is whether the structure
resolves the part of the spectrum that drives the reactions being counted, and
that depends on the problem rather than on the structure.

**None of this is a reason to use a coarse structure at all.** yani folds
against the pointwise cross section, so the group structure is a property of
the spectrum you hand it and not of the library. If the spectrum comes from a
transport run on 709 groups, hand over 709 groups. The rows above say what
would have been lost had it arrived coarser, which is a question about the
upstream calculation rather than about this one.

## Reproducing it

```bash
python benchmarks/fns_decay_heat/group_structure.py --list
python benchmarks/fns_decay_heat/group_structure.py
python benchmarks/fns_decay_heat/group_structure.py --case W --structure UKAEA-1102 SHEM-361
```

Results land in `benchmarks/fns_decay_heat/results/group_structure.json`, with
the full heat curve on every structure and the flux the rebin found outside
each destination's range. The rebin itself is covered by `tests/test_rebin.py`:
flux conservation, an identity rebin returning its input, a group straddling an
edge splitting by lethargy, and out-of-range flux being reported rather than
folded into the end groups.
