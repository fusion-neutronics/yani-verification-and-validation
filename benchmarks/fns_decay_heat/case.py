"""Loading one FNS experiment, and scoring a calculation against it.

Everything about a case -- composition, density, mass, flux, spectrum, the
cooling schedule and the measurement -- comes from `data/fns_data.json`, which
`build_data.py` derives from the IAEA archive. Nothing here reaches the network.
"""

import json
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_DATA = HERE / "data" / "fns_data.json"

GROUPS = 709
GROUP_STRUCTURE = "CCFE-709"

# The measured times are in whichever of these the benchmark stated per case.
UNIT_SECONDS = {"minutes": 60.0, "hours": 3600.0, "days": 86400.0}

# The temperature the FNS foils sat at. Room temperature; the benchmark does not
# state one, and at 14 MeV the Doppler width of anything that matters is
# irrelevant next to the measurement uncertainty.
TEMPERATURE = 294.0

_CACHE = {}


def _document(path=None):
    path = pathlib.Path(path) if path else DEFAULT_DATA
    key = str(path)
    if key not in _CACHE:
        if not path.is_file():
            raise SystemExit(
                f"no benchmark data at {path}. Run build_data.py to derive it from "
                f"the IAEA archive."
            )
        _CACHE[key] = json.loads(path.read_text())
    return _CACHE[key]


class Case:
    """One foil in one FNS campaign."""

    def __init__(self, name, experiment, entry, spectrum):
        self.name = name
        self.experiment = experiment
        self.composition = entry["composition_mass_fraction"]
        self.density = entry["density_g_per_cm3"]
        self.mass_g = entry["mass_g"]
        self.irradiation = entry["irradiation_s_and_flux"]
        self.position = entry["position"]
        self.time_unit = entry["time_unit"]
        self.spectrum = np.array(spectrum, dtype=float)
        self.times = np.array(entry["times"], dtype=float)
        self.measured = np.array(entry["measured_uW_per_g"], dtype=float)
        self.uncertainty = np.array(entry["uncertainty_uW_per_g"], dtype=float)
        self.fispact = (np.array(entry["fispact_uW_per_g"], dtype=float)
                        if entry.get("fispact_uW_per_g") else None)
        self.fispact_library = entry.get("fispact_library")

    @property
    def times_seconds(self):
        return self.times * UNIT_SECONDS[self.time_unit]

    @property
    def cooling_steps(self):
        """Seconds between measured points, so the solve lands on each of them.

        The benchmark's own cooling schedule is not used: stepping to the
        measured times makes the comparison exact at every point, and a few
        decks drift from their measurement by a second or two.
        """
        steps, previous = [], 0.0
        for time in self.times_seconds:
            steps.append(time - previous)
            previous = time
        return steps

    def describe(self):
        elements = " ".join(
            f"{element} {fraction * 100:.4g}%"
            for element, fraction in sorted(self.composition.items())
        )
        irradiation = sum(seconds for seconds, _ in self.irradiation)
        return (f"{self.name} ({elements}), {self.mass_g:g} g at "
                f"{self.density:g} g/cm3, {irradiation:g} s irradiation, "
                f"{len(self.times)} measured points, position {self.position}")


def load(name, experiment=None, path=None):
    document = _document(path)
    if name not in document["cases"]:
        raise SystemExit(f"no foil {name!r}. Known: {' '.join(sorted(document['cases']))}")
    entries = document["cases"][name]
    if experiment is None:
        # The 2000 campaign is the only one covering every foil.
        experiment = "2000exp_5min" if "2000exp_5min" in entries else sorted(entries)[0]
    if experiment not in entries:
        raise SystemExit(
            f"{name} has no {experiment!r}. Known: {' '.join(sorted(entries))}")
    entry = entries[experiment]
    return Case(name, experiment, entry,
                document["spectra_by_position"][entry["position"]])


def cases(path=None):
    return sorted(_document(path)["cases"])


def experiments(name, path=None):
    return sorted(_document(path)["cases"][name])


def every(path=None):
    """(foil, experiment) for all 132 experiments."""
    document = _document(path)
    return [(name, experiment)
            for name in sorted(document["cases"])
            for experiment in sorted(document["cases"][name])]


