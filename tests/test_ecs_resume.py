"""A reaction is either solved or failed in a result file, never both.

The effective cross-section runner resumes from its own output: a reaction
already in `results` is skipped and everything else, earlier failures
included, is tried again. A retry that succeeded used to be appended to
`results` while its old entry stayed in `failures`, so the file listed the
reaction twice, once as a number and once as an error, and the run's own
summary counted it among the failures. The decay-heat sweep drops the failure
when the retry succeeds, and these pin the same for this runner.

They drive the real `main()` with a stand-in for `yani.Material`, so they read
no nuclear data and take milliseconds.
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

FIELD = "test-field"
REACTIONS = {
    "Fe-56(n,p)Mn-56": ("Fe56", "Mn56"),
    "Al-27(n,a)Na-24": ("Al27", "Na24"),
}


def _runner():
    """The runner, imported by path under a name of its own.

    The decay-heat benchmark's runner is also `run.py`, and the other tests
    import that one as `run`.
    """
    spec = importlib.util.spec_from_file_location(
        "ecs_run", ROOT / "benchmarks" / "effective_cross_sections" / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Material:
    """Stands in for `yani.Material`: solves at once, and fails when told to."""

    # Targets whose next solve raises, the way a dropped connection does.
    failing = set()

    def __init__(self, composition, **_kwargs):
        (self.target,) = composition
        self.id = None

    def transmute(self, _schedule, data_uncertainty=None):
        if self.target in _Material.failing:
            _Material.failing.discard(self.target)
            raise RuntimeError(f"connection reset while reading {self.target}")
        atoms = {self.target: 1.0}
        atoms.update({product: 1.0e-8 for _, product in REACTIONS.values()})
        final = types.SimpleNamespace(get_atoms_per_barn_cm=lambda: atoms)
        return types.SimpleNamespace(
            num_steps=1,
            data_releases={},
            get_final_material=lambda _material_id: final,
        )


@pytest.fixture
def ecs(monkeypatch, tmp_path):
    """The runner wired to the stand-in, a two-reaction archive and an output."""
    run = _runner()
    monkeypatch.setattr(run.yani, "Material", _Material)
    # The library settings and their provenance are not under test, and
    # neither should touch yani's process state or its cache from here.
    monkeypatch.setattr(libraries, "apply", lambda combination, yani: None)
    monkeypatch.setattr(libraries, "as_dict",
                        lambda combination: {"name": combination.name})
    _Material.failing = set()

    data = tmp_path / "rr_data.json"
    data.write_text(json.dumps({
        "spectra": {FIELD: {"boundaries_eV": [1.0, 1.0e6, 2.0e7],
                            "flux_n_per_cm2_s": [1.0, 2.0]}},
        "reactions": [
            {"reaction": reaction, "spectrum": FIELD, "target": target,
             "products": [product], "measured_barns": 0.1, "fispact_ce": None}
            for reaction, (target, product) in REACTIONS.items()
        ],
    }))
    output = tmp_path / "results"

    def main():
        monkeypatch.setattr(sys, "argv", [
            "run.py", "--data", str(data), "--output", str(output)])
        run.main()
        return json.loads((output / f"{libraries.APPLES_TO_APPLES_ECS}.json")
                          .read_text())

    main.output = output
    return main


def _key(reaction):
    return f"{reaction} @ {FIELD}"


def test_a_retry_that_succeeds_is_a_result_and_not_a_failure(ecs, capsys):
    _Material.failing = {"Al27"}
    first = ecs()
    assert [row["reaction"] for row in first["results"]] == ["Fe-56(n,p)Mn-56"]
    assert list(first["failures"]) == [_key("Al-27(n,a)Na-24")]
    capsys.readouterr()

    # The resumed run retries only the failure, and this time it solves.
    second = ecs()
    assert sorted(row["reaction"] for row in second["results"]) == sorted(REACTIONS)
    assert second["failures"] == {}
    summary = [line for line in capsys.readouterr().out.splitlines()
               if " reactions in " in line]
    assert summary[-1].startswith("2 reactions in ")
    assert summary[-1].endswith(", 0 failed")


def test_a_retry_that_fails_again_stays_a_failure(ecs):
    _Material.failing = {"Al27"}
    ecs()
    _Material.failing = {"Al27"}
    again = ecs()
    assert [row["reaction"] for row in again["results"]] == ["Fe-56(n,p)Mn-56"]
    assert list(again["failures"]) == [_key("Al-27(n,a)Na-24")]


def test_a_resumed_file_sheds_failures_its_results_already_answer(ecs):
    """A file the old runner wrote is put right on the next resume.

    Its solved reactions are never retried, so the failure it kept beside each
    of them would otherwise stay in the file until a `--redo`.
    """
    solved = ecs()
    destination = ecs.output / f"{libraries.APPLES_TO_APPLES_ECS}.json"
    solved["failures"] = {_key("Fe-56(n,p)Mn-56"): "connection reset"}
    destination.write_text(json.dumps(solved))

    resumed = ecs()
    assert len(resumed["results"]) == len(REACTIONS)
    assert resumed["failures"] == {}
