# Self-shielding on the FNS foils

Every other page on this site runs its foils **dilute**, which is what
`transmute()` does when a material carries no geometry. Inside a real foil the
flux is depressed wherever the total cross section is large, so a dilute run
reads high on anything with strong resonances, and the C/E on those pages is
carrying that error along with everything else.

This page measures how much that matters.

!!! warning "This is a sensitivity study, not a validation"

    The FNS archive publishes each foil's mass and density but **not its
    dimensions**, so the chord length the correction needs is not in the data.
    Nothing here can be scored against the measurement, because the geometry
    going in is assumed rather than recorded.

    What it can say is how far the answer moves when the geometry is varied
    over the range a 1 g activation foil plausibly spans, which separates the
    foils whose dilute C/E can be read as-is from the foils whose dilute C/E is
    partly a geometry error.

## The result

Eight foils, dilute and then at 100 µm and 1000 µm, on TENDL-2017 with
`decay_2012`. Six are resonance absorbers; Al and Ti are controls chosen
because they should not move at all.

| foil | strongest `would_shield` | dilute mean dev | move at 100 µm | move at 1000 µm | mean dev at 1000 µm |
| --- | --- | ---: | ---: | ---: | ---: |
| W  | W180 0.962  | 83.7% | 10.52% | **12.04%** | 78.7% |
| Nb | Nb93 0.784  | 8.7%  | 1.13%  | **4.42%**  | 10.4% |
| Au | Au197 0.818 | 29.7% | 0.85%  | 0.91%  | 28.6% |
| Co | Co59 0.857  | 10.2% | 0.81%  | 0.81%  | 9.6%  |
| Ta | Ta181 0.581 | 9.2%  | 0.07%  | 0.12%  | 9.3%  |
| In | In113 0.832 | 3863% | 0.15%  | 0.15%  | 3858% |
| Al | none 0.000  | 7.2%  | 0.00%  | 0.03%  | 7.2%  |
| Ti | none 0.000  | 3.2%  | 0.00%  | 0.00%  | 3.2%  |

## What it says

**Only two foils move by more than their measurement uncertainty.** Tungsten at
12.0% and niobium at 4.4%. For the other four absorbers the correction is under
1% even at a millimetre, which is thicker than any of these foils can be. So on
this benchmark, in this field, self-shielding is not what separates yani from
the measurement, and the dilute rows on the other pages can be read as they
stand for everything except W and Nb.

**The controls do not move, at all.** Al and Ti come back at 0.00% and 0.03%,
which is the check that the correction is not reaching into groups where there
is no resonance structure to find. A correction that moved them would be
over-shielding, and there would be no way to tell from a foil that is supposed
to move.

**`would_shield` picks the right nuclides and does not rank them.** This is the
useful part. The screen is what a dilute run reports about the correction it
skipped, and its ordering is W (0.962), Co (0.857), In (0.832), Au (0.818),
Nb (0.784), Ta (0.581). The actual ordering of the effect is W (12.0%),
Nb (4.4%), Au (0.9%), Co (0.8%), In (0.15%), Ta (0.12%). Indium is flagged
third hardest and moves less than every other absorber but tantalum.

That is exactly what yani's own documentation says the number is: *"a screen
rather than a bound, since it carries no geometry, so it says which answers to
distrust rather than by how much"*. This page is the measurement behind that
sentence. A zero means no resonance absorber was left uncorrected and is worth
trusting; a large value means look closer, and nothing more.

The reason the two orderings differ is the field. `would_shield` is a property
of a nuclide's own resonances. Whether those resonances matter to *this answer*
depends on how much flux sits on them and how much of the decay heat comes
through them, and in a 14 MeV field most of the activation runs through
threshold reactions well above the resonance region.

**Shielding does not simply improve agreement.** It moves W from 83.7% to 78.7%
and Au from 29.7% to 28.6%, and moves Nb the other way, from 8.7% to 10.4%.
With the geometry assumed rather than known, none of those is evidence about
the correction. They are the reason the assumed geometry cannot be tuned until
the agreement looks best, and this page does not.

## Cost

A shielded solve costs more than a dilute one. The slowing-down solve runs per
nuclide per group, and it needs a wider slice of nuclear data than an
activation-only run, since it wants total and elastic cross sections as well.
Under yani 0.18.0 it ran over the whole reachable network, a few thousand
nuclides, and took 807 s against 15 s for the same foil dilute on a cold cache.
yani 0.21.0 loads cross sections only for the products a solve populates
(fusion-neutronics/core#342), so it shields 11 to 38 nuclides on these foils,
and in the run behind this page a shielded solve took 2 to 10 s against 2 to
4 s dilute.

The default of two thicknesses rather than a fine sweep dates from that
earlier cost.

## Reproducing it

```bash
python benchmarks/fns_decay_heat/self_shielding.py --list
python benchmarks/fns_decay_heat/self_shielding.py
python benchmarks/fns_decay_heat/self_shielding.py --case W --thickness 10 100 1000
```

Results land in `benchmarks/fns_decay_heat/results/self_shielding.json`, with
the full heat curve for every foil and thickness, the `would_shield` report
from the dilute run, and the chord and strongest shielding factor the shielded
runs actually used.
