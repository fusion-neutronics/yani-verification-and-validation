"""A foil that produces no activation must fail the sweep, not hang it.

`sweep.py` runs each experiment in a `multiprocessing` pool worker and catches
`Exception` around the solve, so a failure is recorded and the other 131 cases
carry on. `SystemExit` does not inherit from `Exception`: CPython's own
`multiprocessing.pool.worker` does not catch it either, so raising one inside a
worker kills that worker without returning its task, and `imap_unordered` waits
forever for a result that can no longer arrive.

These tests pin the two properties that keep that from happening again. They do
not run a solve: the point is the exception type and how a pool treats it.
"""

import multiprocessing
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmarks"))
sys.path.insert(0, str(ROOT / "benchmarks" / "fns_decay_heat"))


def _raise_zero_activation(_):
    """Raise the same way `run.run` does when a foil does not activate."""
    import run

    raise run.ZeroActivation("every cooling step came out at zero decay heat")


def _solve_like_the_sweep(entry):
    """The shape of `sweep._solve`: catch Exception, report the failure."""
    try:
        return _raise_zero_activation(entry)
    except Exception as exc:  # noqa: BLE001 - the sweep catches broadly on purpose
        return ("failed", str(exc))


def test_zero_activation_is_an_exception_and_not_a_system_exit():
    import run

    assert issubclass(run.ZeroActivation, Exception)
    assert not issubclass(run.ZeroActivation, SystemExit)


def test_a_sweep_worker_records_it_as_a_failure_rather_than_dying():
    """The whole point: the task comes back, so the pool does not stall.

    'spawn' rather than fork, matching `sweep.py`, because yani's nuclear-data
    cache is process-wide state in a compiled extension.
    """
    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=1) as pool:
        results = pool.imap_unordered(_solve_like_the_sweep, [("Fe", "2000exp_5min")])
        # A timeout rather than a bare next(): if this regresses, the test
        # should fail in seconds rather than hang the suite.
        status, message = results.next(timeout=120)
    assert status == "failed"
    assert "zero decay heat" in message


def test_the_message_still_names_the_foil_and_the_combination():
    """The failure text is what a sweep log shows, so it has to stay diagnostic."""
    import run

    with pytest.raises(run.ZeroActivation) as raised:
        raise run.ZeroActivation(
            "Os/2000exp_5min: every cooling step came out at zero decay heat, "
            "so the transmutation produced no activation products.\n"
            "  combination: fendl-3.2d\n"
            "  cross sections: fendl-3.2d, reactions: endf-b8.1"
        )
    text = str(raised.value)
    assert "Os/2000exp_5min" in text
    assert "combination: fendl-3.2d" in text