def score(calculated, case, calculated_sigma=None):
    """How a calculated curve compares with the measurement.

    `mean_deviation_percent` is the headline: the average of |C/E - 1| over the
    measured points. It is preferred to a median C/E because a curve that runs
    high early and low late can hold a median C/E of 1.000 while matching
    nothing, and because the quantity being judged is agreement rather than
    bias. Both are reported.

    `calculated_sigma` is the nuclear-data standard deviation on the calculated
    curve, in the same units, when the run asked for one. Given it, the
    agreement test becomes |C - E| <= sqrt(sigmaC^2 + sigmaE^2) rather than
    |C - E| <= sigmaE, which is the question worth asking once both sides carry
    an error bar: a point can sit outside the measurement uncertainty and still
    be consistent, if the data it was calculated from is poorly known.

    `points_within_sigma` keeps its old meaning either way, so the two
    columns can be read against each other.
    """
    calculated = np.asarray(calculated, dtype=float)
    measured = case.measured
    usable = measured > 0
    ratio = np.divide(calculated, measured,
                      out=np.full(calculated.shape, np.nan), where=usable)
    sigma = np.divide(case.uncertainty, measured,
                      out=np.full(measured.shape, np.nan), where=usable)
    # A calculation of zero scores 100% under |C/E - 1| and cannot score worse,
    # while one that is a factor of two high scores 100% and one a factor of
    # ten high scores 900%. The metric is therefore bounded below and unbounded
    # above, and it rewards whichever code runs lower. |ln C/E| is the
    # symmetric counterpart: a factor of two either way scores the same.
    #
    # Both are reported because the ordering between two codes can depend on
    # which is used. On the 130 experiments carrying a FISPACT-II curve, yani
    # is at 10.57% against 10.68% under |C/E - 1| and at 10.81% against 10.64%
    # under |ln C/E|. Neither difference is real; quoting only the first would
    # make it look as though one were.
    positive = usable & (calculated > 0)
    log_ratio = np.log(np.divide(calculated, measured,
                                 out=np.full(calculated.shape, np.nan),
                                 where=positive),
                       out=np.full(calculated.shape, np.nan), where=positive)

    # The same score over the points the measurement actually constrains. 82 of
    # the 2378 measured points carry a quoted uncertainty above half their own
    # value and 118 are not three sigma above zero, and whole experiments
    # consist of nothing else, so a mean over every point is partly a mean over
    # noise.
    constrained = usable & (case.uncertainty < 0.25 * measured)

    metrics = {
        "ratio": ratio.tolist(),
        "median_ratio": float(np.nanmedian(ratio)),
        "mean_deviation_percent": float(np.nanmean(np.abs(ratio - 1.0)) * 100.0),
        "mean_log_deviation_percent": (
            float(np.nanmean(np.abs(log_ratio)) * 100.0)
            if positive.any() else float("nan")),
        "max_deviation_percent": float(np.nanmax(np.abs(ratio - 1.0)) * 100.0),
        "median_measurement_sigma_percent": float(np.nanmedian(sigma) * 100.0),
        "points_within_sigma": int(np.nansum(np.abs(ratio - 1.0) <= sigma)),
        "points": int(usable.sum()),
        # How much of the experiment is worth scoring at all.
        "points_constrained": int(constrained.sum()),
        "mean_deviation_constrained_percent": (
            float(np.nanmean(np.abs(ratio[constrained] - 1.0)) * 100.0)
            if constrained.any() else float("nan")),
    }

    if calculated_sigma is not None:
        calculated_sigma = np.asarray(calculated_sigma, dtype=float)
        # Combined in absolute terms and then divided through, so a measured
        # zero drops out the same way it does above.
        combined = np.hypot(calculated_sigma, case.uncertainty)
        relative = np.divide(combined, measured,
                             out=np.full(measured.shape, np.nan), where=usable)
        calculated_relative = np.divide(
            calculated_sigma, calculated,
            out=np.full(calculated.shape, np.nan), where=calculated > 0)
        metrics.update({
            "calculated_sigma": calculated_sigma.tolist(),
            "median_calculated_sigma_percent":
                float(np.nanmedian(calculated_relative) * 100.0),
            "max_calculated_sigma_percent":
                float(np.nanmax(calculated_relative) * 100.0),
            "points_within_combined_sigma":
                int(np.nansum(np.abs(ratio - 1.0) <= relative)),
        })
    return metrics
