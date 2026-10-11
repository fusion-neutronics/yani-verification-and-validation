"""A result file has to say which bytes its libraries were.

The published libraries are overwritten in place when rebuilt, so the keyword
`tendl-2017` names different data before and after a republish. The 2026-09-08
rebuild changed every library's isomeric branching and was invisible in every
output file.

A keyword records the published release it was read from, the folder yani
caches it under (`<cache>/<keyword>/<release>/`); a locally converted directory
records the `data_version` its conversion stamped. Both are read best-effort,
so they have to degrade to None rather than raise.
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))

from common import libraries  # noqa: E402


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


def test_every_combination_reports_all_five_settings():
    for combination in libraries.COMBINATIONS:
        recorded = libraries.as_dict(combination)["data_versions"]
        assert set(recorded) == {"cross_sections", "reactions", "branching",
                                 "decay", "fission_yields"}


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
        recorded = libraries.as_dict(combination)
        assert "data_versions" in recorded


def test_an_unconverted_local_decay_reads_as_not_recorded(monkeypatch, tmp_path):
    from common import ukaea_decay

    monkeypatch.setenv("YANI_VV_CACHE", str(tmp_path))
    monkeypatch.setattr(ukaea_decay, "decay_directory",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("must not fetch")))
    versions = libraries.data_versions(
        libraries.BY_NAME["tendl-2017+decay-2012"])
    assert versions["decay"] is None


def _release(root, keyword, release, *paths):
    folder = root / keyword / release
    folder.mkdir(parents=True)
    (folder / "manifest.json").write_text("{}")
    for path in paths:
        (folder / path).mkdir(parents=True)
    return folder


def test_a_keyword_records_its_newest_cached_release(tmp_path):
    _release(tmp_path, "tendl-2017", "2026-10-01", "transmutation/reactions.arrow")
    _release(tmp_path, "tendl-2017", "2026-10-15.1", "transmutation/reactions.arrow")
    assert libraries._cached_release(
        tmp_path, "tendl-2017", "transmutation/reactions.arrow") == "2026-10-15.1"


def test_a_release_without_the_data_is_passed_over(tmp_path):
    _release(tmp_path, "endf-b8.1", "2026-10-01", "transmutation/decay.arrow")
    _release(tmp_path, "endf-b8.1", "2026-10-15.1", "neutron")
    assert libraries._cached_release(
        tmp_path, "endf-b8.1", "transmutation/decay.arrow") == "2026-10-01"
    assert libraries._cached_release(tmp_path, "endf-b8.1", "neutron") == "2026-10-15.1"


def test_a_folder_without_a_manifest_is_not_a_release(tmp_path):
    (tmp_path / "endf-b8.1" / "2026-10-15.1" / "neutron").mkdir(parents=True)
    assert libraries._cached_release(tmp_path, "endf-b8.1", "neutron") is None


def test_an_uncached_keyword_reads_as_not_recorded(tmp_path):
    assert libraries._cached_release(tmp_path, "jeff-4.0", "neutron") is None
