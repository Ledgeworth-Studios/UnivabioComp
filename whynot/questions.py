"""Turning "we don't know" into something the person can actually do.

`docs/PLAN.md` says the questions a person walks away with are the deliverable —
the thing no existing trial finder gives you. This module builds them.

## An UNKNOWN has two causes, and they are not the same problem

Every `UNKNOWN` verdict in this system comes from one of two places, and telling
them apart is the whole job of this module:

**The registry did not say.** The trial's record has an age bound nobody can
parse, or its healthy-volunteer field is blank. Nothing the person types can fix
that; the answer exists only inside the study team's protocol. *That* is a
question to ask a coordinator.

**The person did not say.** They left the age box empty, or preferred not to
state a sex. The study team cannot answer that, and asking them to would be
ridiculous — "how old am I?" is not a question for a research nurse. This is
something the person can fill in themselves, so it becomes a prompt pointing at
the chip they can edit.

Conflating the two would take the headline feature of this project and make it
look foolish, so the split is enforced here rather than left to the interface.

**The split is by cause, not by field**, and the difference is not academic. The
age check produces an `UNKNOWN` for *two* different reasons: the person left the
box empty, or the registry wrote an age bound nobody can parse. Those are the
same field and opposite problems — one the person fixes in a second, the other
only the study team knows the answer to. Sorting by field name would have sent
"this trial states an age limit we could not read" back to the person as though
they had forgotten to type something. So each field is asked the direct question:
*did the person leave this blank?* If they did, it is theirs. If they did not,
the gap is in the record, and that is a question for the study team.

## What this module will never do

It never asserts eligibility, and it never phrases a question as though the
answer were known. Every question quotes the registry wording that prompted it,
so a person holding the printed list can point at the line. That is rigor rules
1 and 2 (`docs/PLAN.md`) applied to the one output the user actually keeps.

Most questions will eventually come from the judged free-text criteria, which is
W3-3b and needs a model. The structure here is built so that those merge in as
another source of `UNKNOWN`s rather than as a second, parallel feature.
"""

from __future__ import annotations

from dataclasses import dataclass

from whynot.hardfilter import HardCheck, Verdict, hard_filter
from whynot.profile import PatientProfile
from whynot.registry import Study

#: The only fields a person could possibly answer about themselves. A check on
#: any other field that comes back UNKNOWN is, by definition, something only the
#: study team can settle — so a new UNKNOWN added to `hardfilter.py` becomes a
#: coordinator question by default. That is the safe direction to fail in: it
#: produces a question the person did not need, rather than silently swallowing
#: one they did.
#:
#: Being in this set is necessary but not sufficient — see `person_could_answer`.
SELF_ANSWERABLE_FIELDS = {"age", "sex"}


@dataclass(frozen=True)
class CoordinatorQuestion:
    """Something only the study team can answer, and the text that prompted it."""

    #: The question, phrased so it can be read aloud on a phone call.
    question: str
    #: Why we are asking — what the record does or does not say.
    because: str
    #: The registry wording behind it, so the person can point at the line.
    source: str | None


@dataclass(frozen=True)
class SelfAnswerable:
    """Something the person could tell us, with the field they would edit."""

    field: str
    prompt: str


@dataclass(frozen=True)
class OpenQuestions:
    """Everything still unresolved about one trial, sorted by who can resolve it."""

    for_the_study_team: tuple[CoordinatorQuestion, ...]
    you_could_tell_us: tuple[SelfAnswerable, ...]

    @property
    def is_empty(self) -> bool:
        return not self.for_the_study_team and not self.you_could_tell_us


#: How each self-answerable field is offered back to the person. Written as an
#: invitation rather than an instruction: leaving it blank stays a valid choice.
SELF_ANSWERABLE_PROMPTS = {
    "age": "Add your age and we can check this trial's age limits against it.",
    "sex": (
        "This trial only enrols people of one sex. Tell us which applies to you "
        "and we can check it — or leave it blank and ask the study team instead."
    ),
}


def person_could_answer(check: HardCheck, profile: PatientProfile) -> bool:
    """Is this unknown unknown because *the person* didn't say?

    The question is asked of the profile directly rather than inferred from the
    field name, because the same field goes unknown for opposite reasons. An age
    check is the person's to answer only when they left the age blank; when they
    gave an age and the check is still unresolved, the registry wrote a bound
    nobody could read, and that is not theirs to fix.
    """
    if check.field not in SELF_ANSWERABLE_FIELDS:
        return False
    if check.field == "age":
        return profile.age_years is None
    return profile.registry_sex is None


def question_for(check: HardCheck, profile: PatientProfile) -> CoordinatorQuestion | None:
    """The coordinator question one unresolved structured check produces.

    Returns None for anything already settled, and for anything the person can
    answer themselves. A check that came back `MET` or `NOT_MET` has an answer,
    and an answer is not a question — the whole point of the three-valued verdict
    is that only the third one becomes work for anybody.
    """
    if check.verdict is not Verdict.UNKNOWN:
        return None
    if person_could_answer(check, profile):
        return None

    if check.field == "healthy volunteers":
        return CoordinatorQuestion(
            question=(
                "Does this study enrol people who don't have the condition being "
                "studied — and would that apply to me?"
            ),
            because="The registry record doesn't say either way.",
            source=check.source,
        )

    # Anything else unresolved that the person cannot answer themselves. The
    # unreadable-age-bound case lands here, and so will any check added later.
    return CoordinatorQuestion(
        question=f"Can you tell me what this study's {check.field} requirements actually are?",
        because=check.reason,
        source=check.source,
    )


def open_questions(study: Study, profile: PatientProfile) -> OpenQuestions:
    """Everything still open about one trial, split by who can close it."""
    checks = hard_filter(study, profile).checks

    for_team: list[CoordinatorQuestion] = []
    for_you: list[SelfAnswerable] = []

    for check in checks:
        if check.verdict is not Verdict.UNKNOWN:
            continue
        if person_could_answer(check, profile):
            for_you.append(
                SelfAnswerable(
                    field=check.field,
                    prompt=SELF_ANSWERABLE_PROMPTS.get(
                        check.field, f"Tell us your {check.field} and we can check it."
                    ),
                )
            )
            continue
        question = question_for(check, profile)
        if question is not None:
            for_team.append(question)

    return OpenQuestions(for_the_study_team=tuple(for_team), you_could_tell_us=tuple(for_you))
