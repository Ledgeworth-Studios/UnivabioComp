r"""Split the registry's free-text eligibility blob into individual criteria.

ClinicalTrials.gov stores inclusion and exclusion criteria as **one text field**.
There is no structure, no list, no per-criterion identifier — just whatever the
study team typed into a box. This module turns that blob into a list of discrete
criteria, each tagged inclusion or exclusion, each carrying the exact source text
it came from so a verdict can quote it (rigor rule 2 in `docs/PLAN.md`).

This is deliberately not a model's job. Splitting on bullets is a text-formatting
problem, and a model asked to do it will occasionally paraphrase a criterion —
which silently breaks the promise that every quote is verbatim registry text.

## What the real data looks like

Every one of these was found in a recorded fixture, not imagined:

* `Inclusion Criteria:` / `Exclusion Criteria:` headers with `*` bullets.
* The header itself written as a bullet: `* INCLUSION CRITERIA:` (NCT06096870).
* Headers that appear more than twice, split by cohort:
  `Inclusion Criteria, cases:` … `Inclusion Criteria, controls:` (NCT01271491).
* Numbered lists, sometimes with markdown-escaped dots: `1\. ` (NCT06737159).
* Roman-numeral and lettered sub-items: `i)`, `ii)`, `a)` (NCT06408259).
* Indented sub-bullets that are meaningless on their own — "Nasal flaring;"
  under "Increased respiratory effort manifested as follows:".
* Markdown escaping throughout: `Testosterone \>100 ng/dL`, `m\^2`.
* Blobs with **no headers at all** (NCT00132080).

## The one rule worth remembering

An indented bullet is folded into the criterion above it. "Platelets
\>=100,000/microliter" judged on its own is nonsense; judged as part of
"Participants must have adequate organ and marrow function as defined below" it
makes sense. Top-level bullets start new criteria, indented ones never do.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CriterionKind(Enum):
    """Which half of the eligibility text a criterion came from."""

    INCLUSION = "INCLUSION"
    EXCLUSION = "EXCLUSION"
    #: The blob had no headers, so we genuinely do not know. We say so rather
    #: than guessing, for the same reason verdicts have an UNKNOWN.
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass(frozen=True)
class Criterion:
    """One eligibility criterion, and the registry text it was cut from."""

    index: int
    kind: CriterionKind
    #: Readable form: bullet marker removed, markdown escapes undone.
    text: str
    #: A verbatim slice of `eligibilityCriteria`. Never edited, so a quote shown
    #: to a user can always be found in the registry record.
    source_text: str


#: A line that announces which half of the criteria follows. The leading bullet
#: is stripped before matching because some records bullet their headers.
_HEADER_PATTERN = re.compile(
    r"^(?:key\s+|main\s+)?(?P<kind>inclusion|exclusion)(?:\s+criteria)?\b[^.]{0,40}:?\s*$",
    re.IGNORECASE,
)

#: Every list marker seen in real records: asterisks, one or two hyphens, en and
#: em dashes, bullets, `1.`, `1)`, the markdown-escaped `1\.`, `i)` and `a)`.
_BULLET_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>\*|--|-|–|—|•|\\-|\d+\\?[.)]|[ivx]{1,4}\)|[a-zA-Z]\))"
    r"(?=[ \t]|\w|$)[ \t]*"
)

#: Markdown escaping the registry applies to punctuation inside criteria text.
_ESCAPE_PATTERN = re.compile(r"\\([<>\[\]()*_.\-#^`~|])")


def unescape(text: str) -> str:
    r"""Undo the registry's markdown escaping: `\>100` becomes `>100`."""
    return _ESCAPE_PATTERN.sub(r"\1", text)


def _header_kind(line: str) -> CriterionKind | None:
    """If this line is an `Inclusion Criteria:` style header, say which kind."""
    stripped = unescape(line).strip()
    bullet = _BULLET_PATTERN.match(stripped)
    if bullet:
        stripped = stripped[bullet.end() :].strip()
    if not stripped or len(stripped) > 80:
        return None
    match = _HEADER_PATTERN.match(stripped)
    if match is None:
        return None
    return CriterionKind[match.group("kind").upper()]


@dataclass
class _Block:
    """A criterion under construction: where it starts and ends in the blob."""

    kind: CriterionKind
    start: int
    end: int


def split_criteria(blob: str) -> tuple[Criterion, ...]:
    """Cut one `eligibilityCriteria` blob into individual criteria.

    Returns an empty tuple for an empty blob. Never raises: a record whose text
    we cannot make sense of should degrade to "one big criterion", not to a
    crash, because the alternative is dropping a trial from someone's results
    without telling them.
    """
    if not blob or not blob.strip():
        return ()

    text = blob.replace("\r\n", "\n").replace("\r", "\n")
    kind = CriterionKind.UNCLASSIFIED
    blocks: list[_Block] = []
    offset = 0

    for line in text.split("\n"):
        start, end = offset, offset + len(line)
        offset = end + 1  # +1 for the newline we split on

        if not line.strip():
            continue

        header = _header_kind(line)
        if header is not None:
            kind = header
            continue

        bullet = _BULLET_PATTERN.match(line)
        indented = line[: len(line) - len(line.lstrip())] != ""

        starts_new_criterion = bullet is not None and not indented
        if not blocks or blocks[-1].kind is not kind:
            # The first line after a header always starts a criterion, even when
            # it is plain prose with no bullet in front of it.
            starts_new_criterion = starts_new_criterion or not _is_lead_in(line)

        if starts_new_criterion:
            blocks.append(_Block(kind=kind, start=start, end=end))
        elif blocks:
            # A continuation line, an indented sub-bullet, or a bare "OR".
            blocks[-1].end = end
        # else: a lead-in like "Children must fulfil all of the following:" that
        # precedes the first bullet. Dropped — it introduces criteria, it is not
        # one.

    return tuple(
        Criterion(
            index=i,
            kind=block.kind,
            text=_clean(text[block.start : block.end]),
            source_text=text[block.start : block.end],
        )
        for i, block in enumerate(blocks)
    )


def _is_lead_in(line: str) -> bool:
    """True for a sentence that introduces a list rather than being an item in it.

    In practice these always end in a colon — "Children eligible for the trial
    must fulfil all of the following criteria:".
    """
    return line.strip().endswith(":")


def _clean(source: str) -> str:
    """Readable form of a criterion: marker removed, escapes undone, tidy lines."""
    lines = [line.rstrip() for line in unescape(source).split("\n")]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return ""
    first = _BULLET_PATTERN.sub("", lines[0], count=1).strip()
    rest = [line.strip() for line in lines[1:]]
    return "\n".join([first, *rest]).strip()


def inclusion_criteria(criteria: tuple[Criterion, ...]) -> tuple[Criterion, ...]:
    return tuple(c for c in criteria if c.kind is CriterionKind.INCLUSION)


def exclusion_criteria(criteria: tuple[Criterion, ...]) -> tuple[Criterion, ...]:
    return tuple(c for c in criteria if c.kind is CriterionKind.EXCLUSION)
