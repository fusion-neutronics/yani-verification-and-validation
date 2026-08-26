"""What a covariance run actually covered, compacted for a result file.

yani's `data_uncertainty_info` names every nuclide it perturbed and every
nuclide whose evaluation carries no covariance. That is the right shape for one
run printed to a terminal and the wrong shape for a result file: the lists run
to hundreds of names, and a sweep would repeat them once per case.

So a summary is stored instead, keeping the counts, the coverage and the list of
sources that are not propagated. The one list kept in full is the perturbed
nuclides, because it is short when it is interesting (a handful of names) and
empty when it is not.

The distinction this preserves is the one that matters: a sigma of zero because
a cross section is well known and a sigma of zero because nothing is published
are opposite statements, and a result file that recorded only the zero could not
tell them apart.
"""

# The most perturbed nuclides worth naming individually. Beyond this the count
# is the useful number and the list is noise.
NAME_LIMIT = 40


def summarise(info):
    """`data_uncertainty_info` -> a small dict, or None if there was no run."""
    if not info:
        return None

    perturbed = list(info.get("perturbed") or [])
    missing = list(info.get("no_covariance_data") or [])
    covered = info.get("rate_fraction_covered")

    summary = {
        "perturbed_count": len(perturbed),
        "no_covariance_count": len(missing),
        "has_gaps": bool(info.get("has_gaps")),
        "not_perturbed": list(info.get("not_perturbed") or []),
    }
    if len(perturbed) <= NAME_LIMIT:
        summary["perturbed"] = sorted(perturbed)

    # A dict of per-nuclide fractions collapses to its worst entry, which is the
    # one that says how much of a rate the covariance grid failed to span.
    if isinstance(covered, dict) and covered:
        nuclide, fraction = min(covered.items(), key=lambda pair: pair[1])
        summary["rate_fraction_covered_min"] = float(fraction)
        summary["rate_fraction_covered_min_nuclide"] = nuclide
    elif isinstance(covered, (int, float)):
        summary["rate_fraction_covered_min"] = float(covered)
    return summary


def describe(info, indent="             "):
    """The lines a runner prints, so both benchmarks say it the same way."""
    summary = summarise(info)
    if summary is None:
        return []

    lines = [f"covariance:  {summary['perturbed_count']} nuclide(s) perturbed, "
             f"{summary['no_covariance_count']} with none published"]
    if summary.get("perturbed"):
        lines.append(f"{indent}perturbed: {' '.join(summary['perturbed'])}")
    if "rate_fraction_covered_min" in summary:
        nuclide = summary.get("rate_fraction_covered_min_nuclide")
        tail = f" ({nuclide})" if nuclide else ""
        lines.append(f"{indent}rate coverage down to "
                     f"{summary['rate_fraction_covered_min']:.0%}{tail}")
    if summary["has_gaps"] and summary["not_perturbed"]:
        lines.append(f"{indent}not propagated: "
                     f"{', '.join(summary['not_perturbed'])}")
    return lines
