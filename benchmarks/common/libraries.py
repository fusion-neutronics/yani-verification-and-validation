"""The nuclear-data combinations every benchmark on this site is run with.

yani sources five things independently -- cross sections, reaction topology,
isomeric branching, decay data and fission yields -- so "which library" is not
one choice but five. Each combination below sets all five explicitly, because a
setting left alone is a setting you cannot report.

Which library can supply which subsection is fixed by what the library actually
publishes:

| library      | cross sections | decay | reactions | fission yields | branching |
|--------------|:--------------:|:-----:|:---------:|:--------------:|:---------:|
| `tendl-2017` | yes            | --    | yes       | --             | yes       |
| `tendl-2025` | yes            | --    | yes       | --             | yes       |
| `endf-b8.1`  | yes            | yes   | yes       | yes            | yes       |
| `jeff-4.0`   | yes            | yes   | yes       | yes            | yes       |
| `fendl-3.2d` | yes            | --    | --        | --             | --        |

TENDL is a neutron-only evaluation, so a TENDL run always borrows decay data and
fission yields from somewhere else. That is not a workaround; it is the most of
a library swap TENDL is able to express, and it means a C/E from a TENDL
combination is a statement about production rates measured against fixed decay
data.
"""

import collections

Combination = collections.namedtuple(
    "Combination", "name cross_sections reactions branching decay fission_yields note")


def _combination(name, cross_sections, reactions, branching, decay, note):
    """Fission yields follow the decay library: no benchmark here is fissionable.

    Neither FNS foils nor the integral spectra hold a fissionable nuclide, so
    the yields subsection is never read. It is still set explicitly rather than
    left to a default, so the run is fully described by its combination.
    """
    return Combination(name, cross_sections, reactions, branching, decay, decay, note)


# The apples-to-apples entry comes first and is treated specially by the runners:
# it is the one FISPACT-II was run with on the CoNDERC benchmarks, so it is the
# only line on which yani and FISPACT are reading the same evaluations.
COMBINATIONS = [
    _combination(
        "tendl-2017", "tendl-2017", "tendl-2017", "tendl-2017", "endf-b8.1",
        "The library FISPACT-II was run with for the published CoNDERC results. "
        "This is the apples-to-apples comparison: same cross sections, same "
        "reaction topology, same branching, different code."),
    _combination(
        "tendl-2025", "tendl-2025", "tendl-2025", "tendl-2025", "endf-b8.1",
        "The current TENDL, everything else held fixed. The difference from "
        "tendl-2017 is eight years of evaluation work and nothing else."),
    _combination(
        "endf-b8.1", "endf-b8.1", "endf-b8.1", "endf-b8.1", "endf-b8.1",
        "One library for all five subsections, which only ENDF/B and JEFF can "
        "do. Fewer parent nuclides than TENDL, so fewer production channels."),
    _combination(
        "jeff-4.0", "jeff-4.0", "jeff-4.0", "jeff-4.0", "jeff-4.0",
        "The other complete library, again supplying all five subsections."),
    _combination(
        "fendl-3.2d", "fendl-3.2d", "endf-b8.1", "endf-b8.1", "endf-b8.1",
        "The FENDL cross sections, which is the library fusion neutronics "
        "usually transports with. FENDL publishes no chain, so the network "
        "comes from ENDF/B-VIII.1."),
    _combination(
        "tendl-2017+jeff-decay", "tendl-2017", "tendl-2017", "tendl-2017", "jeff-4.0",
        "tendl-2017 with the decay data swapped to JEFF-4.0. Decay heat is a "
        "sum of N x lambda x Q, so this moves lambda and Q while leaving N: it "
        "separates how much of the deviation belongs to the decay data."),
    _combination(
        "tendl-2025+jeff-decay", "tendl-2025", "tendl-2025", "tendl-2025", "jeff-4.0",
        "The same swap on the current TENDL."),
    _combination(
        "tendl-2025-xs+endf-chain", "tendl-2025", "endf-b8.1", "endf-b8.1", "endf-b8.1",
        "TENDL cross sections on an ENDF/B network. A blend, and reported as "
        "one: it is here to show what the chain contributes, not as a "
        "recommendation."),
    _combination(
        "tendl-2017-xs+endf-branching", "tendl-2017", "tendl-2017", "endf-b8.1",
        "endf-b8.1",
        "tendl-2017 with only the isomeric branching moved off it. On foils "
        "whose heat runs through a metastable state this is the whole answer, "
        "and on ground-state foils it does nothing."),
    _combination(
        "fendl-3.2d+tendl-2025-chain", "fendl-3.2d", "tendl-2025", "tendl-2025",
        "endf-b8.1",
        "FENDL transport cross sections against the widest available network, "
        "which is the arrangement a fusion analyst already transporting with "
        "FENDL would actually want."),
]

BY_NAME = {combination.name: combination for combination in COMBINATIONS}

# What FISPACT-II was run with for the results published in the CoNDERC
# archives, and therefore the only fair code-to-code comparison.
APPLES_TO_APPLES = "tendl-2017"


def apply(combination, yani):
    """Set yani's five nuclear-data settings from a combination.

    They are module-level process state rather than per-call arguments, so this
    is a function with a side effect by necessity. Every setting is written on
    every call: leaving one at whatever the previous combination set it to is
    how a sweep silently reports the wrong provenance.
    """
    yani.cross_section_data = combination.cross_sections
    yani.transmutation_reactions = combination.reactions
    yani.transmutation_branch_ratios = combination.branching
    yani.transmutation_decay_data = combination.decay
    yani.transmutation_fission_yields = combination.fission_yields


def resolve(names):
    """Combinations by name, or all of them when nothing is named."""
    if not names:
        return list(COMBINATIONS)
    chosen = []
    for name in names:
        if name not in BY_NAME:
            raise SystemExit(
                f"no combination {name!r}. Known: {' '.join(sorted(BY_NAME))}")
        chosen.append(BY_NAME[name])
    return chosen


def as_dict(combination):
    return {
        "name": combination.name,
        "cross_sections": combination.cross_sections,
        "reactions": combination.reactions,
        "branching": combination.branching,
        "decay": combination.decay,
        "fission_yields": combination.fission_yields,
        "note": combination.note,
    }
