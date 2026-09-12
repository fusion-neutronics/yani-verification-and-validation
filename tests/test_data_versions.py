"""A result file has to say which bytes its libraries were.

The published libraries are overwritten in place when rebuilt, so the keyword
`tendl-2017` names different data before and after a republish. The 2026-09-08
rebuild changed every library's isomeric branching and was invisible in every
output file.

`_stamp` is the part worth pinning: reading the cache layout is best-effort, so
it has to degrade to None rather than raise.
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
