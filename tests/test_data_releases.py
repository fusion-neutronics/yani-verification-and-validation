"""A result file has to say which bytes its libraries were.

A library keyword resolves at run time to the library's current published
release, so the keyword `tendl-2017` names different data before and after a
republish. The 2026-09-08 rebuild changed every library's isomeric branching
and was invisible in every output file.

A published library is recorded as the release its solves read, the way yani
reports it (`TransmutationResults.data_releases`), and not as the newest
release in the cache: a cache holding two releases of a library is the normal
state after a republish, and a run can read the older one. A locally converted
directory records the `data_version` its conversion stamped, read best-effort,
so that has to degrade to None rather than raise.
"""

import importlib.util
import json
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from common import libraries  # noqa: E402

# TENDL-2017 cross sections, network and branching; ENDF/B-VIII.1 decay data
# and fission yields.
TENDL = libraries.BY_NAME["tendl-2017"]


def _release(name, digit="a", offline=False):
    """One library's entry in `TransmutationResults.data_releases`."""
    return {"release": name, "manifest_sha256": digit * 64,
            "format_version": 2, "offline": offline}


def test_a_provenance_stamp_is_read(tmp_path):
    (tmp_path / "provenance.json").write_text(json.dumps({"data_version": "2026-09-08"}))
    assert libraries._stamp(tmp_path) == "2026-09-08"


def test_a_version_stamp_is_read(tmp_path):
    (tmp_path / "version.json").write_text(json.dumps({"data_version": "2026-09-02"}))
    assert libraries._stamp(tmp_path) == "2026-09-02"


def test_a_missing_directory_is_not_an_error(tmp_path):
    assert libraries._stamp(tmp_path / "nope") is None


def test_an_unstamped_marker_reads_as_not_recorded(tmp_path):
    (tmp_path / "provenance.json").write_text(json.dumps({"library": "tendl-2017"}))
    assert libraries._stamp(tmp_path) is None


def test_an_empty_stamp_reads_as_not_recorded(tmp_path):
    (tmp_path / "provenance.json").write_text(json.dumps({"data_version": ""}))
    assert libraries._stamp(tmp_path) is None


def test_unreadable_json_does_not_raise(tmp_path):
    (tmp_path / "provenance.json").write_text("{not json")
    assert libraries._stamp(tmp_path) is None


def test_only_settings_read_from_local_data_carry_a_stamp():
    """A published library is recorded from the solves, so not here."""
    for combination in libraries.COMBINATIONS:
        local = [setting for setting in ("reactions", "branching", "decay",
                                         "fission_yields")
                 if getattr(combination, setting) in libraries.LOCAL_DECAY]
        assert list(libraries.local_data_versions(combination)) == local
    assert list(libraries.local_data_versions(
        libraries.BY_NAME["tendl-2017+decay-2012"])) == ["decay"]


def test_recording_provenance_never_fetches(monkeypatch):
    """`as_dict` must not download 5.5 MB and spend a minute converting it.

    `LOCAL_DECAY` maps the UKAEA decay name to `ukaea_decay.decay_directory`,
    which fetches and converts when the cache is cold. Calling it to read a
    stamp turned a metadata lookup into a network operation, which showed up as
    a CI failure rather than as a slow run only because the runner had no cache
    and no yani.
    """
    from common import ukaea_decay

    def explode(*args, **kwargs):
        raise AssertionError("provenance must not fetch or convert")

    monkeypatch.setattr(ukaea_decay, "decay_directory", explode)
    for combination in libraries.COMBINATIONS:
        recorded = libraries.as_dict(
            combination, libraries.DataReleases(combination, "out.json"))
        assert recorded["data_releases"] == {}
        assert "local_data_versions" in recorded


def test_an_unconverted_local_decay_reads_as_not_recorded(monkeypatch, tmp_path):
    from common import ukaea_decay

    monkeypatch.setenv("YANI_VV_CACHE", str(tmp_path))
    monkeypatch.setattr(ukaea_decay, "decay_directory",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("must not fetch")))
    versions = libraries.local_data_versions(
        libraries.BY_NAME["tendl-2017+decay-2012"])
    assert versions["decay"] is None


def test_a_solve_is_recorded_as_yani_reports_it():
    releases = libraries.DataReleases(TENDL, "out.json")
    read = {"endf-b8.1": _release("2026-10-10.1"),
            "tendl-2017": _release("2026-10-12.1", "b")}
    releases.read(read)
    assert releases.recorded == read


def test_a_library_the_combination_does_not_name_is_left_out():
    """yani reports every library the process has read, not just this run's."""
    releases = libraries.DataReleases(TENDL, "out.json")
    releases.read({"tendl-2017": _release("2026-10-12.1"),
                   "jeff-4.0": _release("2026-10-12.1", "c")})
    assert list(releases.recorded) == ["tendl-2017"]


