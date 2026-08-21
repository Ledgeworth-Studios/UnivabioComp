"""Tests for the coordinator questions.

The load-bearing behaviour is the split: an `UNKNOWN` the person can resolve
themselves must never turn into a question for a research nurse, and an `UNKNOWN`
only the study team can resolve must never be silently dropped.
"""

from __future__ import annotations

import pytest

from whynot.hardfilter import HardCheck, Verdict, hard_filter
from whynot.profile import PatientProfile
from whynot.questions import (
    SELF_ANSWERABLE_FIELDS,
    open_questions,
    person_could_answer,
    question_for,
)
from whynot.registry import Eligibility, Study

KNOWS_EVERYTHING = PatientProfile(age_years=41, sex="female", is_healthy_volunteer=False)
SAYS_NOTHING = PatientProfile()


def make_study(
    *,
    minimum_age: str | None = "18 Years",
    maximum_age: str | None = None,
    sex: str = "ALL",
    healthy_volunteers: bool | None = False,
) -> Study:
    return Study(
        nct_id="NCT00000001",
        brief_title="A study",
        official_title=None,
        overall_status="RECRUITING",
        status_verified_date=None,
        last_update_post_date=None,
        study_type="INTERVENTIONAL",
        phases=("PHASE3",),
        enrollment_count=None,
        conditions=(),
        lead_sponsor=None,
        eligibility=Eligibility(
            criteria_text="",
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            sex=sex,
            healthy_volunteers=healthy_volunteers,
            std_ages=(),
        ),
        locations=(),
    )


# --------------------------------------------------------------------------
# The split: who can actually answer this?
# --------------------------------------------------------------------------


def test_something_the_registry_never_stated_is_a_question_for_the_study_team() -> None:
    study = make_study(healthy_volunteers=None)
    questions = open_questions(study, KNOWS_EVERYTHING)

    assert len(questions.for_the_study_team) == 1
    asked = questions.for_the_study_team[0]
    assert "don't have the condition" in asked.question
    assert "doesn't say" in asked.because
    # Rigor rule 2: the registry wording that prompted it comes along.
    assert asked.source is not None


def test_something_the_person_never_stated_is_not_a_question_for_anyone_else() -> None:
    """Asking a research nurse how old you are would be absurd. This is the point."""
    study = make_study()
    questions = open_questions(study, SAYS_NOTHING)

    assert questions.for_the_study_team == ()
    assert [item.field for item in questions.you_could_tell_us] == ["age"]
    assert "Add your age" in questions.you_could_tell_us[0].prompt


def test_an_unreadable_age_bound_is_a_question_for_the_study_team() -> None:
    """The registry wrote something we cannot parse. Only they know what it means."""
    study = make_study(minimum_age="between 18 and 65")
    questions = open_questions(study, KNOWS_EVERYTHING)

    assert len(questions.for_the_study_team) == 1
    assert "age" in questions.for_the_study_team[0].question


def test_a_sex_restricted_trial_prompts_the_person_rather_than_the_team() -> None:
    study = make_study(sex="FEMALE")
    questions = open_questions(study, PatientProfile(age_years=41))

    assert questions.for_the_study_team == ()
    assert [item.field for item in questions.you_could_tell_us] == ["sex"]
    # The prompt must not imply they have to answer.
    assert "leave it blank" in questions.you_could_tell_us[0].prompt


def test_both_kinds_can_appear_on_one_trial() -> None:
    study = make_study(healthy_volunteers=None)
    questions = open_questions(study, SAYS_NOTHING)

    assert len(questions.for_the_study_team) == 1
    assert [item.field for item in questions.you_could_tell_us] == ["age"]
    assert questions.is_empty is False


# --------------------------------------------------------------------------
# A settled check is not a question
# --------------------------------------------------------------------------


@pytest.mark.parametrize("verdict", [Verdict.MET, Verdict.NOT_MET])
def test_a_settled_check_never_produces_a_question(verdict: Verdict) -> None:
    check = HardCheck(
        field="healthy volunteers",
        verdict=verdict,
        reason="settled one way or the other",
        source="accepts healthy volunteers: False",
    )
    assert question_for(check, KNOWS_EVERYTHING) is None


def test_a_trial_with_nothing_open_reports_nothing_open() -> None:
    study = make_study()
    questions = open_questions(study, KNOWS_EVERYTHING)

    assert questions.is_empty is True
    assert questions.for_the_study_team == ()
    assert questions.you_could_tell_us == ()


def test_every_unknown_a_person_cannot_answer_becomes_a_question() -> None:
    """The guard against an UNKNOWN being silently swallowed.

    Runs the four situations `hardfilter.py` can produce an UNKNOWN in, and
    asserts that each one ends up in exactly one of the two lists — never in
    neither. If somebody adds a fifth UNKNOWN and forgets this module, the new
    one falls to the study-team list by default, which is the safe direction.
    """
    situations = [
        (make_study(), SAYS_NOTHING),  # age not stated by the person
        (make_study(sex="MALE"), PatientProfile(age_years=41)),  # sex not stated
        (make_study(healthy_volunteers=None), KNOWS_EVERYTHING),  # registry silent
        (make_study(minimum_age="18 to 65"), KNOWS_EVERYTHING),  # unreadable bound
    ]

    for study, profile in situations:
        unknowns = [c for c in hard_filter(study, profile).checks if c.verdict is Verdict.UNKNOWN]
        assert unknowns, "this situation was supposed to produce an UNKNOWN"

        questions = open_questions(study, profile)
        raised = len(questions.for_the_study_team) + len(questions.you_could_tell_us)
        assert raised == len(unknowns), (
            f"{len(unknowns)} unknown(s) produced {raised} question(s) for "
            f"{[c.field for c in unknowns]}"
        )


def test_the_self_answerable_list_is_exactly_the_fields_a_person_knows() -> None:
    """A guard on the table itself, so widening it is a deliberate act.

    Adding a field here can stop an unknown ever reaching a coordinator. That
    should never happen by accident, so the set is pinned.
    """
    assert SELF_ANSWERABLE_FIELDS == {"age", "sex"}


def test_the_same_field_is_the_persons_to_answer_or_the_teams_depending_on_why() -> None:
    """The distinction a field-name split would have got wrong.

    Both of these are an `UNKNOWN` on the age check. One is the person's to fix
    in a second; the other only the study team knows the answer to.
    """
    blank_age = hard_filter(make_study(), SAYS_NOTHING).checks[0]
    assert person_could_answer(blank_age, SAYS_NOTHING) is True

    unreadable_bound = hard_filter(make_study(minimum_age="18 to 65"), KNOWS_EVERYTHING).checks[0]
    assert unreadable_bound.verdict is Verdict.UNKNOWN
    assert person_could_answer(unreadable_bound, KNOWS_EVERYTHING) is False


# --------------------------------------------------------------------------
# What it must never say
# --------------------------------------------------------------------------


def test_no_question_ever_asserts_eligibility() -> None:
    """Rigor rule 1, on the one output the person keeps and takes with them."""
    study = make_study(healthy_volunteers=None, minimum_age="18 to 65")
    questions = open_questions(study, SAYS_NOTHING)

    text = " ".join(
        [q.question + " " + q.because for q in questions.for_the_study_team]
        + [item.prompt for item in questions.you_could_tell_us]
    ).lower()

    assert text, "this study was supposed to raise questions"
    for claim in ("you are eligible", "you qualify", "you don't qualify", "you are not eligible"):
        assert claim not in text
