# A systematic isotopic activation campaign

**Proposal.** Irradiate **separated isotopes**, not natural elements. Use **well
characterised** neutron fields, not merely intense ones. Measure **individual
activation products including isomeric states**, not a bulk integral. Cover the
**whole periodic table** in priority order.

These are not independent improvements to trade off. Each removes a degeneracy
the others cannot, and an experiment missing any one of them cannot determine the
quantity it is trying to measure.

---

## 1. An elemental measurement cannot determine a cross section

This is a statement about rank, not precision. No amount of beam time fixes it.

Irradiating a natural element and counting one activation product measures

> **N**<sub>p</sub> = **T** · **Σ**<sub>i</sub> *a*<sub>i</sub> **Σ**<sub>c</sub> ∫ σ<sub>i,c→p</sub>(E) φ(E) dE

with *a*<sub>i</sub> the natural abundance of stable isotope *i* and *c* running
over every channel from isotope *i* to the same product *p*. The experiment gives
**one number**; the quantity wanted is the set of individual
σ<sub>i,c→p</sub>. The system is underdetermined.

**Measuring the same element again does not help.** Each irradiation adds a row to
a design matrix whose entries are *a*<sub>i</sub> × (energy weighting under that
field). A different field changes the energy factor. It does not change
*a*<sub>i</sub>. The abundance vector is fixed by nature and identical in every
natural sample in the universe, so in the isotopic direction every row is
proportional to the same vector and that direction is never resolved.

**Enrichment is the only operation that changes *a*<sub>i</sub>.** It is therefore
not one option among several for improving these measurements. It is the only way
to make the isotopic direction observable at all.

**The consequence is compensating errors.** Two confounded channels can both be
badly wrong in opposite directions and still reproduce every integral measurement
ever made, because the errors cancel in the particular weighted sum nature's
abundances happen to form. This is the expected outcome of tuning evaluations
against elemental integral data, since that is the only quantity the tuning could
see. The cancellation holds only while the weighting holds. Change the spectrum,
the temperature or the position in a reactor and it fails. **A library validated
this way is accurate where it was tested and has unknown error everywhere else.**

The damage is worst when the confounded channels have **opposite energy
dependence**, because then the compensation is most spectrum-dependent. The
canonical case is **(n,γ)** on one isotope competing with **(n,2n)** on another
feeding the same product: capture falls steeply with energy, (n,2n) is zero below
an 8 to 10 MeV threshold. Tungsten is exactly this, with W-185m fed by
W-184(n,γ) at 30.6% abundance and W-186(n,2n) at 28.4%. Neither path dominates,
so neither can be treated as a correction to the other.

How widespread, across all naturally occurring elements:

| stable isotopes | elements | consequence |
|---|--:|---|
| 1 | 21 | a natural sample is already an isotopic sample |
| 2 | 23 | one enrichment separates everything |
| 3 to 4 | 13 | tractable |
| 5 to 7 | 23 | most transition metals and rare earths |
| 8 or more | 4 | Cd, Sn, Te, Xe |

For the **63 elements with more than one stable isotope there is no natural
sample that isolates a single cross section.**

---

## 2. A well characterised source beats an intense one

A measurement gives a response

> *R* = ∫ σ(E) φ(E) dE

To get σ the flux must be divided out, so the result inherits the uncertainty on
the **shape** of φ, not just its magnitude. A magnitude error is benign: one
number, common to every reaction, calibrated out with a monitor foil. A shape
error weights different parts of σ(E) differently, affects every reaction
differently, and nothing in the measurement reveals it.

**The inversion is worst conditioned when σ(E) is small where φ(E) is large.** The
response is then dominated by a sliver of the spectrum carrying little flux and
most of the uncertainty.

**Capture at a DT source is exactly that.** Capture cross sections are millibarns
at 14 MeV and barns at 100 keV. A DT source in a room gives a sharp 14 MeV peak
carrying most of the flux plus a scattered and room-return continuum carrying a
few percent. The capture **rate** is dominated by that few percent. So a capture
measurement at a DT source is largely **not a measurement of the capture cross
section**, but of the low-energy tail of the room, folded through an assumed cross
section. Brightness does not change this.