def test_a_second_release_of_a_library_stops_the_run():
    releases = libraries.DataReleases(TENDL, "results/tendl-2017.json")
    releases.read({"endf-b8.1": _release("2026-10-10.1")})
    with pytest.raises(SystemExit) as stopped:
        releases.read({"endf-b8.1": _release("2026-10-12.1", "b")})
    message = str(stopped.value)
    assert "results/tendl-2017.json" in message
    assert "2026-10-10.1" in message and "2026-10-12.1" in message
    assert "--redo" in message
    assert releases.recorded["endf-b8.1"]["release"] == "2026-10-10.1"


def test_the_same_release_name_with_other_bytes_is_a_second_release():
    releases = libraries.DataReleases(TENDL, "out.json")
    releases.read({"endf-b8.1": _release("2026-10-12.1", "a")})
    with pytest.raises(SystemExit):
        releases.read({"endf-b8.1": _release("2026-10-12.1", "b")})


def test_a_release_any_solve_read_offline_is_recorded_as_offline():
    releases = libraries.DataReleases(TENDL, "out.json")
    for offline in (False, True, False):
        releases.read({"endf-b8.1": _release("2026-10-12.1", offline=offline)})
    assert releases.recorded["endf-b8.1"]["offline"] is True


def test_a_resumed_file_keeps_its_record_and_holds_to_it():
    document = {"combination": {"data_releases": {
        "endf-b8.1": _release("2026-10-10.1")}}}
    releases = libraries.DataReleases.resumed(TENDL, "out.json", document, 3)
    releases.read({"endf-b8.1": _release("2026-10-10.1")})
    assert releases.recorded == document["combination"]["data_releases"]
    with pytest.raises(SystemExit):
        releases.read({"endf-b8.1": _release("2026-10-12.1", "b")})


def test_results_that_record_no_release_cannot_be_added_to():
    """A file written before the record existed, as every yani 0.18.0 one was."""
    document = {"combination": {"data_versions": {"decay": "2026-09-18"}}}
    with pytest.raises(SystemExit) as stopped:
        libraries.DataReleases.resumed(
            TENDL, "results/tendl-2017.json", document, 132)
    assert "132 results" in str(stopped.value)
    assert "--redo" in str(stopped.value)


def test_a_file_with_no_results_starts_an_empty_record():
    assert libraries.DataReleases.resumed(TENDL, "out.json", {}, 0).recorded == {}


def _ecs_runner():
    """The effective cross-section runner, imported by path under its own name.

    The decay-heat benchmark's runner is also `run.py`, and other tests import
    that one as `run`.
    """
    spec = importlib.util.spec_from_file_location(
        "ecs_run", ROOT / "benchmarks" / "effective_cross_sections" / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _cache_release(cache, keyword, release, *paths):
    folder = cache / keyword / release
    for path in paths:
        (folder / path).mkdir(parents=True)
    (folder / "manifest.json").write_text("{}")


def test_a_result_file_records_the_release_its_solves_read(monkeypatch, tmp_path):
    """Not the newest release the cache holds, which is what it used to say.

    The cache holds two releases of ENDF/B-VIII.1, as this machine's did, and
    the solve read the older one, as a run does while the origin still points
    at it, or offline when the newer one lacks a file the run needs first.
    """
    cache = tmp_path / "cache"
    _cache_release(cache, "tendl-2017", "2026-10-12.1", "neutron",
                   "transmutation/reactions.arrow", "transmutation/branching.arrow")
    for release in ("2026-10-10.1", "2026-10-12.1"):
        _cache_release(cache, "endf-b8.1", release, "neutron",
                       "transmutation/decay.arrow",
                       "transmutation/fission_yields.arrow")
    read = {"endf-b8.1": _release("2026-10-10.1"),
            "tendl-2017": _release("2026-10-12.1", "b")}

    run = _ecs_runner()

    class Material:
        """Stands in for `yani.Material`: solves at once and reports `read`."""

        def __init__(self, composition, **_kwargs):
            (self.target,) = composition
            self.id = None

        def transmute(self, _schedule, data_uncertainty=None):
            atoms = {self.target: 1.0, "Mn56": 1.0e-8}
            final = types.SimpleNamespace(get_atoms_per_barn_cm=lambda: atoms)
            return types.SimpleNamespace(
                num_steps=1, data_releases=read,
                get_final_material=lambda _material_id: final)

    monkeypatch.setattr(run.yani, "Material", Material)
    monkeypatch.setattr(run.yani, "cache_dir", lambda: str(cache))
    monkeypatch.setattr(libraries, "apply", lambda combination, yani: None)

    data = tmp_path / "rr_data.json"
    data.write_text(json.dumps({
        "spectra": {"field": {"boundaries_eV": [1.0, 1.0e6, 2.0e7],
                              "flux_n_per_cm2_s": [1.0, 2.0]}},
        "reactions": [{"reaction": "Fe-56(n,p)Mn-56", "spectrum": "field",
                       "target": "Fe56", "products": ["Mn56"],
                       "measured_barns": 0.1, "fispact_ce": None}],
    }))
    output = tmp_path / "results"
    monkeypatch.setattr(sys, "argv", [
        "run.py", "--combination", "tendl-2017", "--data", str(data),
        "--output", str(output)])
    run.main()

    combination = json.loads((output / "tendl-2017.json").read_text())["combination"]
    assert combination["data_releases"] == read
    assert combination["local_data_versions"] == {}
