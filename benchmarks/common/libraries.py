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
| `ukaea-decay-2012` | --       | yes   | --        | --             | --        |

TENDL is a neutron-only evaluation, so a TENDL run always borrows decay data and
fission yields from somewhere else. That is not a workaround; it is the most of
a library swap TENDL is able to express, and it means a C/E from a TENDL
combination is a statement about production rates measured against fixed decay
data.

`ukaea-decay-2012` is not a yani keyword. It is UKAEA's FISPACT-II decay
library, the one the published CoNDERC results were run with, fetched from
UKAEA's own distribution and converted locally by `common.ukaea_decay` the
first time a combination names it. It exists here so the comparison with
FISPACT-II can be made on the same decay data, and nowhere else.
"""

import collections
import json
import os
import pathlib

from common import ukaea_decay

Combination = collections.namedtuple(
    "Combination", "name cross_sections reactions branching decay fission_yields note")


def _combination(name, cross_sections, reactions, branching, decay, note,
                 fission_yields=None):
    """Fission yields follow the decay library: no benchmark here is fissionable.

    Neither FNS foils nor the integral spectra hold a fissionable nuclide, so
    the yields subsection is never read. It is still set explicitly rather than
    left to a default, so the run is fully described by its combination. A
    decay source that publishes no yields names where they come from instead.
    """
    return Combination(name, cross_sections, reactions, branching, decay,
                       fission_yields or decay, note)


# Decay sources that are not yani keywords: the name a combination uses, and
# the function that fetches and converts the data and returns the directory to
# point yani at.
LOCAL_DECAY = {
    "ukaea-decay-2012": lambda: ukaea_decay.decay_directory("decay_2012"),
}

# The apples-to-apples entry comes first and is treated specially by the runners:
# it is what FISPACT-II was run with on the CoNDERC benchmarks, cross sections
# and decay data both, so it is the only line on which yani and FISPACT-II are
# reading the same data and a difference between them is the code.
COMBINATIONS = [
    _combination(
        "tendl-2017+decay-2012", "tendl-2017", "tendl-2017", "tendl-2017",
        "ukaea-decay-2012",
        "Exactly what FISPACT-II was run with for the published CoNDERC "
        "results: TENDL-2017 cross sections, reaction topology and branching, "
        "and UKAEA's decay_2012 decay library. On this line a difference "
        "between yani and FISPACT-II is a difference between two codes, and "
        "there is almost none: the median deviation between the two heat "
        "curves is 0.01%.",
        fission_yields="endf-b8.1"),
    _combination(
        "tendl-2017", "tendl-2017", "tendl-2017", "tendl-2017", "endf-b8.1",
        "The same neutron library with the decay data yani users get by "
        "default, ENDF/B-VIII.1. Against the line above this isolates the "
        "decay data: it is what moves the Sn, Ta and Ho foils, and where "
        "ENDF/B-VIII.1 carries a Q/3 placeholder record (Sn111, Cd105, "
        "Co62m) the placeholder is what moves them."),
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
        "separates how much of the deviation belongs to the decay data. JEFF-4.0 "
        "reproduces FISPACT-II's decay_2012 values for the nuclides that carry "
        "the FNS heat (Ta180, Ho164), so this is the closest same-data "
        "comparison with the published FISPACT-II curves."),
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
# archives, cross sections and decay data both, and therefore the only fair
# code-to-code comparison on the decay-heat benchmark.
APPLES_TO_APPLES = "tendl-2017+decay-2012"

# The effective cross sections involve no decay data, so there the plain
# TENDL-2017 combination already is the same-data comparison.
APPLES_TO_APPLES_ECS = "tendl-2017"


def apply(combination, yani):
    """Set yani's five nuclear-data settings from a combination.

    They are module-level process state rather than per-call arguments, so this
    is a function with a side effect by necessity. Every setting is written on
    every call: leaving one at whatever the previous combination set it to is
    how a sweep silently reports the wrong provenance.

    A decay source in `LOCAL_DECAY` is fetched and converted on first use and
    yani is pointed at the directory; the combination and everything written
    about the run keep the name.
    """
    yani.cross_section_data = combination.cross_sections
    yani.transmutation_reactions = combination.reactions
    yani.transmutation_branch_ratios = combination.branching
    decay = combination.decay
    if decay in LOCAL_DECAY:
        decay = str(LOCAL_DECAY[decay]())
    yani.transmutation_decay_data = decay
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


def _cache_root():
    override = os.environ.get("YAMC_CACHE_DIR")
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".cache" / "yamc"


def _stamp(directory):
    """The `data_version` a cached subsection records, if it records one."""
    for marker in ("provenance.json", "version.json"):
        path = pathlib.Path(directory) / marker
        if not path.is_file():
            continue
        try:
            value = json.loads(path.read_text()).get("data_version")
        except (json.JSONDecodeError, OSError):
            return None
        if isinstance(value, str) and value:
            return value
    return None


def data_versions(combination):
    """The release stamp behind each of a combination's five settings.

    The published libraries are overwritten in place when they are rebuilt, so
    the keyword `tendl-2017` names different bytes before and after a
    republish. Without this a result file cannot say which. The 2026-09-08
    rebuild changed every library's isomeric branching and was invisible in
    every output.

    Read out of the cache rather than asked of yani, because yani exposes no
    accessor for it: the stamp lives in `provenance.json` beside each cached
    transmutation subsection and in `version.json` beside each cached nuclide.
    That makes this best-effort and layout-dependent, and a `None` here means
    "not recorded" rather than "unstamped data". The durable fix is an
    accessor in the core, at which point this can be deleted.
    """
    root = _cache_root()
    found = {}
    for setting, source, subsection in (
            ("reactions", combination.reactions, "reactions"),
            ("branching", combination.branching, "branching"),
            ("decay", combination.decay, "decay"),
            ("fission_yields", combination.fission_yields, "fission_yields")):
        if source in LOCAL_DECAY:
            # Converted on this machine, so its stamp sits with the conversion.
            # Looked up rather than resolved: `LOCAL_DECAY[source]()` fetches
            # and converts when the cache is cold, and recording provenance
            # must not download 5.5 MB and spend a minute converting it.
            cached = ukaea_decay.cached_decay_directory(
                source.replace("ukaea-", "").replace("-", "_"))
            found[setting] = _stamp(cached) if cached else None
        elif isinstance(source, str) and not pathlib.Path(source).is_dir():
            found[setting] = _stamp(
                root / f"{source}-transmutation-{subsection}.arrow")
        else:
            found[setting] = _stamp(pathlib.Path(str(source)) / subsection)

    # Cross sections are per nuclide, so any cached one carries the stamp of
    # the release they all came from.
    library = combination.cross_sections
    stamp = None
    if isinstance(library, str):
        for directory in sorted(root.glob(f"{library}-*.arrow")):
            if "transmutation" in directory.name:
                continue
            stamp = _stamp(directory)
            if stamp:
                break
    found["cross_sections"] = stamp
    return found


def as_dict(combination):
    return {
        "name": combination.name,
        "cross_sections": combination.cross_sections,
        "reactions": combination.reactions,
        "branching": combination.branching,
        "decay": combination.decay,
        "fission_yields": combination.fission_yields,
        # Which bytes each setting resolved to, so a data rebuild is visible.
        "data_versions": data_versions(combination),
        "note": combination.note,
    }
