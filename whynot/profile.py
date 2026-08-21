"""What the user told us about themselves.

This is the only description of a person that the rest of the app ever sees.
Every field is optional, and that is the point: the product's whole argument is
that not knowing something is a first-class answer, not a gap to be papered over.
A missing field produces `UNKNOWN` verdicts and coordinator questions, never a
guess.

Nothing here is stored server-side (rigor rule 4). It is built from what the user
typed, held for the length of a search, and thrown away.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Words we are willing to read as a sex, mapped to the registry's own vocabulary.
#: Anything not in this table is treated as "we don't know", never as a guess.
#: The registry records sex, not gender identity, and only ever uses these two
#: values plus ALL — so this table stays deliberately small rather than trying to
#: interpret how someone describes themselves.
SEX_SYNONYMS = {
    "f": "FEMALE",
    "female": "FEMALE",
    "woman": "FEMALE",
    "m": "MALE",
    "male": "MALE",
    "man": "MALE",
}


@dataclass(frozen=True)
class PatientProfile:
    """A person's situation, as far as we know it.

    `age_years` is a float so that infant trials — the registry has bounds
    measured in days and hours — can be represented at all.

    The field list is argued in `docs/decisions/0008`. The short version: each one
    had to be something a person would say in a sentence about their situation,
    unprompted, because W2-1's job is to fill this from exactly such a sentence.
    A field nobody says out loud is a field that stays empty forever. Lab values
    and disease scores were rejected on that test — criteria needing them stay
    `UNKNOWN` and become questions for the study team, which is the product
    working rather than failing.
    """

    age_years: float | None = None
    sex: str | None = None
    is_healthy_volunteer: bool | None = None
    conditions: tuple[str, ...] = field(default_factory=tuple)
    #: "diagnosed in 2019". A year, not a date: nobody remembers the day.
    diagnosed_year: int | None = None
    #: What they are on now — "ocrelizumab", "metformin".
    current_treatments: tuple[str, ...] = field(default_factory=tuple)
    #: What they have been on before. Trials ask about prior therapy constantly.
    past_treatments: tuple[str, ...] = field(default_factory=tuple)

    @property
    def registry_sex(self) -> str | None:
        """The user's sex in the registry's vocabulary, or None if we can't tell."""
        if self.sex is None:
            return None
        return SEX_SYNONYMS.get(self.sex.strip().lower())
