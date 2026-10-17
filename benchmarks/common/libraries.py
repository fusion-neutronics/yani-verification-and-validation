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
| `fendl-3.2d` | yes            | --    | yes       | --             | yes       |
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


def _stamp(directory):
    """The `data_version` a locally converted directory records, if any."""
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


def local_data_versions(combination):
    """The `data_version` stamp of each setting a combination reads from local data.

    yani reports the published release behind every library keyword a solve
    read (see `DataReleases`), and nothing for data it was pointed at as a
    directory. Here that is the UKAEA decay library, which `common.ukaea_decay`
    converts on this machine and stamps with the archive it came from, so the
    stamp is the record. Settings that name a published library are left out.
    A `None` means "not recorded" rather than "unstamped data".
    """
    found = {}
    for setting, source in (
            ("reactions", combination.reactions),
            ("branching", combination.branching),
            ("decay", combination.decay),
            ("fission_yields", combination.fission_yields)):
        if source in LOCAL_DECAY:
            # Looked up rather than resolved: `LOCAL_DECAY[source]()` fetches
            # and converts when the cache is cold, and recording provenance
            # must not download 5.5 MB and spend a minute converting it.
            cached = ukaea_decay.cached_decay_directory(
                source.replace("ukaea-", "").replace("-", "_"))
            found[setting] = _stamp(cached) if cached else None
        elif pathlib.Path(str(source)).is_dir():
            found[setting] = _stamp(pathlib.Path(str(source)) / setting)
    return found


class DataReleases:
    """The published release of each library behind one result file.

    A library keyword resolves at run time to the library's current published
    release, so the keyword `tendl-2017` names different bytes before and after
    a republish, and a result file has to say which. The 2026-09-08 rebuild
    changed every library's isomeric branching and was invisible in every
    output.

    So the record is what the solves report. yani resolves each keyword to one
    release per process, and every solve reports the ones it read as
    `TransmutationResults.data_releases`: the release, the sha256 of its
    manifest (which pins every file in it), the manifest's format version, and
    `offline`, true when the origin could not be reached and a cached release
    was used. The newest release in the cache is no substitute. The cache keeps
    every release a run has used, and a run reads the one the origin points at
    or, offline, the newest cached one holding what its first request needs;
    either can be older than the newest there.

    `read` takes one solve's report and keeps the libraries the combination
    names: the report covers every library the process has read, which for a
    process that ran another combination first includes others.

    One release of each library per file. A solve that read another release
    than the file already records, as a run resumed after a republish does,
    stops the run rather than mixing the two: `--redo` solves every case again
    against one release.
    """

    def __init__(self, combination, destination, recorded=None):
        self.destination = destination
        self._libraries = {combination.cross_sections, combination.reactions,
                           combination.branching, combination.decay,
                           combination.fission_yields}
        self.recorded = {keyword: dict(record)
                         for keyword, record in (recorded or {}).items()}

    @classmethod
    def resumed(cls, combination, destination, document, solved):
        """The record of a result file that a run is about to add to.

        `document` is the file as it stands, `{}` when there is none, and
        `solved` how many results it holds. Results from a run that recorded no
        releases, which is every file written before this record existed, were
        solved against releases nobody can now name, and adding to them would
        label them all with this run's, so that stops the run instead.
        """
        recorded = (document.get("combination") or {}).get("data_releases")
        if solved and recorded is None:
            raise SystemExit(
                f"{destination} holds {solved} results from a run that recorded "
                f"no data releases, so which release of each library they were "
                f"solved against is unknown, and adding to them would label "
                f"them all with this run's. Run again with --redo to solve them "
                f"against one release.")
        return cls(combination, destination, recorded)

    def read(self, data_releases):
        """Add one solve's `TransmutationResults.data_releases`."""
        for keyword, record in sorted(data_releases.items()):
            if keyword not in self._libraries:
                continue
            held = self.recorded.setdefault(keyword, dict(record))
            if (held["release"], held["manifest_sha256"]) != (
                    record["release"], record["manifest_sha256"]):
                raise SystemExit(
                    f"{self.destination}: its results were solved against "
                    f"{keyword} release {held['release']} (manifest sha256 "
                    f"{held['manifest_sha256']}), and this solve read release "
                    f"{record['release']} (manifest sha256 "
                    f"{record['manifest_sha256']}). A result file holds one "
                    f"release of each library, so this stops rather than mix "
                    f"them. Run again with --redo to solve every case against "
                    f"one release.")
            # The same bytes either way. True once any solve read them
            # offline, because that release need not have been the current one.
            held["offline"] = bool(held["offline"] or record["offline"])


def as_dict(combination, releases):
    """The combination as a result file records it.

    `releases` is the file's `DataReleases`, the published release of each
    library its solves read. With the stamps of any local data, that is which
    bytes the results came from, so a data rebuild is visible.
    """
    return {
        "name": combination.name,
        "cross_sections": combination.cross_sections,
        "reactions": combination.reactions,
        "branching": combination.branching,
        "decay": combination.decay,
        "fission_yields": combination.fission_yields,
        "data_releases": releases.recorded,
        "local_data_versions": local_data_versions(combination),
        "note": combination.note,
    }
