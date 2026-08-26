#!/usr/bin/env python3
"""Pack the CoNDERC effective cross-section benchmark into one JSON.

The IAEA publishes two datasets that only mean something together:

* **Effective RR** -- 365 measured spectrum-averaged ("effective") cross
  sections, each naming the reaction and the neutron field it was measured in,
  with the experimental uncertainty and the value FISPACT-II calculated with
  TENDL-2017 alongside it.
* **Spectra** -- the neutron fields themselves, as group fluxes with their own
  boundaries, under the same names the reaction table uses.

    build_data.py                          # downloads both (a few MB, cached)
    build_data.py --effective-zip ... --spectra-zip ...

A spectrum-averaged cross section is what an activation measurement actually
produces: a foil is irradiated in a known field, the product's activity is
counted, and the number reported is the production rate divided by the total
flux. It is therefore the cleanest possible test of the one thing an inventory
code does before any solving happens -- fold a cross section against a spectrum
-- and it is where a continuous-energy code and a multigroup one part company.

## What the product suffixes mean

The table names a product like `Mn-56`, `Cl-34m`, `K-38g` or `Au-196n`:

| suffix | means                    | this file records |
|--------|--------------------------|-------------------|
| `m`    | first metastable state   | `_m1`             |
| `n`    | second metastable state  | `_m2`             |
| `g`    | ground state only        | ground            |
| none   | the total over all states| ground + isomers  |

The last row is the one worth arguing about. `Dy-164(n,g)Dy-165` appears three
times in the table, once bare, once as `Dy-165g` and once as `Dy-165m`, which
only makes sense if the bare entry is the sum. Where no isomer of the product
exists the sum is the ground state anyway, so the rule costs nothing on the 240
reactions that have no isomeric sibling.
"""

import argparse
import collections
import json
import pathlib
import re
import shutil
import urllib.request
import zipfile

EFFECTIVE_URL = "https://nds.iaea.org/data/effective/effective.zip"
SPECTRA_URL = "https://nds.iaea.org/data/spectra/spectra.zip"

# Element-Mass(suffix)(n,channel)Element-Mass(suffix)
REACTION = re.compile(
    r"^([A-Z][a-z]?)-(\d+)\(n,([a-z0-9']+)\)([A-Z][a-z]?)-(\d+)([a-zA-Z]*)$")

ISOMER_SUFFIX = {"": None, "g": "ground", "m": "_m1", "n": "_m2"}

# The ENDF reaction numbers behind the table's channel names. Only used to
# report what the reaction is; the runner does not filter on MT, since what is
# measured is the production of a nuclide however it got there.
MT = {
    "n": 4, "2n": 16, "3n": 17, "g": 102, "p": 103, "d": 104, "t": 105,
    "a": 107, "np": 28, "na": 22, "pa": 112,
}


def fetch(url, destination, label):
    """A local copy of an IAEA archive, downloaded if there is not one."""
    if destination.is_file():
        print(f"{label}: using {destination}")
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"{label}: fetching {url}")
    # The IAEA server refuses urllib's default User-Agent, so it names itself.
    request = urllib.request.Request(url, headers={"User-Agent": "build_data.py"})
    partial = destination.with_suffix(destination.suffix + ".part")
    with urllib.request.urlopen(request) as response, open(partial, "wb") as out:
        shutil.copyfileobj(response, out)
    partial.replace(destination)
    return destination


def read_spectrum(text, label):
    """(ascending boundaries [eV], group flux [n/cm2/s]) from a CoNDERC spectrum.

    The file is a table of GROUP, UPPER, LOWER, LETHARGY, DATA, DATA/LETHARGY,
    written highest energy first and closed by a TOTAL line. Every spectrum
    carries its own boundaries, which is why no named group structure is needed
    anywhere in this benchmark: the 175-group files and the one 211-group file
    are read exactly the same way.
    """
    upper, lower, flux = [], [], []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or not parts[0].isdigit():
            continue
        upper.append(float(parts[1]))
        lower.append(float(parts[2]))
        flux.append(float(parts[4]))
    if not flux:
        raise SystemExit(f"{label}: no group data found")

    # Written top group first. Reversed, the boundaries ascend and the fluxes
    # follow them.
    for index in range(len(upper) - 1):
        if abs(lower[index] - upper[index + 1]) > 1e-6 * upper[index + 1]:
            raise SystemExit(
                f"{label}: group {index + 1} ends at {lower[index]:g} eV but "
                f"group {index + 2} starts at {upper[index + 1]:g} eV")
    boundaries = [lower[-1]] + [u for u in reversed(upper)]
    return boundaries, list(reversed(flux))


