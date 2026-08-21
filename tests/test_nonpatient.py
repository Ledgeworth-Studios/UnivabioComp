"""Tests for detecting trials that enrol organisations rather than people.

The test that matters most is `test_no_ordinary_patient_trial_is_flagged`. A
false positive tells somebody a study is not for people when it is, and they
never call — the same shape of harm as a `NOT_MET` that should have been
`UNKNOWN`. Everything else here is in service of not doing that.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from whynot.nonpatient import CAUTION, assess
from whynot.registry import Eligibility, Study, parse_study

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"


def load_study(name: str) -> Study:
    return parse_study(json.loads((FIXTURE_DIR / name).read_text()))


def make_study(*, criteria: str = "", primary_purpose: str | None = "TREATMENT") -> Study:
    return Study(
        nct_id="NCT00000001",
        brief_title="A study",
        official_title=None,
        overall_status="RECRUITING",
        status_verified_date=None,
        last_update_post_date=None,
        study_type="INTERVENTIONAL",
        primary_purpose=primary_purpose,
        phases=("PHASE3",),
        enrollment_count=None,
        conditions=(),
        lead_sponsor=None,
        eligibility=Eligibility(
            criteria_text=criteria,
            minimum_age="18 Years",
            maximum_age=None,
            sex="ALL",
            healthy_volunteers=True,
            std_ages=(),
        ),
        locations=(),
    )


# --------------------------------------------------------------------------
# The verified example from docs/PLAN.md
# --------------------------------------------------------------------------


def test_the_verified_non_patient_trial_is_flagged_with_its_evidence() -> None:
    """`NCT06251323` enrols federally qualified health centres, not people."""
    study = load_study("study_NCT06251323.json")
    result = assess(study)

    assert result.looks_like_organisations is True
    assert len(result.signals) >= 2

    names = {signal.name for signal in result.signals}
    assert "purpose" in names
    assert "organisation named in the criteria" in names

    # Every signal shows its working.
    for signal in result.signals:
        assert signal.explanation
        assert signal.quote, f"{signal.name} produced no quotable evidence"

    quotes = " ".join(s.quote or "" for s in result.signals).lower()
    assert "fqhc" in quotes or "clinic site" in quotes


def test_that_trial_looks_perfectly_ordinary_in_its_structured_fields() -> None:
    """Why this task exists: nothing above the criteria text gives it away.

    If this ever starts failing it means the registry added a field that says so
    outright, and the text heuristics below could be replaced by it.
    """
    study = load_study("study_NCT06251323.json")

    assert study.eligibility.minimum_age == "18 Years"
    assert study.eligibility.sex == "ALL"
    assert study.eligibility.healthy_volunteers is True
    assert "diabetes" in study.brief_title.lower()


# --------------------------------------------------------------------------
# The failure mode that matters
# --------------------------------------------------------------------------


def test_no_ordinary_patient_trial_is_flagged() -> None:
    """Every study in the recorded Portland MS search must come back unflagged."""
    payload = json.loads((FIXTURE_DIR / "search_ms_portland.json").read_text())
    studies = [parse_study(raw) for raw in payload["studies"]]
    assert studies, "the fixture should contain studies"

    for study in studies:
        result = assess(study)
        assert result.looks_like_organisations is False, (
            f"{study.nct_id} was wrongly flagged as not enrolling people: "
            f"{[s.name for s in result.signals]}"
        )


@pytest.mark.parametrize(
    "criteria",
    [
        "Inclusion Criteria:\n* Currently hospitalised for an acute exacerbation",
        "Inclusion Criteria:\n* Able to attend the study site for all visits",
        "Exclusion Criteria:\n* Resident in a nursing home at the time of screening",
        "Inclusion Criteria:\n* Referred by a physician practice in the region",
    ],
)
def test_one_organisation_sounding_phrase_is_never_enough(criteria: str) -> None:
    """Ordinary patient criteria mention buildings and practices all the time."""
    assert assess(make_study(criteria=criteria)).looks_like_organisations is False


def test_health_services_research_alone_is_not_enough() -> None:
    """Plenty of health services research does enrol patients."""
    study = make_study(
        primary_purpose="HEALTH_SERVICES_RESEARCH",
        criteria="Inclusion Criteria:\n* Adults aged 18 or over with type 2 diabetes",
    )
    result = assess(study)

    assert len(result.signals) == 1
    assert result.looks_like_organisations is False


def test_a_study_with_no_criteria_text_is_never_flagged() -> None:
    assert assess(make_study(criteria="")).looks_like_organisations is False


# --------------------------------------------------------------------------
# Corroboration
# --------------------------------------------------------------------------


def test_two_signals_from_the_text_alone_are_enough() -> None:
    """Purpose is not required — the criteria can corroborate themselves."""
    study = make_study(
        primary_purpose="PREVENTION",
        criteria=(
            "Inclusion Criteria:\n"
            "* Primary care practices with at least three clinicians\n"
            "Exclusion Criteria:\n"
            "* Practices whose patient population is more than 80% children"
        ),
    )
    result = assess(study)

    assert result.looks_like_organisations is True
    assert {s.name for s in result.signals} == {
        "organisation named in the criteria",
        "criteria written about a population",
    }


def test_each_kind_of_signal_is_counted_once() -> None:
    """Ten mentions of clinics is still one reason to think this, not ten."""
    study = make_study(
        criteria="Inclusion Criteria:\n* health centers, health systems and clinic sites"
    )
    result = assess(study)

    assert len(result.signals) == 1


# --------------------------------------------------------------------------
# What it is allowed to say
# --------------------------------------------------------------------------


def test_the_caution_is_worded_as_a_possibility_and_points_at_the_study_team() -> None:
    """Rigor rule 1. We are guessing, and the wording has to admit it."""
    lowered = CAUTION.lower()

    assert "may not be" in lowered
    assert "we could be wrong" in lowered
    assert "study team" in lowered
    for claim in ("is not for patients", "you cannot join", "you are not eligible"):
        assert claim not in lowered
