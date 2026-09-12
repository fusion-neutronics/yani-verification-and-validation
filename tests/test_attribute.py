"""The attribution's join rules and its two thresholds.

This repository has no test runner, so nothing runs these automatically yet.
They are here because the logic they cover got two things wrong on its first
pass against real data, and both were the kind of mistake that produces a
confident wrong answer rather than an error:

* reasons were reported only when a library was behind the best, so the FNS
  osmium foil, where the leader is 78% out against a measurement good to 5.6%,
  was called a win and explained nothing;
* a decay record filled from a second library no longer appears in the
  placeholder list, so the tin foil's Sn111 showed no cause at all.

    python -m pytest tests/test_attribute.py
"""

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "attribute", ROOT / "benchmarks" / "fns_decay_heat" / "attribute.py")
attribute = importlib.util.module_from_spec(_spec)
sys.modules["attribute"] = attribute
_spec.loader.exec_module(attribute)


def result(name, deviation, sigma=5.0, leaders=("Os191_m1",)):
    """One sweep document holding one experiment."""
    return {
        "combination": {"name": name},
        "results": {
            "Os/2000exp_5min": {
                "leaders": list(leaders),
                "metrics": {
                    "mean_deviation_percent": deviation,
                    "median_measurement_sigma_percent": sigma,
                },
            }
        },
    }


SURVEY = {
    "gaps": [
        {"channel": "Os190 (n,n')", "state_keV": 1705.7,
         "carried_by": ["jeff-4.0", "tendl-2025"], "omitted_by": ["tendl-2017"]},
        {"channel": "Ir191 (n,2n)", "state_keV": 376.4,
         "carried_by": ["jeff-4.0"], "omitted_by": ["tendl-2017"]},
    ]
}


def test_libraries_are_ranked_by_agreement():
    results = {"a": result("a", 9.0), "b": result("b", 3.0)}
    order = [name for _score, name, _case in
             attribute.ranking(results, "Os/2000exp_5min")]
    assert order == ["b", "a"]


def test_a_lead_inside_the_tie_threshold_is_not_a_win():
    """Half a percentage point is below what the measurement can distinguish."""
    results = {"lead": result("lead", 4.0, sigma=30.0),
               "other": result("other", 4.0 + attribute.TIE_POINTS - 0.01, sigma=30.0)}
    _lines, wins, losses = attribute.report(results, None, {}, "other")
    assert wins and not losses


def test_leading_a_poor_field_still_gets_explained():
    """The osmium case: best of three, and every one of them badly out.

    Reported because it is beyond twice the measurement's own uncertainty,
    which is the case an evaluator can act on, and the one that reporting only
    the shortfall against the best passed over in silence.
    """
    results = {"tendl-2017": result("tendl-2017", 78.0, sigma=5.6),
               "other": result("other", 79.3, sigma=5.6)}
    lines, wins, _losses = attribute.report(results, SURVEY, {}, "tendl-2017")
    text = "\n".join(lines)
    assert "every library is poor here" in text
    assert "78.0% against a measurement good to 5.6%" in text
    assert "Os190 (n,n') at 1705.7 keV" in text
    assert wins == ["Os/2000exp_5min"], "still counted as leading"


def test_a_foil_within_its_own_uncertainty_is_left_alone():
    """A measurement good to 30% cannot indict a library at 20%."""
    results = {"a": result("a", 20.0, sigma=30.0), "b": result("b", 20.1, sigma=30.0)}
    lines, _wins, _losses = attribute.report(results, SURVEY, {}, "a")
    assert "poor here" not in "\n".join(lines)


def test_only_the_omitting_library_is_told_about_a_gap():
    assert attribute.gaps_for(SURVEY, "tendl-2017", ["Os191_m1"])
    assert attribute.gaps_for(SURVEY, "jeff-4.0", ["Os191_m1"]) == []