def read_reactions(text):
    """The measured effective cross sections, one dict per row."""
    rows = []
    unparsed = []
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split("\t") if field.strip()]
        if len(fields) < 4:
            continue
        name, spectrum, sigma, uncertainty = fields[:4]
        fispact_ce = float(fields[4]) if len(fields) > 4 else None
        fispact_sigma = float(fields[5]) if len(fields) > 5 else None

        match = REACTION.match(name)
        if not match:
            unparsed.append(name)
            continue
        element, mass, channel, product_element, product_mass, suffix = match.groups()
        if suffix not in ISOMER_SUFFIX:
            unparsed.append(name)
            continue

        rows.append({
            "reaction": name,
            "spectrum": spectrum,
            "target": f"{element}{mass}",
            "channel": channel,
            "mt": MT.get(channel),
            "product_element": product_element,
            "product_mass": int(product_mass),
            "product_state": suffix,
            "measured_barns": float(sigma),
            "uncertainty_barns": float(uncertainty),
            "fispact_ce": fispact_ce,
            "fispact_barns": fispact_sigma,
        })
    return rows, unparsed


def resolve_products(rows):
    """Which yani nuclide names each row's measurement covers.

    A bare product name means the total over the ground state and every isomer,
    but only the rows that have a `g` sibling prove that reading. Both come out
    the same for a product with no isomer, which is most of them, so the sum is
    applied uniformly and the reason is recorded per row.
    """
    explicit_ground = {
        (row["target"], row["channel"], row["product_element"], row["product_mass"])
        for row in rows if row["product_state"] == "g"
    }
    for row in rows:
        base = f"{row['product_element']}{row['product_mass']}"
        state = row["product_state"]
        key = (row["target"], row["channel"], row["product_element"],
               row["product_mass"])
        if state == "m":
            row["products"] = [f"{base}_m1"]
            row["product_note"] = "first metastable state"
        elif state == "n":
            row["products"] = [f"{base}_m2"]
            row["product_note"] = "second metastable state"
        elif state == "g":
            row["products"] = [base]
            row["product_note"] = "ground state only"
        else:
            row["products"] = [base, f"{base}_m1", f"{base}_m2"]
            row["product_note"] = (
                "total over ground and isomeric states"
                + (", listed alongside an explicit ground-state entry"
                   if key in explicit_ground else ""))
    return rows


def main():
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--effective-zip", type=pathlib.Path)
    parser.add_argument("--spectra-zip", type=pathlib.Path)
    parser.add_argument("-o", "--output", type=pathlib.Path,
                        default=here / "data" / "rr_data.json")
    args = parser.parse_args()

    effective = args.effective_zip or fetch(
        EFFECTIVE_URL, here / "data" / "effective.zip", "effective")
    spectra_archive = args.spectra_zip or fetch(
        SPECTRA_URL, here / "data" / "spectra.zip", "spectra")

    with zipfile.ZipFile(effective) as bundle:
        table = next(name for name in bundle.namelist() if name.endswith(".txt"))
        rows, unparsed = read_reactions(bundle.read(table).decode(errors="replace"))
    rows = resolve_products(rows)
    if unparsed:
        print(f"  {len(unparsed)} rows not understood: {' '.join(unparsed[:5])}")

    wanted = sorted({row["spectrum"] for row in rows})
    spectra, missing = {}, []
    with zipfile.ZipFile(spectra_archive) as bundle:
        # The spectrum files are named `<groups>_<name>.txt`, and the reaction
        # table names only the second half, so the group count is discovered
        # here rather than assumed.
        by_name = {}
        for member in bundle.namelist():
            if not member.endswith(".txt"):
                continue
            stem = member.rsplit("/", 1)[-1][: -len(".txt")]
            groups, _, name = stem.partition("_")
            if groups.isdigit():
                by_name[name] = member
        for name in wanted:
            if name not in by_name:
                missing.append(name)
                continue
            boundaries, flux = read_spectrum(
                bundle.read(by_name[name]).decode(errors="replace"), by_name[name])
            spectra[name] = {
                "source_file": by_name[name],
                "groups": len(flux),
                "boundaries_eV": boundaries,
                "flux_n_per_cm2_s": flux,
                "total_flux": sum(flux),
            }

    if missing:
        print(f"  no spectrum for: {' '.join(missing)}")
    usable = [row for row in rows if row["spectrum"] in spectra]

    document = {
        "description": "Measured spectrum-averaged (effective) cross sections from "
                       "the IAEA CoNDERC 'Effective RR' dataset, paired with the "
                       "neutron fields from the CoNDERC 'Spectra' dataset.",
        "sources": {"reactions": EFFECTIVE_URL, "spectra": SPECTRA_URL},
        "built_by": "build_data.py",
        "fispact_note": "fispact_barns and fispact_ce are FISPACT-II with "
                        "TENDL-2017, as published in the reaction table.",
        "spectra": spectra,
        "reactions": usable,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=1, sort_keys=True))

    by_spectrum = collections.Counter(row["spectrum"] for row in usable)
    isomeric = sum(1 for row in usable if row["product_state"] in ("m", "n"))
    size = args.output.stat().st_size / 1024
    print(f"{args.output}: {size:.0f} KB")
    print(f"  {len(usable)} reactions across {len(spectra)} spectra "
          f"({len(rows) - len(usable)} dropped for want of a spectrum)")
    print(f"  {isomeric} of them measure an isomeric state directly")
    for name, count in by_spectrum.most_common():
        print(f"  {name:22s} {count:3d} reactions, "
              f"{spectra[name]['groups']} groups")


if __name__ == "__main__":
    main()
