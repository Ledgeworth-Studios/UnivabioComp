"""Tests for the eval set — the answer key the judge will be marked against.

Two of these are guards on the *method* rather than on the code, and they are the
reason this module exists: an invented criterion must not be able to enter the
set, and a label nobody has vouched for must not be able to reach the scoring
code. See `docs/decisions/0004`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from whynot.evalset import EvalSetError, load_current, load_eval_set
from whynot.hardfilter import Verdict


def write_set(tmp_path: Path, pairs: list[dict]) -> Path:
    path = tmp_path / "set.json"
    path.write_text(json.dumps({"version": "test", "description": "test set", "pairs": pairs}))
    return path


def a_pair(**overrides) -> dict:
    """A pair quoting a criterion that really is in the recorded fixtures."""
    pair = {
        "id": "p01",
        "nct_id": "NCT06441617",
        "criterion": "* Living in the US",
        "kind": "INCLUSION",
        "profile": {"age_years": 41, "sex": "female", "conditions": ["multiple sclerosis"]},
        "expected": "UNKNOWN",
        "basis": "The profile records no country.",
        "needs_human_review": False,
        "reviewed_by": "",
    }
    pair.update(overrides)
    return pair


# --------------------------------------------------------------------------
# The method guards
# --------------------------------------------------------------------------


def test_a_criterion_that_is_not_real_registry_text_is_refused(tmp_path: Path) -> None:
    """An invented criterion would make the eval measure the wrong thing quietly."""
    path = write_set(
        tmp_path,
        [a_pair(criterion="* Must have a positive attitude and a can-do spirit")],
    )
    with pytest.raises(EvalSetError, match="verbatim registry text"):
        load_eval_set(path)


def test_a_label_nobody_has_vouched_for_is_not_handed_to_the_scoring_code(
    tmp_path: Path,
) -> None:
    """An agent may propose a label. It may not confirm one — docs/decisions/0004."""
    path = write_set(
        tmp_path,
        [
            a_pair(id="p01", needs_human_review=False),
            a_pair(id="p02", needs_human_review=True, reviewed_by=""),
            a_pair(id="p03", needs_human_review=True, reviewed_by="a person"),
        ],
    )
    eval_set = load_eval_set(path)

    assert [p.id for p in eval_set.scorable_pairs()] == ["p01", "p03"]
    assert [p.id for p in eval_set.held_back()] == ["p02"]


def test_every_label_must_state_its_reasoning(tmp_path: Path) -> None:
    """A label with no basis cannot be argued with, so it cannot be checked."""
    path = write_set(tmp_path, [a_pair(basis="")])
    with pytest.raises(EvalSetError, match="no stated basis"):
        load_eval_set(path)


def test_duplicate_pair_ids_are_refused(tmp_path: Path) -> None:
    path = write_set(tmp_path, [a_pair(id="p01"), a_pair(id="p01")])
    with pytest.raises(EvalSetError, match="duplicate"):
        load_eval_set(path)


def test_an_unknown_verdict_is_refused(tmp_path: Path) -> None:
    path = write_set(tmp_path, [a_pair(expected="PROBABLY")])
    with pytest.raises(EvalSetError, match="unknown verdict"):
        load_eval_set(path)


def test_an_empty_set_is_refused(tmp_path: Path) -> None:
    with pytest.raises(EvalSetError, match="no pairs"):
        load_eval_set(write_set(tmp_path, []))


# --------------------------------------------------------------------------
# The shipped set
# --------------------------------------------------------------------------


def test_the_shipped_set_loads_and_is_about_the_right_size() -> None:
    eval_set = load_current()
    assert 25 <= len(eval_set.pairs) <= 45
    assert eval_set.version == "criteria_v1"


def test_every_shipped_criterion_is_real_registry_text() -> None:
    """Guaranteed by the loader, asserted here so the guarantee is visible."""
    eval_set = load_current()
    assert eval_set.pairs
    for pair in eval_set.pairs:
        assert pair.criterion.strip()
        assert pair.nct_id.startswith("NCT")


def test_the_shipped_set_covers_all_three_verdicts() -> None:
    """A set with no NOT_MET in it cannot detect the error we care most about."""
    verdicts = {pair.expected for pair in load_current().pairs}
    assert verdicts == {Verdict.MET, Verdict.NOT_MET, Verdict.UNKNOWN}


def test_the_shipped_set_includes_an_exclusion_criterion() -> None:
    """Exclusion polarity is the thing most likely to be scored backwards."""
    kinds = {pair.kind for pair in load_current().pairs}
    assert "EXCLUSION" in kinds


def test_the_interpretive_labels_are_flagged_and_the_readable_ones_are_not() -> None:
    """The split that decides which labels a person still has to settle."""
    eval_set = load_current()
    flagged = eval_set.held_back()

    assert flagged, "some labels should need a human"
    assert len(eval_set.scorable_pairs()) > len(flagged), (
        "if most of the set needs review, the eval cannot run at all until a "
        "person works through it"
    )
    for pair in flagged:
        assert "Proposed" in pair.basis, (
            f"{pair.id} is flagged for review but its basis does not read as a proposal"
        )


def test_nobody_has_reviewed_the_shipped_set_yet() -> None:
    """Deliberately failing-on-purpose the day someone reviews it.

    This test exists to be deleted. It records the state of the set as shipped —
    proposed labels, nobody's name on them — so that the day a human reviews the
    flagged pairs, this test fails and reminds them to update the journal and any
    published number with how many pairs were actually scored.
    """
    assert all(pair.reviewed_by == "" for pair in load_current().pairs)


# --------------------------------------------------------------------------
# The profile fields (D-6) — a silent drop would be worse than a crash
# --------------------------------------------------------------------------


def test_the_reader_knows_every_field_a_profile_has() -> None:
    """A field added to `PatientProfile` and forgotten here vanishes silently.

    The pair would then be scored against a person missing the exact detail it
    was written to test, and the eval would look fine while measuring the wrong
    thing. This fails the moment the dataclass grows.
    """
    from dataclasses import fields

    from whynot.evalset import PROFILE_FIELDS
    from whynot.profile import PatientProfile

    assert set(PROFILE_FIELDS) == {f.name for f in fields(PatientProfile)}


def test_a_profile_in_the_set_keeps_every_detail_it_states(tmp_path: Path) -> None:
    rich = {
        "age_years": 38,
        "sex": "female",
        "conditions": ["relapsing-remitting multiple sclerosis"],
        "diagnosed_year": 2019,
        "current_treatments": ["ocrelizumab"],
        "past_treatments": ["interferon beta-1a"],
    }
    path = write_set(tmp_path, [a_pair(profile=rich)])
    profile = load_eval_set(path).pairs[0].profile

    assert profile.age_years == 38
    assert profile.diagnosed_year == 2019
    assert profile.current_treatments == ("ocrelizumab",)
    assert profile.past_treatments == ("interferon beta-1a",)


def test_a_misspelled_profile_field_is_refused(tmp_path: Path) -> None:
    """Silently ignoring it would test a person who is not the one described."""
    path = write_set(tmp_path, [a_pair(profile={"age_years": 41, "current_treatment": ["x"]})])
    with pytest.raises(EvalSetError, match="does not have"):
        load_eval_set(path)


def test_the_shipped_set_exercises_the_treatment_fields() -> None:
    """D-6's reason for existing: before it, no pair could resolve on treatment."""
    pairs = load_current().pairs
    with_treatments = [
        p for p in pairs if p.profile.past_treatments or p.profile.current_treatments
    ]

    assert with_treatments, "the set should contain somebody with a treatment history"
    settled = [p for p in with_treatments if p.expected is not Verdict.UNKNOWN]
    assert settled, "and at least one of them should resolve to something other than UNKNOWN"
