r"""Tests for the eligibility-criteria splitter.

Every blob used here is real registry text, recorded by
`tools/record_fixtures.py`. The seventeen fixture records between them cover
tidy bulleted lists, numbered lists, markdown-escaped numbering, bulleted
headers, cohort-split headers, deeply nested sub-bullets and blobs with no
headers at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from whynot.criteria import (
    Criterion,
    CriterionKind,
    exclusion_criteria,
    inclusion_criteria,
    split_criteria,
    unescape,
)
from whynot.registry import parse_study

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"


def _all_fixture_studies() -> dict:
    studies = {}
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        payload = json.loads(path.read_text())
        for record in payload.get("studies", [payload]):
            study = parse_study(record)
            studies[study.nct_id] = study
    return studies


@pytest.fixture(scope="module")
def studies() -> dict:
    return _all_fixture_studies()


@pytest.fixture(scope="module")
def blobs(studies) -> dict:
    return {nct: study.eligibility.criteria_text for nct, study in studies.items()}


def split(blobs: dict, nct_id: str) -> tuple[Criterion, ...]:
    return split_criteria(blobs[nct_id])


# --------------------------------------------------------------------------
# The promise that makes quoting safe
# --------------------------------------------------------------------------


def test_every_source_text_appears_verbatim_in_the_registry_blob(blobs):
    """Rigor rule 2. If this fails, a quote shown to a user is not registry text."""
    for nct_id, blob in blobs.items():
        normalised = blob.replace("\r\n", "\n").replace("\r", "\n")
        for criterion in split_criteria(blob):
            assert criterion.source_text in normalised, f"{nct_id} #{criterion.index}"


def test_criteria_come_back_in_source_order(blobs):
    for blob in blobs.values():
        normalised = blob.replace("\r\n", "\n").replace("\r", "\n")
        position = -1
        for criterion in split_criteria(blob):
            found = normalised.index(criterion.source_text, position + 1)
            assert found > position
            position = found


def test_no_criterion_is_empty_and_every_record_yields_several(blobs):
    for nct_id, blob in blobs.items():
        criteria = split_criteria(blob)
        assert len(criteria) >= 3, f"{nct_id} split into only {len(criteria)}"
        for criterion in criteria:
            assert criterion.text.strip(), f"{nct_id} #{criterion.index} is blank"


def test_headers_never_become_criteria(blobs):
    for nct_id, blob in blobs.items():
        for criterion in split_criteria(blob):
            first_line = criterion.text.splitlines()[0].strip().lower()
            assert first_line not in {
                "inclusion criteria:",
                "exclusion criteria:",
                "inclusion criteria",
                "exclusion criteria",
            }, f"{nct_id} kept a header as a criterion"


# --------------------------------------------------------------------------
# Six real records, each a different shape
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nct_id", "shape", "inclusions", "exclusions"),
    [
        ("NCT07000786", "plain headers, asterisk bullets", 3, 2),
        ("NCT06096870", "the header itself is a bullet, and is SHOUTED", 13, 8),
        ("NCT06433752", "numbered list, '1.' '2.'", 2, 3),
        ("NCT06737159", "markdown-escaped numbering, '1\\.'", 4, 1),
        ("NCT01271491", "four headers: inclusion/exclusion x cases/controls", 5, 6),
        ("NCT06408259", "roman-numeral sub-items and a '\\-' bullet", 5, 4),
        ("NCT00113191", "2004-era record, deeply nested sub-bullets", 4, 7),
    ],
)
def test_real_records_of_differing_shape_split_as_expected(
    blobs, nct_id, shape, inclusions, exclusions
):
    criteria = split(blobs, nct_id)
    assert len(inclusion_criteria(criteria)) == inclusions, shape
    assert len(exclusion_criteria(criteria)) == exclusions, shape


# --------------------------------------------------------------------------
# Individual behaviours, each pinned to the record that motivated it
# --------------------------------------------------------------------------


def test_a_bulleted_shouted_header_is_still_a_header(blobs):
    """NCT06096870 writes its header as `* INCLUSION CRITERIA:`."""
    criteria = split(blobs, "NCT06096870")
    assert criteria[0].kind is CriterionKind.INCLUSION
    assert criteria[0].text.startswith("Participant must provide documentation")


def test_indented_sub_bullets_are_folded_into_the_criterion_above(blobs):
    """'Platelets >=100,000/microliter' is meaningless as a standalone criterion."""
    criteria = split(blobs, "NCT06096870")
    organ_function = next(c for c in criteria if "adequate organ and marrow" in c.text)
    assert "Platelets" in organ_function.text
    assert "Serum albumin" in organ_function.text
    assert not any(c.text.strip().startswith("Platelets") for c in criteria)


def test_cohort_split_headers_switch_kind_each_time(blobs):
    """NCT01271491 has inclusion and exclusion headers twice: cases, then controls."""
    kinds = [c.kind for c in split(blobs, "NCT01271491")]
    assert kinds[0] is CriterionKind.INCLUSION
    assert CriterionKind.INCLUSION in kinds[3:], "the second cohort's inclusions were lost"


def test_a_blob_with_no_headers_is_unclassified_not_guessed(blobs):
    """NCT00132080 starts straight into bullets. We say so instead of assuming."""
    criteria = split(blobs, "NCT00132080")
    assert criteria
    assert all(c.kind is CriterionKind.UNCLASSIFIED for c in criteria)


def test_a_lead_in_sentence_is_not_treated_as_a_criterion(blobs):
    """NCT06737159 says 'Children eligible ... must fulfil all of the following:'."""
    criteria = split(blobs, "NCT06737159")
    assert not any(c.text.startswith("Children eligible for the trial") for c in criteria)
    assert any(c.text.startswith("Children admitted to the hospital") for c in criteria)


def test_markdown_escapes_are_removed_from_text_but_kept_in_the_source(blobs):
    criteria = split(blobs, "NCT06096870")
    testosterone = next(c for c in criteria if "Testosterone" in c.text)
    assert testosterone.text == "Testosterone >100 ng/dL."
    assert "\\>" in testosterone.source_text


def test_unescape_handles_the_punctuation_the_registry_escapes():
    assert unescape(r"m\^2 \[HBV\] \<2 \>=18 \*note\* \- dash") == "m^2 [HBV] <2 >=18 *note* - dash"


# --------------------------------------------------------------------------
# Degenerate input
# --------------------------------------------------------------------------


@pytest.mark.parametrize("blob", ["", "   ", "\n\n\n"])
def test_an_empty_blob_produces_no_criteria(blob):
    assert split_criteria(blob) == ()


def test_a_single_unbulleted_paragraph_becomes_one_criterion():
    criteria = split_criteria("Adults with type 2 diabetes who are not pregnant.")
    assert len(criteria) == 1
    assert criteria[0].kind is CriterionKind.UNCLASSIFIED
    assert criteria[0].text == "Adults with type 2 diabetes who are not pregnant."


def test_a_header_with_nothing_under_it_produces_nothing():
    assert split_criteria("Inclusion Criteria:\n\nExclusion Criteria:\n") == ()


def test_windows_line_endings_do_not_break_source_quoting():
    blob = "Inclusion Criteria:\r\n\r\n* Age over 18\r\n* Able to consent\r\n"
    criteria = split_criteria(blob)
    assert len(criteria) == 2
    assert criteria[0].text == "Age over 18"
    assert criteria[0].source_text == "* Age over 18"
