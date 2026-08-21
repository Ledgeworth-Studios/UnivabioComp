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
    """

    age_years: float | None = None
    sex: str | None = None
    is_healthy_volunteer: bool | None = None
    conditions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def registry_sex(self) -> str | None:
        """The user's sex in the registry's vocabulary, or None if we can't tell."""
        if self.sex is None:
            return None
        return SEX_SYNONYMS.get(self.sex.strip().lower())
