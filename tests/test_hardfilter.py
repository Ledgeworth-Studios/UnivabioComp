"""Tests for the deterministic age / sex / healthy-volunteer filters.

The trials used here are real records, recorded by `tools/record_fixtures.py`
precisely because between them they cover every age-bound shape the registry
actually emits: hours, days, weeks, months, years, missing minimums, missing
maximums, and no bounds at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from whynot.hardfilter import (
    UnparseableAge,
    Verdict,
    check_age,
    check_healthy_volunteers,
    check_sex,
    describe_age_range,
    hard_filter,
    parse_age_to_years,
)
from whynot.profile import PatientProfile
from whynot.registry import Eligibility, parse_study

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"


@pytest.fixture(scope="module")
def shapes() -> dict:
    """The eleven hand-picked real trials, keyed by NCT id."""
    payload = json.loads((FIXTURE_DIR / "age_and_sex_shapes.json").read_text())
    return {parse_study(s).nct_id: parse_study(s) for s in payload["studies"]}


def eligibility(**overrides) -> Eligibility:
    """A blank eligibility record with only the fields a test cares about set."""
    base = {
        "criteria_text": "",
        "minimum_age": None,
        "maximum_age": None,
        "sex": "ALL",
        "healthy_volunteers": None,
        "std_ages": (),
    }
    return Eligibility(**{**base, **overrides})


# --------------------------------------------------------------------------
# Age string parsing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected_years"),
    [
        ("18 Years", 18.0),
        ("1 Year", 1.0),
        ("6 Months", 0.5),
        ("24 Months", 2.0),
        ("5 Weeks", 5 * 7 / 365.25),
        ("30 Days", 30 / 365.25),
        ("72 Hours", 72 / (24 * 365.25)),
        ("120 Years", 120.0),
    ],
)
def test_registry_age_strings_convert_to_years(text, expected_years):
    assert parse_age_to_years(text) == pytest.approx(expected_years)


def test_an_absent_bound_is_none_not_zero():
    assert parse_age_to_years(None) is None
    assert parse_age_to_years("") is None


def test_an_unreadable_age_raises_rather_than_guessing():
    with pytest.raises(UnparseableAge):
        parse_age_to_years("adult")


def test_every_age_bound_in_the_fixtures_is_readable(shapes):
    for study in shapes.values():
        parse_age_to_years(study.eligibility.minimum_age)
        parse_age_to_years(study.eligibility.maximum_age)


def test_describe_age_range_quotes_the_registry_wording():
    assert describe_age_range(eligibility(minimum_age="18 Years")) == "18 Years and older"
    assert describe_age_range(eligibility(maximum_age="2 Years")) == "up to 2 Years"
    assert (
        describe_age_range(eligibility(minimum_age="6 Months", maximum_age="18 Years"))
        == "6 Months to 18 Years"
    )
    assert describe_age_range(eligibility()) == "no age limits stated"


# --------------------------------------------------------------------------
# Age decisions on real records
# --------------------------------------------------------------------------


def test_a_trial_with_no_age_bounds_never_excludes_on_age(shapes):
    # NCT02138032 states neither a minimum nor a maximum.
    study = shapes["NCT02138032"]
    check = check_age(study.eligibility, PatientProfile(age_years=40))
    assert check.verdict is Verdict.MET


def test_a_maximum_only_trial_excludes_an_adult(shapes):
    # NCT01271491 is "up to 2 Years" with no minimum.
    study = shapes["NCT01271491"]
    check = check_age(study.eligibility, PatientProfile(age_years=40))
    assert check.verdict is Verdict.NOT_MET
    assert "2 Years" in check.reason


def test_a_maximum_only_trial_admits_an_infant(shapes):
    study = shapes["NCT01271491"]
    assert check_age(study.eligibility, PatientProfile(age_years=0.5)).verdict is Verdict.MET


def test_a_minimum_expressed_in_months_is_compared_correctly(shapes):
    # NCT00157079 is "24 Months and older" — an adult qualifies, an infant does not.
    study = shapes["NCT00157079"]
    assert check_age(study.eligibility, PatientProfile(age_years=40)).verdict is Verdict.MET
    assert check_age(study.eligibility, PatientProfile(age_years=1)).verdict is Verdict.NOT_MET


def test_mixed_units_are_compared_on_the_same_scale(shapes):
    # NCT06737159 runs from 5 Weeks to 24 Months.
    study = shapes["NCT06737159"]
    six_weeks = 6 * 7 / 365.25
    assert check_age(study.eligibility, PatientProfile(age_years=six_weeks)).verdict is Verdict.MET
    three_weeks = 3 * 7 / 365.25
    assert (
        check_age(study.eligibility, PatientProfile(age_years=three_weeks)).verdict
        is Verdict.NOT_MET
    )
    assert check_age(study.eligibility, PatientProfile(age_years=3)).verdict is Verdict.NOT_MET


def test_bounds_measured_in_hours_still_work(shapes):
    # NCT02210026 is 6 Hours to 72 Hours old.
    study = shapes["NCT02210026"]
    two_days = 2 / 365.25
    assert check_age(study.eligibility, PatientProfile(age_years=two_days)).verdict is Verdict.MET
    assert check_age(study.eligibility, PatientProfile(age_years=40)).verdict is Verdict.NOT_MET


def test_the_bounds_are_inclusive(shapes):
    # NCT00132080 runs 6 Months to 18 Years. Someone who is exactly 18 is in.
    study = shapes["NCT00132080"]
    assert check_age(study.eligibility, PatientProfile(age_years=18)).verdict is Verdict.MET
    assert check_age(study.eligibility, PatientProfile(age_years=0.5)).verdict is Verdict.MET
    assert check_age(study.eligibility, PatientProfile(age_years=18.5)).verdict is Verdict.NOT_MET


def test_an_unstated_age_is_unknown_not_excluded(shapes):
    """The failure this project cares most about: never turn silence into a rejection."""
    study = shapes["NCT00132080"]
    check = check_age(study.eligibility, PatientProfile(age_years=None))
    assert check.verdict is Verdict.UNKNOWN
    assert "didn't tell us your age" in check.reason


def test_an_unreadable_age_bound_is_unknown_not_excluded():
    check = check_age(eligibility(minimum_age="adult"), PatientProfile(age_years=40))
    assert check.verdict is Verdict.UNKNOWN


# --------------------------------------------------------------------------
# Sex
# --------------------------------------------------------------------------


def test_a_female_only_trial_excludes_a_man(shapes):
    study = shapes["NCT07000786"]  # FEMALE
    assert study.eligibility.sex == "FEMALE"
    assert check_sex(study.eligibility, PatientProfile(sex="man")).verdict is Verdict.NOT_MET
    assert check_sex(study.eligibility, PatientProfile(sex="Female")).verdict is Verdict.MET


def test_a_male_only_trial_excludes_a_woman(shapes):
    study = shapes["NCT02706561"]  # MALE
    assert check_sex(study.eligibility, PatientProfile(sex="F")).verdict is Verdict.NOT_MET
    assert check_sex(study.eligibility, PatientProfile(sex="male")).verdict is Verdict.MET


def test_an_all_sexes_trial_never_excludes():
    assert check_sex(eligibility(sex="ALL"), PatientProfile(sex=None)).verdict is Verdict.MET


def test_an_unstated_sex_against_a_restricted_trial_is_unknown(shapes):
    check = check_sex(shapes["NCT07000786"].eligibility, PatientProfile(sex=None))
    assert check.verdict is Verdict.UNKNOWN


def test_a_sex_we_do_not_recognise_is_unknown_not_excluded(shapes):
    """We do not try to interpret how someone describes themselves."""
    check = check_sex(shapes["NCT07000786"].eligibility, PatientProfile(sex="intersex"))
    assert check.verdict is Verdict.UNKNOWN


# --------------------------------------------------------------------------
# Healthy volunteers
# --------------------------------------------------------------------------


def test_a_trial_accepting_healthy_volunteers_never_excludes():
    check = check_healthy_volunteers(
        eligibility(healthy_volunteers=True), PatientProfile(is_healthy_volunteer=True)
    )
    assert check.verdict is Verdict.MET


def test_a_declared_healthy_volunteer_is_excluded_from_a_patients_only_trial():
    check = check_healthy_volunteers(
        eligibility(healthy_volunteers=False), PatientProfile(is_healthy_volunteer=True)
    )
    assert check.verdict is Verdict.NOT_MET


def test_not_accepting_healthy_volunteers_does_not_exclude_a_patient():
    check = check_healthy_volunteers(
        eligibility(healthy_volunteers=False), PatientProfile(is_healthy_volunteer=False)
    )
    assert check.verdict is Verdict.MET


def test_an_unstated_healthy_volunteer_field_is_unknown():
    check = check_healthy_volunteers(eligibility(healthy_volunteers=None), PatientProfile())
    assert check.verdict is Verdict.UNKNOWN


# --------------------------------------------------------------------------
# The three together
# --------------------------------------------------------------------------


def test_hard_filter_runs_all_three_checks(shapes):
    result = hard_filter(shapes["NCT07000786"], PatientProfile(age_years=30, sex="female"))
    assert [c.field for c in result.checks] == ["age", "sex", "healthy volunteers"]
    assert not result.is_ruled_out


def test_a_ruled_out_person_gets_a_reason_they_can_read(shapes):
    result = hard_filter(shapes["NCT07000786"], PatientProfile(age_years=70, sex="male"))
    assert result.is_ruled_out
    assert len(result.blocking_reasons) == 2
    assert all(reason.endswith(".") for reason in result.blocking_reasons)


def test_an_empty_profile_produces_questions_and_no_rejections(shapes):
    """Rigor rule: telling us nothing must never rule you out of anything."""
    empty = PatientProfile()
    for study in shapes.values():
        result = hard_filter(study, empty)
        assert not result.is_ruled_out, f"{study.nct_id} rejected a person who said nothing"


def test_every_check_carries_the_registry_text_it_came_from(shapes):
    """Rigor rule 2: every reason is traceable to a registry field."""
    result = hard_filter(shapes["NCT00132080"], PatientProfile(age_years=10, sex="female"))
    for check in result.checks:
        assert check.source
        assert check.reason
