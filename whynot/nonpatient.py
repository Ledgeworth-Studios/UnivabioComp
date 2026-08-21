"""Some trials do not enrol people.

`docs/PLAN.md` records this as a verified trap. `NCT06251323` looks like an
ordinary diabetes study — "Implementing Scalable, PAtient-centered, Team-based,
Technology-enabled Care for Adults With Type 2 Diabetes", ages 18 and up, all
sexes, healthy volunteers accepted. Its eligibility criteria then turn out to
describe *federally qualified health centres*: two largest clinic sites,
prioritise those with poorer A1c control, exclude ones with fewer than 5,000
patients. A person with type 2 diabetes cannot enrol in it. There is nothing in
the structured fields that says so outright.

## The hazard is a false positive, not a false negative

Getting this wrong in one direction shows somebody a study they cannot join, and
they lose a minute reading it. Getting it wrong in the other direction tells
somebody a study is not for people when it is — and they never call. That is the
same shape as a `NOT_MET` that should have been `UNKNOWN`, the error
`docs/PLAN.md` says to weight hardest.

Three consequences, and all three are the design:

1. **Two independent signals are required**, never one. A single mention of
   "hospital" or "clinic" in an eligibility criterion means nothing — plenty of
   patient trials enrol people *at* a hospital, or exclude people who live in a
   nursing home. One signal is a coincidence; two is a pattern.
2. **The evidence comes back with the answer.** The caller gets the list of
   signals that fired, so the interface can show its working and a reader can
   disagree with it.
3. **The wording is a possibility, never a verdict**, and the trial is labelled
   rather than hidden or demoted — `docs/decisions/0003`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from whynot.registry import Study

#: A purpose of "health services research" means the study is investigating how
#: care is delivered. Many such studies still enrol patients, so on its own this
#: proves nothing — it is one signal of the two that are required.
ORGANISATION_PURPOSES = {"HEALTH_SERVICES_RESEARCH"}

#: Words that name an *organisation* in eligibility criteria. Deliberately short.
#: Every entry here had to survive one question: could this word appear in the
#: criteria of an ordinary trial that enrols people? "Hospital" and "site" fail
#: that test — "currently hospitalised" and "able to attend the study site" are
#: ordinary patient criteria — so they are not here. What is left are words that
#: are hard to write about a single human being.
ORGANISATION_TERMS = (
    "fqhc",
    "federally qualified health cent",
    "health cent",
    "health system",
    "clinic site",
    "primary care practice",
    "general practice",
    "physician practice",
    "medical practice",
    "nursing home",
    "care home",
    "dialysis facilit",
    "pharmacies",
    "participating practices",
)

#: Criteria phrased about a population rather than a person. "Patient population"
#: is the giveaway: a trial that enrols people never describes its participant as
#: having one.
POPULATION_PHRASES = (
    "patient population",
    "patient panel",
    "number of patients served",
    "patients served",
    "patient volume",
)


@dataclass(frozen=True)
class Signal:
    """One piece of evidence, and the registry text it was found in."""

    name: str
    explanation: str
    #: The matched wording, so a reader can check it against the record.
    quote: str | None


@dataclass(frozen=True)
class NonPatientAssessment:
    """Whether a study looks like it enrols organisations, and why we think so."""

    signals: tuple[Signal, ...]

    @property
    def looks_like_organisations(self) -> bool:
        """True only with corroboration. One signal is never enough."""
        return len(self.signals) >= 2


def _quote_around(text: str, term: str) -> str | None:
    """The sentence-ish fragment a term was found in, for showing as evidence."""
    match = re.search(rf"[^\n.]*{re.escape(term)}[^\n.]*", text, re.IGNORECASE)
    if match is None:
        return None
    return " ".join(match.group(0).split()).strip(" *-")[:200]


def assess(study: Study) -> NonPatientAssessment:
    """Look for evidence that this study enrols organisations rather than people."""
    signals: list[Signal] = []
    criteria = study.eligibility.criteria_text or ""
    lowered = criteria.lower()

    if study.primary_purpose in ORGANISATION_PURPOSES:
        signals.append(
            Signal(
                name="purpose",
                explanation=(
                    "The registry records this study's purpose as health services "
                    "research — research into how care is delivered."
                ),
                quote=f"primary purpose: {study.primary_purpose}",
            )
        )

    for term in ORGANISATION_TERMS:
        if term in lowered:
            signals.append(
                Signal(
                    name="organisation named in the criteria",
                    explanation="The eligibility criteria describe organisations, not individuals.",
                    quote=_quote_around(criteria, term),
                )
            )
            break

    for phrase in POPULATION_PHRASES:
        if phrase in lowered:
            signals.append(
                Signal(
                    name="criteria written about a population",
                    explanation=(
                        "The criteria describe the participant as having a patient "
                        "population, which an individual person does not."
                    ),
                    quote=_quote_around(criteria, phrase),
                )
            )
            break

    return NonPatientAssessment(signals=tuple(signals))


#: The caution shown on a card. It is a possibility and a redirection, never a
#: conclusion — rigor rule 1, and the false-positive hazard above.
CAUTION = (
    "This study's eligibility criteria appear to describe clinics, practices or "
    "health systems rather than individual people, so it may not be one you can "
    "join as a patient. We could be wrong — the evidence is below, and the study "
    "team can tell you for certain."
)