def test_a_gap_is_matched_to_a_metastable_carrier_of_the_same_element():
    """The survey knows an energy, the results know a name, so the join is
    the element plus the carrier being metastable at all. Loose in the safe
    direction: it can suggest a gap that did not matter and cannot hide one
    that did."""
    assert attribute.gaps_for(SURVEY, "tendl-2017", ["Os189_m1"])
    # A ground-state-only carrier list has no isomer for a missing state to be.
    assert attribute.gaps_for(SURVEY, "tendl-2017", ["Re190", "Os190"]) == []
    # Another element's gap is not attributed here.
    assert not any(g["channel"].startswith("Ir")
                   for g in attribute.gaps_for(SURVEY, "tendl-2017", ["Os191_m1"]))


def test_a_placeholder_mean_energy_is_named():
    notes = attribute.decay_notes(
        {"decay_energy_placeholders": {"nuclides": ["Sn111"]}}, ["Sn111", "Sn123_m1"])
    assert "Sn111" in notes and "Q/3 placeholder" in notes["Sn111"][0]
    assert "Sn123_m1" not in notes


def test_a_filled_record_is_named_with_what_it_moved_from_and_to():
    """A build that filled its placeholders no longer lists them as such, and
    the fact a reader needs is the same: this record had no evaluated scheme."""
    notes = attribute.decay_notes(
        {"decay_energy_fill": {"library": "jendl-5.0",
                               "replaced": [{"nuclide": "Sn111",
                                             "before_eV": 1634549.4,
                                             "after_eV": 693315.8}]}},
        ["Sn111"])
    assert "1.63 MeV -> 0.69 MeV" in notes["Sn111"][0]
    assert "0.42x" in notes["Sn111"][0]
    assert "jendl-5.0" in notes["Sn111"][0]


def test_an_inconsistent_decay_record_is_named_by_kind():
    notes = attribute.decay_notes(
        {"decay_inconsistencies": {"count": 1, "isomeric_transition_energy": [
            {"nuclide": "Hf177_m1", "q_eV": 1315450.0, "recoverable_eV": 1518972.4}]}},
        ["Hf177_m1"])
    assert notes["Hf177_m1"] == ["decay record inconsistent: isomeric_transition_energy"]


def test_nothing_is_claimed_without_the_inputs_to_claim_it():
    assert attribute.gaps_for(None, "tendl-2017", ["Os191_m1"]) == []
    assert attribute.decay_notes(None, ["Sn111"]) == {}


def test_the_repository_results_load():
    """The loader has to read what sweep.py actually writes."""
    results = attribute.load_results(ROOT / "benchmarks" / "fns_decay_heat" / "results")
    assert "tendl-2017" in results, sorted(results)
    document = results["tendl-2017"]
    assert document["results"], "no experiments in the committed result file"
    case = next(iter(document["results"].values()))
    assert "mean_deviation_percent" in case["metrics"]


def test_one_library_alone_gives_no_ranking():
    """A single sweep file cannot say which library is better."""
    lines, wins, losses = attribute.report({"a": result("a", 9.0)}, SURVEY, {}, "a")
    assert lines == [] and wins == [] and losses == []


def test_a_one_letter_element_does_not_match_a_two_letter_carrier():
    """`startswith` put every one-letter symbol in front of every two-letter one.

    A gap on a carbon channel was attributed to a caesium carrier, boron to
    barium and bismuth, sulphur to tin, strontium and antimony.
    """
    for channel, carrier in [("C12 (n,p)", "Cs134_m1"),
                             ("B10 (n,a)", "Ba137_m1"),
                             ("S32 (n,p)", "Sn111"),
                             ("Y89 (n,2n)", "Yb167_m1")]:
        survey = {"gaps": [{"channel": channel, "state_keV": 0,
                            "carried_by": [], "omitted_by": ["lib"]}]}
        assert attribute.gaps_for(survey, "lib", [carrier]) == []


def test_the_real_osmium_case_still_matches():
    survey = {"gaps": [{"channel": "Os190 (n,n')", "state_keV": 1706,
                        "carried_by": ["Os190_m1"], "omitted_by": ["tendl-2017"]}]}
    assert len(attribute.gaps_for(survey, "tendl-2017", ["Os190_m1"])) == 1


def test_element_of_takes_the_whole_symbol():
    assert attribute.element_of("Cs134_m1") == "Cs"
    assert attribute.element_of("C12") == "C"
    assert attribute.element_of("Os190_m1") == "Os"
