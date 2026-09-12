"""UKAEA's FISPACT-II decay libraries, fetched and converted for a same-data comparison.

The FISPACT-II results published in the CoNDERC archives were run with UKAEA's
`decay_2012` decay library, which no yani keyword supplies. UKAEA publishes it,
and its successor `decay_2020`, as per-nuclide ENDF-6 files on the OECD-NEA
GitLab (https://git.oecd-nea.org/fispact/nuclear_data, readable without an
account). This module downloads one, converts it with yani's own converter and
caches the result, so a combination can name it the way it names a keyword.

It is deliberately not a yani keyword. The repository carries no licence file,
so the data is not republished anywhere: every machine fetches it from UKAEA's
own distribution and converts it locally, which takes about a minute.

    python -m common.ukaea_decay            # fetch and convert decay_2012
    python -m common.ukaea_decay decay_2020

The converted subsection lands under `~/.cache/yani-verification-and-validation/`
(override with `YANI_VV_CACHE`) and is reused on every later run.
"""

import hashlib
import os
import pathlib
import sys
import tarfile
import time
import urllib.request

REPOSITORY = "https://git.oecd-nea.org/fispact/nuclear_data/-/raw/main/"

# archive name in the repository, and the directory inside it holding the
# per-nuclide files.
LIBRARIES = {
    "decay_2012": ("decay.tar.bz2", "decay/decay_2012"),
    "decay_2020": ("decay2020.tar.bz2", "decay_2020"),
}


def cache_root():
    override = os.environ.get("YANI_VV_CACHE")
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".cache" / "yani-verification-and-validation"


def cached_decay_directory(library="decay_2012"):
    """The converted `decay/` subsection if it is already on this machine.

    Returns `None` rather than fetching. `decay_directory` downloads a 5.5 MB
    archive from the OECD-NEA GitLab and spends about a minute converting it,
    which is the right behaviour when a run needs the data and the wrong
    behaviour when a caller only wants to know what is already there. Recording
    provenance is the second kind.
    """
    if library not in LIBRARIES:
        return None
    decay = cache_root() / f"ukaea-{library.replace('_', '-')}" / "decay"
    if (decay / "provenance.json").is_file() and (decay / "nuclides.arrow").is_file():
        return decay
    return None


def decay_directory(library="decay_2012"):
    """The converted `decay/` subsection of a UKAEA library, fetching and
    converting it on first use.

    Returns a path suitable for `yani.transmutation_decay_data`.
    """
    if library not in LIBRARIES:
        raise SystemExit(f"unknown UKAEA decay library {library!r}; "
                         f"known: {' '.join(LIBRARIES)}")
    root = cache_root() / f"ukaea-{library.replace('_', '-')}"
    decay = root / "decay"
    if (decay / "provenance.json").is_file() and (decay / "nuclides.arrow").is_file():
        return decay

    archive_name, member_dir = LIBRARIES[library]
    archive = root / archive_name
    root.mkdir(parents=True, exist_ok=True)
    if not archive.is_file():
        url = REPOSITORY + archive_name
        print(f"ukaea decay: fetching {url}", file=sys.stderr, flush=True)
        # The GitLab instance refuses urllib's default User-Agent.
        request = urllib.request.Request(url, headers={"User-Agent": "yani-verification"})
        partial = archive.with_suffix(".part")
        with urllib.request.urlopen(request) as response, open(partial, "wb") as out:
            out.write(response.read())
        partial.replace(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()

    # Per-nuclide ENDF-6 files. A few carry bytes outside UTF-8 in their
    # comment records, which the ENDF reader rejects, so they are re-encoded
    # to ASCII on the way out; the numbers are unaffected.
    sources = root / "endf"
    sources.mkdir(exist_ok=True)
    started = time.time()
    with tarfile.open(archive, "r:bz2") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            parent, _, name = member.name.rpartition("/")
            if parent != member_dir or name.startswith("."):
                continue
            raw = tar.extractfile(member).read()
            (sources / name).write_bytes(raw.decode("latin-1").encode("ascii", "replace"))
    files = sorted(str(p) for p in sources.iterdir())
    if not files:
        raise SystemExit(f"{archive}: no files under {member_dir}/")

    import yani
    print(f"ukaea decay: converting {len(files)} {library} evaluations "
          f"into {decay}", file=sys.stderr, flush=True)
    count = yani.convert_transmutation(
        decay_files=files,
        fpy_files=[],
        neutron_files=[],
        output_path=str(root),
        library=f"ukaea-{library.replace('_', '-')}",
        decay_library=f"ukaea-{library.replace('_', '-')}",
        data_version=f"nea-gitlab-sha256-{digest[:16]}",
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        subsections=["decay"],
    )
    print(f"ukaea decay: {count} nuclides in {time.time() - started:.0f} s",
          file=sys.stderr, flush=True)
    return decay


def main():
    library = sys.argv[1] if len(sys.argv) > 1 else "decay_2012"
    print(decay_directory(library))


if __name__ == "__main__":
    main()
