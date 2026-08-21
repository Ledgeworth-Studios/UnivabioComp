"""Age, sex and healthy-volunteer decisions, made in plain Python.

The registry gives us these three things as *structured fields* — `minimumAge`,
`maximumAge`, `sex`, `healthyVolunteers` — so the answer is arithmetic, not
interpretation. `docs/PLAN.md` is explicit that no model touches this step. It
would be slower, cost money, and be wrong occasionally, in exchange for nothing.

The verdicts are the same three the rest of the app uses:

    MET       nothing in this field rules the person out
    NOT_MET   this field rules the person out
    UNKNOWN   the person didn't tell us enough, or the registry didn't

`UNKNOWN` is why this module is not a boolean filter. If someone never mentions
their age, the honest answer is "ask the study team", not "excluded".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from whynot.profile import PatientProfile
from whynot.registry import Eligibility, Study


class Verdict(Enum):
    """The three-valued verdict used everywhere in this project."""

    MET = "MET"
    NOT_MET = "NOT_MET"
    UNKNOWN = "UNKNOWN"


#: How the registry writes ages, and how many years one of each unit is.
#: Observed live on 2026-08-21: Hours, Days, Weeks, Months and Years all occur,
#: in both singular and plural spellings.
DAYS_PER_YEAR = 365.25
YEARS_PER_UNIT = {
    "hour": 1 / (24 * DAYS_PER_YEAR),
    "day": 1 / DAYS_PER_YEAR,
    "week": 7 / DAYS_PER_YEAR,
    "month": 1 / 12,
    "year": 1.0,
}

_AGE_PATTERN = re.compile(
    r"^\s*(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>hour|day|week|month|year)s?\s*$",
    re.IGNORECASE,
)


class UnparseableAge(ValueError):
    """The registry gave an age string in a shape we have never seen."""


#: A human pregnancy runs to about 40 weeks, and a gestational age is quoted from
#: roughly the edge of viability to a little past term. A bound in weeks inside
#: this range may be a *gestational* age rather than a postnatal one — and the
#: registry has no field that says which. See `docs/decisions/0006`.
GESTATIONAL_WEEKS = (20, 45)

#: How old a person can be and still plausibly be in a trial that enrols babies
#: by their gestational age at birth. Deliberately generous: it decides only
#: whether we are willing to say NOT_MET, so erring large errs towards UNKNOWN.
NEWBORN_WINDOW_YEARS = 2.0


def possibly_gestational(text: str | None) -> bool:
    """Could this age bound be a gestational age rather than a postnatal one?

    True for `"27 Weeks"`, false for `"5 Weeks"` and for anything not in weeks.
    Both of those are real: `NCT01066728` enrols infants "between 27 and 32 weeks
    gestational age", and `NCT06737159` enrols children from 5 weeks old, which is
    an age since birth. Twenty-seven weeks is a plausible length of pregnancy;
    five weeks is not.
    """
    if text is None:
        return False
    match = _AGE_PATTERN.match(text)
    if match is None or match.group("unit").lower() != "week":
        return False
    low, high = GESTATIONAL_WEEKS
    return low <= float(match.group("number")) <= high


@dataclass(frozen=True)
class HardCheck:
    """One structured-field decision, with the text that justifies it."""

    field: str
    verdict: Verdict
    reason: str
    source: str | None = None


@dataclass(frozen=True)
class HardFilterResult:
    """The three checks for one study."""

    checks: tuple[HardCheck, ...]

    @property
    def is_ruled_out(self) -> bool:
        """True when a structured field definitively excludes this person."""
        return any(check.verdict is Verdict.NOT_MET for check in self.checks)

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        return tuple(c.reason for c in self.checks if c.verdict is Verdict.NOT_MET)

    @property
    def open_questions(self) -> tuple[str, ...]:
        return tuple(c.reason for c in self.checks if c.verdict is Verdict.UNKNOWN)


# --------------------------------------------------------------------------
# Age
# --------------------------------------------------------------------------


def parse_age_to_years(text: str | None) -> float | None:
    """Turn a registry age string such as `"18 Years"` or `"6 Months"` into years.

    Returns None when the bound is simply absent, which is common and normal —
    most adult trials have no upper age limit. Raises `UnparseableAge` when the
    string exists but is not a shape we recognise, because silently returning
    None there would turn a parser bug into a wrong eligibility answer.
    """
    if text is None or not text.strip():
        return None
    match = _AGE_PATTERN.match(text)
    if match is None:
        raise UnparseableAge(f"cannot read {text!r} as an age")
    return float(match.group("number")) * YEARS_PER_UNIT[match.group("unit").lower()]


def describe_age_range(eligibility: Eligibility) -> str:
    """Human-readable age window, quoting the registry's own wording."""
    low, high = eligibility.minimum_age, eligibility.maximum_age
    if low and high:
        return f"{low} to {high}"
    if low:
        return f"{low} and older"
    if high:
        return f"up to {high}"
    return "no age limits stated"


