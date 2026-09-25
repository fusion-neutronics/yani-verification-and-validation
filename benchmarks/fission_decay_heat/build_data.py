#!/usr/bin/env python3
"""Pack the CoNDERC fission decay-heat benchmark into one JSON.

The IAEA publishes it as `fission.zip`, holding 48 measured decay-heat curves
across ten fissioning systems, the neutron fields the irradiations were done
in, and the FISPACT-II and ORIGEN input decks that define them.

    build_data.py                             # downloads fission.zip (28 MB, cached)
    build_data.py --fission-zip fission.zip   # a copy you already have

Run only when the benchmark data changes. The result is committed, so nobody
needs the archive to reproduce a run; the point of keeping this script is that
it says exactly how the JSON was derived, and lets anyone re-derive it.

## What is in the archive, and what is not

Unlike the FNS and effective-cross-section archives, **this one carries no
other code's calculated results**. It has FISPACT-II and ORIGEN *inputs*, and
13 source papers as PDFs, but no output curves. So the pages built from this
are yani against measurement, not a three-way code comparison, and the decks
are useful as a statement of what the experiment was rather than as a
reference answer.

## The fields

`Fispact-II/Inputs/fluxes_therm` and `fluxes_fast` are 709-group FISPACT flux
files in descending energy order, each with exactly one populated group:

* thermal, descending group 538, which is CCFE-709 ascending group 170,
  spanning 0.025119 to 0.026303 eV, the 0.0253 eV thermal point;
* fast, descending group 178, ascending group 530, spanning 398110 to
  416870 eV.

Both are monoenergetic rather than spectra. That is the benchmark's own
definition of "thermal" and "fast" and is carried across unchanged.

## The measurement

Every curve is `T(s)` against beta, gamma and total decay heat in **MeV per
fission per second**, each with its uncertainty, which is the normalisation
this benchmark uses throughout: the decay power divided by the total number of
fissions the irradiation caused. The irradiation is either a pulse, taken as
instantaneous, or a stated number of seconds at constant power.
"""

import argparse
import csv
import io
import json
import pathlib
import sys
import urllib.request
import zipfile

HERE = pathlib.Path(__file__).resolve().parent

FISSION_URL = "https://nds.iaea.org/data/fission/fission.zip"

# FISPACT flux files are descending in energy; CCFE-709 is ascending.
GROUPS = 709
GROUP_STRUCTURE = "CCFE-709"

FIELD_FILES = {
    "thermal": "fission/Fispact-II/Inputs/fluxes_therm",
    "fast": "fission/Fispact-II/Inputs/fluxes_fast",
}


def fetch(path):
    if path is not None:
        return pathlib.Path(path).read_bytes()
    cache = HERE / "data" / "fission.zip"
    if cache.exists():
        return cache.read_bytes()
    print(f"downloading {FISSION_URL}", file=sys.stderr)
    with urllib.request.urlopen(FISSION_URL, timeout=300) as response:
        payload = response.read()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(payload)
    return payload


def parse_field(text):
    """A FISPACT flux file into ascending CCFE-709 group fluxes.

    The file is group values in descending energy, then a normalisation, then a
    title. Only the values are taken; the normalisation is 1.000 in both files
    and multiplying by it would be a no-op that hides a change if it ever is
    not.
    """
    values = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        try:
            values.extend(float(p) for p in parts)
        except ValueError:
            break  # the title line ends the numbers
    if len(values) < GROUPS:
        raise SystemExit(f"flux file holds {len(values)} values, need at least {GROUPS}")
    descending = values[:GROUPS]
    normalisation = values[GROUPS] if len(values) > GROUPS else 1.0
    if abs(normalisation - 1.0) > 1e-9:
        raise SystemExit(
            f"flux normalisation is {normalisation}, not 1.0. This script assumes "
            f"the values are absolute; check the file before changing that.")
    return list(reversed(descending))


def _number(cell):
    """A cell as a float, or None where the experiment measured nothing."""
    cell = cell.strip()
    if cell in ("", "-"):
        return None
    return float(cell)


