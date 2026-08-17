#!/usr/bin/env python3
"""Trim an OpenMC cross_sections.xml to the data files that are actually present.

    python tools/openmc_subset_library.py /path/to/endfb-viii.1-hdf5

OpenMC's HDF5 libraries are large -- ENDF/B-VIII.1 is about 9.7 GB compressed
and considerably more unpacked -- and a machine that cannot hold one can still
run these benchmarks on a subset of foils by unpacking only the nuclides those
foils need:

    tar -xJf endfb81.tar.xz --wildcards \\
        'endfb-viii.1-hdf5/cross_sections.xml' \\
        'endfb-viii.1-hdf5/neutron/Fe5*.h5'

The index that comes out of that still lists every nuclide in the full library,
including the several thousand whose files were not unpacked.
`MicroXS.from_multigroup_flux` reads the index to decide which nuclides it has
data for, then asks OpenMC to load each one, so it would fail on the first
absent file. This rewrites the index to list only what is there.

## Is a subset a valid calculation

For these benchmarks, yes, and the reason is worth stating rather than
assuming. The FNS foils are irradiated for 5 minutes or 7.6 hours at about
1e10 n/cm2/s, so the fluence is around 1e13 to 1e14 n/cm2. At that fluence the
burnup of an activation product is of order sigma*phi*t, roughly 1e-10, so
whether the code has cross sections for the *products* changes the answer in
about the tenth decimal place. What has to be present is the foil's own
isotopes, which set the production rates.

`MicroXS` gives a nuclide with no data a cross section of exactly zero rather
than failing, which is the right behaviour here and the wrong behaviour to rely
on silently: the report at the end says how many chain nuclides ended up with
no data, so the omission is visible.

For a full run, unpack the whole library and skip this entirely.
"""

import argparse
import pathlib
import shutil
import xml.etree.ElementTree as ElementTree


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("library", type=pathlib.Path,
                        help="the unpacked library directory, holding "
                             "cross_sections.xml")
    parser.add_argument("--output", type=pathlib.Path,
                        help="where to write the trimmed index "
                             "(default: cross_sections_subset.xml beside it)")
    args = parser.parse_args()

    index = args.library / "cross_sections.xml"
    if not index.is_file():
        raise SystemExit(f"no cross_sections.xml in {args.library}")
    destination = args.output or args.library / "cross_sections_subset.xml"

    # Keep the original: it is the library's own file, and a run that later
    # unpacks the rest should find it unmodified.
    backup = args.library / "cross_sections_full.xml"
    if not backup.is_file():
        shutil.copyfile(index, backup)

    tree = ElementTree.parse(index)
    root = tree.getroot()

    kept, dropped = [], []
    for entry in list(root.findall("library")):
        path = entry.get("path")
        if path and (args.library / path).is_file():
            kept.append(entry.get("materials"))
        else:
            root.remove(entry)
            dropped.append(entry.get("materials"))

    tree.write(destination, encoding="utf-8", xml_declaration=True)
    print(f"{destination}")
    print(f"  {len(kept)} nuclides present, {len(dropped)} listed but absent")
    print(f"  kept: {' '.join(sorted(n for n in kept if n))}")
    print()
    print(f"export OPENMC_CROSS_SECTIONS={destination}")


if __name__ == "__main__":
    main()
