# Temperature on the FNS foils

Doppler broadening widens and flattens a resonance without changing the area
under it, so a spectrum-averaged reaction rate moves with temperature wherever
resonance structure sits under flux. How far it moves is a property of the
evaluation and of the spectrum, and not something that can be read off the
material.

yani takes the temperature from the `Material` and reads the evaluation at that
temperature. TENDL-2017 carries 250, 294, 600, 900, 1200 and 2500 K, so those
are the rows.

!!! warning "This is a sensitivity study, not a validation"

    The FNS foils were irradiated at room temperature. **The 294 K row is the
    one with a measurement behind it**, and the rest say what the same foil
    would have done hotter. Nothing here is scored against a hot measurement,
    because there is not one.

    The question it answers is the one a fusion component asks, where tungsten
    sits at several hundred degrees rather than at 294 K, and where an
    activation library is usually read at room temperature anyway because that
    is the only temperature a multigroup activation library ships.

## The result

Tungsten and tantalum, every temperature the evaluations carry, on TENDL-2017
with `decay_2012`. Move is the largest relative change in the decay-heat curve
against the 294 K row.

| temperature | W mean dev | W move | Ta mean dev | Ta move |
| ---: | ---: | ---: | ---: | ---: |
| 250 K  | 83.657% | 0.0030% | 9.180% | 0.0000% |
| 294 K  | 83.656% | reference | 9.180% | reference |
| 600 K  | 83.649% | 0.0166% | 9.180% | 0.0001% |
| 900 K  | 83.642% | 0.0332% | 9.180% | 0.0001% |
| 1200 K | 83.637% | 0.0456% | 9.180% | 0.0002% |
| 2500 K | 83.620% | **0.0881%** | 9.180% | 0.0003% |

## What it says

**Temperature is not what is wrong with these foils.** Tungsten moves by at
most 0.09% across a range from 250 K to 2500 K, and tantalum by 0.0003%, which
is round-off. Tungsten's 83.7% disagreement with the measurement is the same
83.7% at every temperature, so whatever is behind it, Doppler broadening is
not.

That is the field rather than the physics. In a 14 MeV field almost no flux
sits in the resonance region, so widening those resonances moves almost no
reaction rate. The same study in a thermal or epithermal field would not be
expected to come out this flat, and this result should not be carried there.

**600 C, which a first wall runs near, is 873 K.** That falls between the 600 K
and 900 K the evaluations carry. Both are reported rather than interpolated,
because the library is what it is and an interpolated row would look like
evidence it is not.

**The move rises with temperature, as broadening does.** Tungsten reads
0.003%, 0.017%, 0.033%, 0.046%, 0.088% going up the range, carried by W187
from capture on W186.

Under yani 0.18.0 it did not: 0.003%, 0.017%, 0.452%, 0.381%, 0.208%, peaking
at 900 K, which this page flagged as not the shape Doppler broadening predicts.
It was not Doppler. The peaks were W183m, a 5 s isomer, at the last measured
times, where the 0.18.0 solver read it off the stable W183 bulk as a residue
that changed from one temperature to the next. yani 0.19.0 solves the decay
block by block (fusion-neutronics/core#212), and on the same data W183m drops
to a hundredth of that residue there, leaving W187 as what moves.

## Reproducing it

```bash
python benchmarks/fns_decay_heat/temperature.py --list
python benchmarks/fns_decay_heat/temperature.py
python benchmarks/fns_decay_heat/temperature.py --case W --temperature 294 900
```

Results land in `benchmarks/fns_decay_heat/results/temperature.json` with the
full heat curve at every temperature. A solve is about 9 s, so the whole study
is a couple of minutes.