def parse_curve(text):
    """One measured decay-heat curve.

    Three header lines, then rows of time and the beta, gamma and total heat
    with their uncertainties. Every file in the archive has exactly these
    columns, which is asserted rather than assumed.
    """
    author = irradiation = None
    rows = []
    reader = csv.reader(io.StringIO(text))
    for parts in reader:
        if not parts:
            continue
        head = parts[0].strip()
        if head.startswith("#Author:"):
            author = parts[1].strip()
        elif head.startswith("#Irradiation:"):
            irradiation = parts[1].strip()
        elif head.startswith("#T("):
            expected = ["T(s)", "Beta(MeV/f/s)", "dBeta(MeV/f/s)", "Gamma(MeV/f/s)",
                        "dGamma(MeV/f/s)", "Total(MeV/f/s)", "dTotal(MeV/f/s)"]
            got = [p.strip().lstrip("#") for p in parts]
            if got != expected:
                raise SystemExit(f"unexpected columns {got}")
        elif not head.startswith("#"):
            # A "-" or an empty cell is a component this experiment did not
            # measure, which is common: 19 of the 48 curves carry only some of
            # beta, gamma and total, because the technique determined which.
            # Time is always present, and a row without it is not a row.
            cells = [_number(p) for p in parts[:7]]
            if cells[0] is None:
                raise SystemExit(f"a row carries no time: {parts!r}")
            rows.append(cells)
    if author is None or irradiation is None:
        raise SystemExit("curve has no #Author or #Irradiation header")

    # "Pulse" is an instantaneous burst; anything else is a duration in
    # seconds, written as e.g. "20000s".
    if irradiation.lower() == "pulse":
        seconds = 0.0
    else:
        seconds = float(irradiation.rstrip("sS"))

    measured = {
        name: [r[i] for r in rows]
        for name, i in (("beta", 1), ("beta_uncertainty", 2), ("gamma", 3),
                        ("gamma_uncertainty", 4), ("total", 5), ("total_uncertainty", 6))
    }
    # Which components this curve actually carries, so a consumer scores what
    # was measured rather than treating a missing beta as a beta of zero.
    components = [c for c in ("beta", "gamma", "total")
                  if any(v is not None for v in measured[c])]

    return {
        "author": author,
        "irradiation": irradiation,
        "irradiation_s": seconds,
        "components": components,
        "times_s": [r[0] for r in rows],
        "beta_MeV_per_fission_s": measured["beta"],
        "beta_uncertainty": measured["beta_uncertainty"],
        "gamma_MeV_per_fission_s": measured["gamma"],
        "gamma_uncertainty": measured["gamma_uncertainty"],
        "total_MeV_per_fission_s": measured["total"],
        "total_uncertainty": measured["total_uncertainty"],
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fission-zip", default=None, help="a local copy of fission.zip")
    ap.add_argument("--output", type=pathlib.Path, default=HERE / "data" / "fission_data.json")
    args = ap.parse_args()

    archive = zipfile.ZipFile(io.BytesIO(fetch(args.fission_zip)))

    fields = {}
    for name, path in FIELD_FILES.items():
        flux = parse_field(archive.read(path).decode("utf-8", "replace"))
        populated = [(i, v) for i, v in enumerate(flux) if v]
        fields[name] = {
            "group_structure": GROUP_STRUCTURE,
            "flux": flux,
            "source_file": path,
            "populated_groups": populated,
        }
        print(f"{name}: {len(populated)} populated group(s) {populated}", file=sys.stderr)

    cases = {}
    for entry in sorted(archive.namelist()):
        parts = entry.split("/")
        if len(parts) != 4 or parts[1] != "expDataSystem" or not entry.endswith(".csv"):
            continue
        system, filename = parts[2], parts[3]
        curve = parse_curve(archive.read(entry).decode("utf-8", "replace"))
        nuclide, field = system.split("_", 1)
        if field not in fields:
            raise SystemExit(f"{entry}: field {field!r} has no flux file")
        curve["nuclide"] = nuclide
        curve["field"] = field
        curve["source_file"] = entry
        cases.setdefault(system, {})[filename[:-4]] = curve

    total = sum(len(v) for v in cases.values())
    print(f"{total} curve(s) across {len(cases)} system(s)", file=sys.stderr)

    document = {
        "built_by": "benchmarks/fission_decay_heat/build_data.py",
        "source": FISSION_URL,
        "description": (
            "CoNDERC fission decay heat: measured decay power per fission after "
            "irradiation of a fissioning system, in MeV per fission per second."),
        "reference_codes_note": (
            "The archive carries FISPACT-II and ORIGEN inputs but no calculated "
            "results, so unlike the other benchmarks here there is no second "
            "code's curve to compare against."),
        "group_structure": GROUP_STRUCTURE,
        "fields": fields,
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=1) + "\n")
    print(f"wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