Existing integral data shows the signature. Same libraries, same samples, same
facility; the only difference is which part of the spectrum each reaction
integrates over:

| reaction class | n | median C/E | within ±25% |
|---|--:|--:|--:|
| inelastic to isomer (n,n') | 4 | 1.806 | 25% |
| capture (n,γ) | 16 | 1.234 | 44% |
| **all threshold reactions** | **164** | **1.052** | **74%** |

With a monoenergetic field, φ(E) = Φ δ(E − E₀) and the response collapses to

> *R* = σ(E₀) · Φ

No integral to invert, no shape to know. Fluence at a metrology laboratory is
traceable at the 1 to 3% level, better than the quoted uncertainty on essentially
all existing integral activation data. Systematic errors stop hiding, because
there is no assumed spectrum shape to be wrong about.

**Most importantly the result is σ(E), not one integral of σ(E).** An evaluator
cannot determine the shape of an excitation function from a single integral
response; six energies determine it. Integral measurements **test** an
evaluation, differential measurements **make** one.

**Intensity is the cheap axis.** Monoenergetic fields are far less intense, but
counting statistics fall as 1/√t and can be bought with beam time, while spectrum
shape uncertainty does not fall with time at all. Running a poorly characterised
source longer improves a term that is not the limiting one. Intensity is still
needed for very small cross sections and very short half-lives, which is why a DT
field stays in the programme, but it should be chosen for measurements that need
it rather than used by default.

---

## 3. Isomeric states must be resolved

The **isomeric branching ratio** is a separate evaluated quantity from the cross
section, stored differently and subject to independent error. A bulk measurement
that sums over states determines nothing about the split. Yet for shutdown dose
rate the split is often the whole answer, because the metastable state is
frequently far longer lived and dominates at exactly the cooling times when
people need access.

| isomer | half-life | ground state |
|---|---|---|
| Ag-108m | 438 y | 2.4 min |
| Ho-166m | 1200 y | 26.8 h |
| Ta-180m | > 10<sup>15</sup> y | 8.2 h |
| Nb-94m | 6.3 min | 2.0 × 10<sup>4</sup> y |

A factor of 10<sup>8</sup> in half-life means a branching ratio propagates into a
dose rate almost undamped. Existing data confirms this is the weak spot:
isomer-resolved measurements sit at **64% within ±25%** against **74%** for
totals over the same reactions, and the worst class in the dataset is inelastic
scattering to an isomer, which is a pure branching measurement.

Resolving the states is easy with the right observable, counting both by their
distinct gamma lines, and impossible with a bulk integral.

---

## 4. What to measure, and in what

**Time-resolved HPGe gamma spectrometry**, giving each product nuclide separately
against cooling time. Against bulk calorimetry it wins four ways:

- **It attributes by construction.** One Ni-58 sample gives Co-58m, Co-58g, Co-57
  and Ni-57 as separate numbers, each constraining one cross section. A bulk
  number that disagrees says nothing about which of dozens of channels was wrong.
- **It is immune to impurities.** In the previous campaign N-16 from sample oxygen
  was a top-three heat contributor in 23 of 73 samples and the largest in 10,
  because its 6.1 MeV beta and 6.13 MeV gamma dominate the early points. Those
  samples scored 20.9% median deviation against 11.2% for the rest. A gamma
  spectrum resolves the 6.13 MeV line and discards it; a calorimeter cannot.
- **It works at the sample sizes enrichment provides.** Separated isotopes come in
  milligram to gram quantities. Calorimetry at milligram scale is very hard,
  gamma spectrometry is routine. **The enriched-target choice and the observable
  choice have the same answer.**
- **It produces what is wanted.** The decay photon source term against energy and
  cooling time is the direct input to a dose rate calculation. Decay heat is a
  scalar projection of the same inventory.

**Fields, in priority order.** (1) **Monoenergetic** at a metrology laboratory,
roughly 0.5, 1.2, 2.5, 5.0, 14.8, 17.9 MeV from T(p,n), D(d,n), T(d,n), where
excitation functions are measured rather than tested. (2) **14 MeV DT**, for
intensity and as an integral check on functions already measured differentially.
(3) **Cf-252**, a standardised broad spectrum covering between the monoenergetic
points. (4) **A thermalised reactor position**, for capture measured where
capture dominates in a spectrum that is genuinely known.

---

## 5. The whole periodic table, in priority order

The most complete existing decay-heat campaign covered **69 of the 84 elements
with stable isotopes**, all natural, one facility, one field, one observable. The
15 never covered are **H, He, Li, Be, B, C, N, O, Ne, Ar, Kr, Xe, Th, Pa, U**:
very nearly the complete set of **light elements and gases**. That includes
**lithium and beryllium**, the breeder and the multiplier, and **carbon, nitrogen
and oxygen**, constituents of every steel, ceramic, coolant and atmosphere in a
plant. C-14 from N-14(n,p) is a principal waste-classification driver and no
measurement of its production exists in that dataset.

Elements below are ranked by **gain over effort**. Gain combines how much
confounding an enriched target removes with how directly the element feeds
shutdown dose rate, as bulk material or as a trace impurity making a long-lived
emitter. Effort is dominated by enrichment difficulty, which scales with the
number of stable isotopes. **The 21 mono-isotopic elements are free**: no
enrichment, already unconfounded, and several are among the largest dose-rate
drivers in a plant.

Columns: **iso** = stable isotopes; **conf** = activation products reachable from
two or more of them at 14 MeV, that is, cross sections a natural sample cannot
separate; **sev** = fraction of the worst confounded product's yield not coming
from its single largest path, so above 0.5 most of the signal is unattributable.
**\*** marks an element never measured in the previous campaign.

**Band A. Mono-isotopic: no enrichment needed, start here**

| El | Z | iso | conf | sev | enrich | role | dose-rate products |
|---|--:|--:|--:|--:|---|---|---|
| Be\* | 4 | 1 | 0 | - | none needed | multiplier, PFC | He-3/H-3 production, Be-10 |
| F | 9 | 1 | 0 | - | none needed | molten salt | F-18, O-19, N-16 |
| Na | 11 | 1 | 0 | - | none needed | coolant, trace | Na-22 (2.6 y), Na-24 |
| Al | 13 | 1 | 0 | - | none needed | structure, insulator | Na-24, Na-22 (2.6 y), Al-26 |
| P | 15 | 1 | 0 | - | none needed | steel trace | P-32, Si-31 |
| Sc | 21 | 1 | 0 | - | none needed | trace in Ti | Sc-46 (84 d), Sc-47 |
| Mn | 25 | 1 | 0 | - | none needed | steel constituent | Mn-54 (312 d), Mn-56 |
| Co | 27 | 1 | 0 | - | none needed | structural impurity | Co-60 (5.3 y), Co-58m/g |
| As | 33 | 1 | 0 | - | none needed | steel trace | Ge-75, As-74 |
| Y | 39 | 1 | 0 | - | none needed | insulator, HTS | Y-88, Sr-89 |
| Nb | 41 | 1 | 0 | - | none needed | structural, magnet | Nb-94 (2e4 y), Nb-92m, Nb-95 |
| Rh | 45 | 1 | 0 | - | none needed | trace | Rh-104, Rh-103m |
| I | 53 | 1 | 0 | - | none needed | volatile product | I-128, I-130 |
| Cs | 55 | 1 | 0 | - | none needed | fission/trace | Cs-134 (2.1 y) |
| Pr | 59 | 1 | 0 | - | none needed | trace | Pr-140, Ce-139 |
| Tb | 65 | 1 | 0 | - | none needed | trace impurity | Tb-160 (72 d) |
| Ho | 67 | 1 | 0 | - | none needed | trace impurity | Ho-166m (1200 y) |
| Tm | 69 | 1 | 0 | - | none needed | trace | Tm-168, Tm-170 |
| Au | 79 | 1 | 0 | - | none needed | trace, dosimetry | Au-196, Au-198 |
| Bi | 83 | 1 | 0 | - | none needed | LBE coolant | Po-210 (alpha), Bi-207 |

**Band B. Two isotopes: cheapest enrichment, large gain**

| El | Z | iso | conf | sev | enrich | role | dose-rate products |
|---|--:|--:|--:|--:|---|---|---|
| Ag | 47 | 2 | 3 | 0.48 | easy | trace, magnet solder | Ag-108m (438 y), Ag-110m (250 d) |
| Eu | 63 | 2 | 3 | 0.48 | easy | trace in concrete | Eu-152 (13.5 y), Eu-154 (8.6 y) |
| Sb | 51 | 2 | 3 | 0.43 | easy | trace | Sb-124 (60 d), Sb-125 (2.8 y) |
| Re | 75 | 2 | 3 | 0.37 | easy | W alloy | Re-186, Re-188, W-185 |
| Ir | 77 | 2 | 3 | 0.37 | easy | trace | Ir-192 (74 d), Ir-194m |
| Cu | 29 | 2 | 3 | 0.31 | easy | conductor, magnet | Cu-64, Co-60, Zn-65 |
| B\* | 5 | 2 | 5 | 0.20 | easy | shield, absorber | H-3 via B-10(n,t), Be-7 |
| Li\* | 3 | 2 | 5 | 0.08 | easy | breeder | H-3, Be-7 |
| In | 49 | 2 | 3 | 0.04 | easy | trace, dosimetry | In-116m, In-114m |
| N\* | 7 | 2 | 5 | 0.00 | easy | steel constituent | C-14 (5730 y), N-16 |
| V | 23 | 2 | 5 | 0.00 | easy | structural (V alloys) | V-52, Sc-48, Ti-51 |
| Ta | 73 | 2 | 5 | 0.00 | easy | structural, W alloy | Ta-182 (114 d), Ta-180m |

**Band C. Primary materials: worth the cost whatever it is**

| El | Z | iso | conf | sev | enrich | role | dose-rate products |
|---|--:|--:|--:|--:|---|---|---|
| Mo | 42 | 7 | 21 | 0.60 | hard | structural, PFC | Nb-94, Mo-99, Tc-99 |
| Ti | 22 | 5 | 15 | 0.59 | hard | structural, magnet | Sc-46 (84 d), Sc-48 |
| W | 74 | 5 | 15 | 0.57 | hard | PFC armour | W-187, W-185, Ta-182, Re-186 |
| Sn | 50 | 10 | 30 | 0.51 | very hard | Nb3Sn magnet | Sn-123m, Sb-124, In-118m |
| Zr | 40 | 5 | 16 | 0.50 | hard | cladding, insulator | Nb-95, Zr-95, Nb-94 |
| Pb | 82 | 4 | 11 | 0.49 | moderate | multiplier, coolant | Bi-207, Po-210, Tl-208 |
| Ni | 28 | 5 | 15 | 0.45 | hard | primary structural | Co-58 (70.9 d), Co-60, Ni-63 |
| Si | 14 | 3 | 9 | 0.40 | moderate | steel, ceramic, SiC | Al-28, Mg-27, Si-31 |
| Cr | 24 | 4 | 11 | 0.20 | moderate | primary structural | Cr-51 (27.7 d), V-52 |
| O\* | 8 | 3 | 9 | 0.16 | moderate | oxide, coolant | N-16, O-19, C-14 |
| Fe | 26 | 4 | 11 | 0.12 | moderate | primary structural | Mn-54 (312 d), Fe-59, Mn-56 |

**Band D. Confounded, secondary relevance**

| El | Z | iso | conf | sev | enrich | role | dose-rate products |
|---|--:|--:|--:|--:|---|---|---|
| Dy | 66 | 7 | 20 | 0.64 | hard | permanent magnet | Dy-159, Tb-160 |
| Sm | 62 | 7 | 20 | 0.63 | hard | permanent magnet | Sm-151, Pm-147 |
| Er | 68 | 6 | 18 | 0.60 | hard | trace, insulator | Er-169, Ho-166m |
| Gd | 64 | 7 | 21 | 0.60 | hard | burnable absorber, HTS | Gd-153, Eu-152, Tb-160 |
| Ru | 44 | 7 | 21 | 0.60 | hard | trace | Ru-103, Tc-99 |
| Yb | 70 | 7 | 21 | 0.58 | hard | trace | Yb-169, Tm-170 |
| Nd | 60 | 7 | 22 | 0.57 | hard | permanent magnet | Nd-147, Pr-143 |
| Ba | 56 | 7 | 20 | 0.56 | hard | HTS, concrete | Ba-137m, Cs-134 |
| Cd | 48 | 8 | 24 | 0.56 | very hard | absorber, trace | Cd-109, Ag-110m |
| Pd | 46 | 6 | 18 | 0.55 | hard | trace | Pd-109m, Rh-105 |
| Hf | 72 | 6 | 17 | 0.54 | hard | trace in Zr | Hf-181, Hf-175, Lu-177 |
| Ge | 32 | 5 | 15 | 0.51 | hard | semiconductor, trace | Ga-72, Ge-71 |
| Br | 35 | 2 | 3 | 0.49 | easy | trace | Br-82, Se-75 |
| Se | 34 | 6 | 18 | 0.48 | hard | trace | Se-75, Se-79 |
| Mg | 12 | 3 | 9 | 0.48 | moderate | insulator, alloy | Na-24, Ne-23 |
| Zn | 30 | 5 | 15 | 0.45 | hard | trace, coating | Zn-65 (244 d), Cu-64 |
| Sr | 38 | 4 | 11 | 0.43 | moderate | HTS, concrete | Sr-85, Rb-86, Y-88 |
| Ce | 58 | 4 | 9 | 0.43 | moderate | trace | Ce-141, Ce-139 |
| Ga | 31 | 2 | 3 | 0.40 | easy | trace, alloy | Ga-72, Zn-69m |
| Tl | 81 | 2 | 3 | 0.30 | easy | trace in Pb | Tl-204, Hg-203 |
| Rb | 37 | 2 | 3 | 0.28 | easy | trace | Rb-86, Kr-85 |
| Ca | 20 | 6 | 18 | 0.27 | hard | concrete | Ca-45, K-42, Sc-47 |
| Cl | 17 | 2 | 3 | 0.24 | easy | salt, trace | S-35, Cl-36 (3e5 y) |
| S | 16 | 4 | 13 | 0.15 | moderate | steel trace | P-32, S-35, Si-31 |
| K | 19 | 3 | 9 | 0.07 | moderate | trace, concrete | K-42, Ar-41 |
| Lu | 71 | 2 | 5 | 0.03 | easy | trace | Lu-177, Lu-176m |
| C\* | 6 | 2 | 5 | 0.01 | easy | PFC, steel | C-14 (5730 y), Be-7 |
| La | 57 | 2 | 5 | 0.00 | easy | trace | La-140, Ba-139 |

**Band E. Completeness: gases and non-fusion elements**

| El | Z | iso | conf | sev | enrich | role | dose-rate products |
|---|--:|--:|--:|--:|---|---|---|
| Xe\* | 54 | 9 | 27 | 0.64 | very hard | fission gas, diagnostics | Xe-133, I-131 |
| Pt | 78 | 6 | 18 | 0.63 | hard | trace, catalyst | Pt-195m, Ir-192 |
| Hg | 80 | 7 | 21 | 0.57 | hard | trace | Hg-203, Au-198 |
| Kr\* | 36 | 6 | 18 | 0.54 | hard | fission gas | Kr-85 (10.8 y) |
| Os | 76 | 7 | 21 | 0.53 | hard | trace | Os-185, Re-186 |
| Te | 52 | 8 | 24 | 0.51 | very hard | trace | Te-129m, Sb-124 |
| Ar\* | 18 | 3 | 6 | 0.16 | moderate | air activation | Ar-41 (1.8 h), Cl-38 |
| Ne\* | 10 | 3 | 9 | 0.10 | moderate | trace gas | F-20, Ne-23 |
| U\* | 92 | 3 | 6 | 0.01 | moderate | not fusion relevant | - |
| Th\* | 90 | 2 | 3 | 0.00 | easy | not fusion relevant | - |
| H\* | 1 | 2 | 5 | 0.00 | easy | coolant, plasma | H-3 |
| He\* | 2 | 2 | 5 | 0.00 | easy | coolant | H-3 via He-3 |
| Pa\* | 91 | 1 | 0 | - | none needed | not fusion relevant | - |

---

## 6. Why this gives better nuclear data

An evaluated library is nuclear model calculations, adjusted where differential
data exists to constrain them. For most of the roughly 2400 target nuclides a
library must cover, **no differential measurement exists** and the evaluation is
unadjusted model output with globally fitted parameters.

This is why minor isotopes of common elements are so often wrong. The element
looks well validated because its dominant isotope has been measured many times.
The minor isotopes, contributing a few percent each to every natural-sample
measurement ever made, have never been separately constrained.

One isotopic measurement changes three things an elemental one cannot:

- **It anchors an unconstrained prediction.** Optical potential, level density and
  pre-equilibrium parameters are fitted globally, so one reliable point pins the
  local value and improves neighbouring unmeasured nuclides too.
- **It makes covariances mean something.** An evaluated uncertainty on an
  unmeasured reaction is the spread of a model prior, not knowledge. Propagating
  it yields numbers that look rigorous and trace back to no measurement.
- **It breaks the compensating errors of section 1**, which no quantity of further
  elemental data can do. Libraries can then be tested against a constraint they
  were never fitted to. Some will fail, which is the point.

Isomeric branching ratios gain disproportionately: they are among the least
constrained quantities in evaluated data, they enter dose rates almost undamped,
and measuring both states costs nothing beyond measuring one.

---

## 7. Why that gives better shutdown dose rates

The chain is: neutron transport → flux → **activation** → inventory → decay photon
source → photon transport → dose rate. Transport is Monte Carlo, with statistical
error that shrinks with computing time. **The activation step is where the
irreducible uncertainty lives, and it enters entirely through nuclear data.**
There is nothing else in that step to improve.

The improvement is concentrated, because dose rate at any cooling time is
dominated by a handful of nuclides: short-lived bulk activity at seconds to
hours; Mn-54, Co-58, Nb-95, Ta-182 at days to months; Co-60, Eu-152, Ag-108m at
years. Two features of that list drive the whole priority ordering.

**They often come from trace impurities, not bulk constituents.** Cobalt at 0.05%
in a steel dominates the dose rate after a year through Co-60. Silver at parts
per million dominates after a century through Ag-108m. A trace element
contributes through **one channel from one isotope**, which is exactly the clean
isolated cross section an enriched target determines and an elemental measurement
of the bulk alloy never sees.

**They are reached by single dominant capture channels**: Co-59(n,γ)Co-60,
Ta-181(n,γ)Ta-182, Ag-107(n,γ)Ag-108m, Ho-165(n,γ)Ho-166m, Nb-93(n,γ)Nb-94. Every
one is capture on a mono-isotopic or nearly mono-isotopic element. From section 2
capture is the worst predicted class in existing data at 44% within ±25%; from
section 5 these elements need no enrichment at all.

**The reactions that dominate long-term dose rate and waste classification are
simultaneously the worst known and the cheapest to measure properly.** That is
the strongest argument here, and it falls straight out of the priority table.

In engineering terms, dose rate uncertainties of a factor of two to three are
common and are managed by margin: longer cooling before access, more shielding,
more remote handling. The value is asymmetric, since an over-prediction costs
schedule and money while an under-prediction is a late safety case failure, so
margin is set against the pessimistic end. Narrowing the band converts directly
into shorter cooling before access, less shielding mass, and a maintenance plan
committable at design time. Waste classification is the same argument over longer
times: disposal route boundaries are set by Nb-94, Ag-108m, Ho-166m, C-14, Tc-99
and Ni-59/63, all from trace impurities through single channels, and an inventory
near a boundary is decided by exactly these cross sections.

---

## 8. Practical points

- **Assay impurities as part of the measurement.** The N-16 result shows what an
  unassayed light-element impurity does. Publish oxygen, nitrogen and carbon,
  which routine metallic assays often omit.
- **Monitor foils in every irradiation**, so fluence is measured in the sample
  geometry rather than inferred from a calibration elsewhere.
- **Publish the flux spectrum with its covariance**, not a bare histogram. Without
  it the extracted cross section cannot be given an honest error bar.
- **Publish raw counts and the decay data used to reduce them.** Existing
  measurements are permanently tied to the decay data current when analysed and
  cannot be re-reduced. Over the decades such data stays in use, this is worth
  more than any single improvement in the measurement itself.
- **Staging.** Band A needs no enrichment and can start on procurement alone. Band
  B is 23 elements at the cheapest enrichment available and runs in parallel. Later
  bands should follow A and B, which will show whether model systematics fail in a
  pattern that changes the order.