def check_age(eligibility: Eligibility, profile: PatientProfile) -> HardCheck:
    source = describe_age_range(eligibility)

    try:
        low = parse_age_to_years(eligibility.minimum_age)
        high = parse_age_to_years(eligibility.maximum_age)
    except UnparseableAge as exc:
        # An age we cannot read is a reason to ask, never a reason to exclude.
        return HardCheck(
            field="age",
            verdict=Verdict.UNKNOWN,
            reason=f"This trial states an age limit we could not read ({exc}). Ask the study team.",
            source=source,
        )

    if low is None and high is None:
        return HardCheck(
            field="age",
            verdict=Verdict.MET,
            reason="This trial states no age limits.",
            source=source,
        )

    if profile.age_years is None:
        return HardCheck(
            field="age",
            verdict=Verdict.UNKNOWN,
            reason=f"This trial enrols ages {source}. You didn't tell us your age.",
            source=source,
        )

    age = profile.age_years
    outside_postnatal = (low is not None and age < low) or (high is not None and age > high)

    # A bound in weeks may be a gestational age, and the registry does not say
    # which. `docs/decisions/0006`: never rule somebody out on a reading of the
    # record we cannot confirm.
    if possibly_gestational(eligibility.minimum_age) or possibly_gestational(
        eligibility.maximum_age
    ):
        if age > NEWBORN_WINDOW_YEARS:
            # No reading admits them: under the gestational reading this trial
            # enrols newborns, and they are not one.
            return HardCheck(
                field="age",
                verdict=Verdict.NOT_MET,
                reason=(
                    f"This trial enrols ages {source} — which for a newborn study "
                    f"usually means weeks of pregnancy at birth — and you told us "
                    f"you are {_years(age)}."
                ),
                source=source,
            )
        return HardCheck(
            field="age",
            verdict=Verdict.UNKNOWN,
            reason=(
                f"This trial states ages {source}. For studies of newborns that "
                "usually means weeks of pregnancy at birth rather than age since "
                "birth, and the registry record does not say which. Ask the study "
                "team which one they mean."
            ),
            source=source,
        )

    if outside_postnatal:
        return HardCheck(
            field="age",
            verdict=Verdict.NOT_MET,
            reason=f"This trial enrols ages {source}; you told us you are {_years(age)}.",
            source=source,
        )
    return HardCheck(
        field="age",
        verdict=Verdict.MET,
        reason=f"This trial enrols ages {source}, which includes {_years(age)}.",
        source=source,
    )


def _years(age: float) -> str:
    """Print an age the way a person would say it."""
    if age >= 2:
        return f"{age:.0f} years old" if float(age).is_integer() else f"{age:.1f} years old"
    if age >= 1 / 12:
        return f"{age * 12:.0f} months old"
    return f"{age * DAYS_PER_YEAR:.0f} days old"


# --------------------------------------------------------------------------
# Sex
# --------------------------------------------------------------------------


def check_sex(eligibility: Eligibility, profile: PatientProfile) -> HardCheck:
    trial_sex = (eligibility.sex or "ALL").upper()
    source = f"sex: {trial_sex}"

    if trial_sex not in {"FEMALE", "MALE"}:
        return HardCheck(
            field="sex",
            verdict=Verdict.MET,
            reason="This trial enrols people of any sex.",
            source=source,
        )

    spoken = trial_sex.lower()
    person_sex = profile.registry_sex
    if person_sex is None:
        return HardCheck(
            field="sex",
            verdict=Verdict.UNKNOWN,
            reason=(
                f"This trial enrols {spoken} participants only, and we could not tell "
                "which applies to you. Ask the study team."
            ),
            source=source,
        )
    if person_sex != trial_sex:
        return HardCheck(
            field="sex",
            verdict=Verdict.NOT_MET,
            reason=f"This trial enrols {spoken} participants only.",
            source=source,
        )
    return HardCheck(
        field="sex",
        verdict=Verdict.MET,
        reason=f"This trial enrols {spoken} participants, which matches what you told us.",
        source=source,
    )


# --------------------------------------------------------------------------
# Healthy volunteers
# --------------------------------------------------------------------------


def check_healthy_volunteers(eligibility: Eligibility, profile: PatientProfile) -> HardCheck:
    """Decide the `healthyVolunteers` field.

    Read it narrowly, because it says less than it looks like it says. `true`
    means the study will take people who do not have the condition; it never
    excludes anyone. `false` means it will not — which only rules out a person
    who has told us they are healthy. It does *not* mean "you must have
    condition X", and this module does not pretend otherwise; the actual
    diagnosis requirements live in the free-text criteria, where W1-5's judge
    reads them.
    """
    accepts = eligibility.healthy_volunteers
    source = f"accepts healthy volunteers: {accepts}"

    if accepts is None:
        return HardCheck(
            field="healthy volunteers",
            verdict=Verdict.UNKNOWN,
            reason="This trial does not say whether it accepts healthy volunteers.",
            source=source,
        )
    if accepts:
        return HardCheck(
            field="healthy volunteers",
            verdict=Verdict.MET,
            reason="This trial accepts healthy volunteers.",
            source=source,
        )
    if profile.is_healthy_volunteer is True:
        return HardCheck(
            field="healthy volunteers",
            verdict=Verdict.NOT_MET,
            reason=(
                "This trial does not accept healthy volunteers, and you told us you "
                "are volunteering without the condition being studied."
            ),
            source=source,
        )
    return HardCheck(
        field="healthy volunteers",
        verdict=Verdict.MET,
        reason="This trial does not accept healthy volunteers, which does not rule you out.",
        source=source,
    )


# --------------------------------------------------------------------------
# All three at once
# --------------------------------------------------------------------------


def hard_filter(study: Study, profile: PatientProfile) -> HardFilterResult:
    """Run every structured-field check against one study."""
    eligibility = study.eligibility
    return HardFilterResult(
        checks=(
            check_age(eligibility, profile),
            check_sex(eligibility, profile),
            check_healthy_volunteers(eligibility, profile),
        )
    )
