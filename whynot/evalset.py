"""The answer key the judge will be marked against.

An eval set is a list of (person, criterion, expected verdict) triples. When the
judge exists — W1-5, waiting on an API key — W4-2 runs it over these and reports
how often it agreed, weighting the dangerous error specifically: `NOT_MET` where
the truth is `UNKNOWN`, which tells a real person they don't qualify for a trial
they might qualify for.

Two rules are enforced in code here rather than trusted to whoever edits the
fixture. Both are argued in `docs/decisions/0004`.

## An agent may propose a label; it may not confirm one

The number this set produces is going in front of competition judges attached to a
claim about a medical tool. If the same kind of system writes both the answers and
the answer key, that number measures agreement, not correctness.

So a pair that takes judgement to label carries `needs_human_review`, and
`scorable_pairs` refuses to hand it to the scoring code until a person has put
their name in `reviewed_by`. Not a warning printed and ignored — excluded from the
count, with the exclusions reported next to the score.

Pairs that need no review are the ones anybody can check by reading: the profile
says nothing at all about MRI lesions, so a criterion about MRI lesions is
`UNKNOWN`. That is not a clinical opinion, and those cases are the majority of
what matters, because the dangerous error lives exactly there.

## Criteria must be real, and this is checked

`load_eval_set` refuses any pair whose criterion text does not appear **verbatim**
in one of the recorded registry fixtures. A plausible-sounding criterion somebody
typed from memory would make the eval measure the wrong thing while looking
entirely fine, so the set is pinned to bytes that came from the registry.

## What MET means

`MET` means **this criterion, as written, describes the person** — including for
exclusion criteria, where being described is what rules you out. See
`docs/decisions/0004`; W1-5's prompt must state the same convention or every
exclusion in this set scores backwards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from whynot.hardfilter import Verdict
from whynot.profile import PatientProfile

#: Where the recorded registry responses live. Criterion text is checked against
#: these, so the eval set can never drift into invented prose.
REGISTRY_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "registry"

#: The eval sets themselves, versioned: a set is never edited in place once
#: numbers have been published from it. A new version is a new file.
EVAL_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "eval"


class EvalSetError(ValueError):
    """The eval set on disk is not usable, and using it anyway would be worse."""


@dataclass(frozen=True)
class EvalPair:
    """One person, one criterion, one expected answer, and who vouches for it."""

    id: str
    nct_id: str
    #: Verbatim registry text. Checked against the recorded fixtures on load.
    criterion: str
    #: INCLUSION / EXCLUSION / UNCLASSIFIED, as `whynot/criteria.py` tags it.
    kind: str
    profile: PatientProfile
    #: What the judge ought to answer. `MET` = this sentence describes the person.
    expected: Verdict
    #: Why, in one sentence, so the label can be argued with rather than trusted.
    basis: str
    #: True when settling this takes judgement rather than reading.
    needs_human_review: bool
    #: Who confirmed it. Empty string means nobody has.
    reviewed_by: str

    @property
    def is_scorable(self) -> bool:
        """Can this pair be counted without somebody vouching for its label?"""
        return not self.needs_human_review or bool(self.reviewed_by)


@dataclass(frozen=True)
class EvalSet:
    version: str
    description: str
    pairs: tuple[EvalPair, ...]

    def scorable_pairs(self) -> tuple[EvalPair, ...]:
        """The pairs W4-2 is allowed to compute a number from."""
        return tuple(pair for pair in self.pairs if pair.is_scorable)

    def held_back(self) -> tuple[EvalPair, ...]:
        """Pairs waiting on a human. Report these next to any score."""
        return tuple(pair for pair in self.pairs if not pair.is_scorable)


def _recorded_criteria_text() -> str:
    """Every byte of eligibility text we have on disk, concatenated.

    Crude and deliberately so: the question being asked is only "did this string
    come from the registry", and a substring check over the recorded corpus
    answers it without needing to know which file it came from.
    """
    blobs: list[str] = []
    for path in sorted(REGISTRY_FIXTURE_DIR.glob("*.json")):
        payload = json.loads(path.read_text())
        studies = payload.get("studies") or [payload]
        for raw in studies:
            eligibility = (raw.get("protocolSection") or {}).get("eligibilityModule") or {}
            blobs.append(eligibility.get("eligibilityCriteria") or "")
    return "\n".join(blobs)


#: Every field of `PatientProfile` that an eval pair may set. Kept beside the
#: reader because the failure mode is silent: a field added to the profile and
#: forgotten here is simply dropped, and the pair scores against a person missing
#: the very detail it was written to test. `tests/test_evalset.py` asserts this
#: table covers the whole dataclass.
PROFILE_FIELDS = (
    "age_years",
    "sex",
    "is_healthy_volunteer",
    "conditions",
    "diagnosed_year",
    "current_treatments",
    "past_treatments",
)

#: Which of them are lists in the JSON and tuples on the dataclass.
_TUPLE_FIELDS = frozenset({"conditions", "current_treatments", "past_treatments"})


def _profile_from(raw: dict) -> PatientProfile:
    values = {
        name: tuple(raw.get(name) or ()) if name in _TUPLE_FIELDS else raw.get(name)
        for name in PROFILE_FIELDS
    }
    unknown = set(raw) - set(PROFILE_FIELDS)
    if unknown:
        raise EvalSetError(
            f"a pair's profile sets {sorted(unknown)}, which PatientProfile does not have. "
            "A typo here would silently test a different person."
        )
    return PatientProfile(**values)


def load_eval_set(path: Path | str) -> EvalSet:
    """Read and validate an eval set. Raises rather than returning a broken one."""
    path = Path(path)
    payload = json.loads(path.read_text())
    corpus = _recorded_criteria_text()

    pairs: list[EvalPair] = []
    seen: set[str] = set()
    for raw in payload.get("pairs") or ():
        pair_id = raw["id"]
        if pair_id in seen:
            raise EvalSetError(f"duplicate pair id {pair_id!r}")
        seen.add(pair_id)

        criterion = raw["criterion"]
        if criterion not in corpus:
            raise EvalSetError(
                f"pair {pair_id!r} quotes a criterion that appears in no recorded "
                "registry fixture. Eval criteria must be verbatim registry text — "
                "record the study with tools/record_fixtures.py first."
            )

        try:
            expected = Verdict(raw["expected"])
        except ValueError as exc:
            raise EvalSetError(f"pair {pair_id!r} has an unknown verdict") from exc

        if not raw.get("basis"):
            raise EvalSetError(f"pair {pair_id!r} has no stated basis for its label")

        pairs.append(
            EvalPair(
                id=pair_id,
                nct_id=raw["nct_id"],
                criterion=criterion,
                kind=raw["kind"],
                profile=_profile_from(raw["profile"]),
                expected=expected,
                basis=raw["basis"],
                needs_human_review=bool(raw["needs_human_review"]),
                reviewed_by=raw.get("reviewed_by") or "",
            )
        )

    if not pairs:
        raise EvalSetError(f"{path} contains no pairs")

    return EvalSet(
        version=payload["version"],
        description=payload["description"],
        pairs=tuple(pairs),
    )


def load_current() -> EvalSet:
    """The eval set W4-2 should use."""
    return load_eval_set(EVAL_FIXTURE_DIR / "criteria_v1.json")
