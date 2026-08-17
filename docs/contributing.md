# Add a benchmark

**If you know of an open benchmark that is not on this site, please
[raise an issue][issues] and we will add it.**

That is a genuine request rather than a formality. The list here is the list we
have found, not the list that exists, and the gaps are the interesting part: a
benchmark nobody has run yani against is worth more to us than another foil on
one we have.

[issues]: https://github.com/fusion-neutronics/yani-verification-and-validation/issues

## Why everything here is CoNDERC so far

Not a convenience choice. For fusion inventory validation specifically, the
IAEA's [CoNDERC][conderc] collection is very close to the whole of what is
openly redistributable, and the reason is worth knowing before you go looking.

The experimental campaigns that produced this field's validation data were run
at JAEA's FNS and at AWE's ASP. A [2023 review][gilbert] by the author of the
FNS decay-heat benchmark notes in passing that **neither facility is available
any more**. The corpus is closed: no new measurements of this kind are coming,
and what exists is what was published at the time.

Of that, only the FNS decay-heat set was packaged for public redistribution,
which is what CoNDERC hosts. The rest is in the literature rather than in a
repository:

* the ASP gamma-spectroscopy campaigns, published as results rather than data,
* `UKAEA-FUS-390`, described in its own citation as available on request from
  UKAEA,
* the FNG decay-heat experiments at Frascati, distributed through SINBAD, which
  needs registration.

[conderc]: https://nds.iaea.org/conderc/
[gilbert]: https://doi.org/10.1088/2515-7655/acbeaf

So "we have two benchmarks" is not a stopping point we settled for. It is the
count of the ones that meet the standard below. Outside fusion inventory
specifically there is more -- IRDFF-II, EXFOR, and the fission-product
decay-heat measurements -- and those are tracked as issues.

If you know of something in the second category that has since been published
as data, that is exactly the issue worth raising.

## What makes one usable here

Every benchmark on this site is reproducible by anyone from a clean checkout,
and that constraint decides what can go on it:

* **The measurement has to be openly published**, and downloadable without a
  registration wall or a licence agreement. This is the one that rules most
  candidates out. The FNG decay-heat experiments distributed through SINBAD and
  the SFCOMPO spent-fuel assays are both excellent activation and depletion
  benchmarks, and neither can go on a site whose whole claim is that you can
  re-run it.
* **It has to describe an inventory problem**: a known irradiation, in a known
  or published spectrum, with something measured afterwards. Decay heat,
  activity, a gamma spectrum, a dose rate, an isotopic assay, an effective
  cross section. Benchmarks that measure a *transported* quantity -- leakage
  spectra, in-material fluxes, shielding attenuation -- test a transport code,
  not this one.
* **Enough of the input has to be stated** to run it without guessing:
  composition, mass, flux magnitude, spectrum, and the irradiation and cooling
  schedule. A benchmark that omits one of these can still be listed, but the
  missing piece has to be named on the page rather than quietly assumed.

A published set of results from another code, in the same archive, is not
required -- but it is what turns a page from "yani agrees with the measurement"
into a comparison, so it is always worth saying whether one exists.

## What adding one involves

Each benchmark on this site is a directory under `benchmarks/` with the same
three parts, and nothing else:

```
benchmarks/<name>/
    build_data.py    fetches the published archive, distils it to JSON
    data/<name>.json committed, so nobody needs the archive to reproduce a run
    run.py           one case, or all of them, against a named data combination
```

`build_data.py` exists so that the committed JSON is never a file somebody
typed. It is the record of how the numbers were derived from the archive, and
re-running it is the only way to check that record.

The nuclear-data combinations are shared across every benchmark, in
`benchmarks/common/libraries.py`, so `tendl-2017` means the same five settings
on every page.

You do not have to write any of this to suggest a benchmark. An issue with a
link to the data is entirely enough.
