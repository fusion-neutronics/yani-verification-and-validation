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
| 250 K  | 83.708% | 0.0030% | 9.180% | 0.0000% |
| 294 K  | 83.707% | reference | 9.180% | reference |
| 600 K  | 83.700% | 0.0166% | 9.180% | 0.0001% |
| 900 K  | 83.715% | **0.4515%** | 9.180% | 0.0001% |
| 1200 K | 83.636% | 0.3806% | 9.180% | 0.0002% |
| 2500 K | 83.649% | 0.2079% | 9.181% | 0.0003% |

## What it says

**Temperature is not what is wrong with these foils.** Tungsten moves by at
most 0.45% across a range from 250 K to 2500 K, and tantalum by 0.0003%, which
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

**The move is not monotonic in temperature, and a pure Doppler effect would
be.** Tungsten reads 0.003%, 0.017%, 0.452%, 0.381%, 0.208% going up the
range, peaking at 900 K rather than at 2500 K. Broadening is monotonic, so
something other than temperature differs between those evaluated files. This
is flagged rather than explained: it is under half a percent and well below
anything that matters to the decay heat, but it is not the shape the mechanism
predicts, and calling it Doppler would be reading a trend that is not there.

## Reproducing it

```bash
python benchmarks/fns_decay_heat/temperature.py --list
python benchmarks/fns_decay_heat/temperature.py
python benchmarks/fns_decay_heat/temperature.py --case W --temperature 294 900
```

Results land in `benchmarks/fns_decay_heat/results/temperature.json` with the
full heat curve at every temperature. A solve is about 9 s, so the whole study
is a couple of minutes.
