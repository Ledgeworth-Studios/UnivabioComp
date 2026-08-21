"""Tests for the order trials are shown in.

Most of these build small `Study` objects by hand rather than using recorded
fixtures. That is deliberate: ranking is about the *relationships* between
trials — this one has a conflict, that one is nearer — and a fixture that happens
to contain the right combination today is a fixture that stops testing anything
the day it is re-recorded. The last test uses the real Portland fixture to check
that the whole endpoint agrees with the module.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from whynot.hardfilter import hard_filter
from whynot.profile import PatientProfile
from whynot.ranking import (
    UNKNOWN_PHASE,
    distance_to_nearest_site,
    phase_rank,
    rank_studies,
)
from whynot.registry import Eligibility, Location, Study, parse_study

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"
PORTLAND_LAT, PORTLAND_LON = 45.5152, -122.6784

ADULT = PatientProfile(age_years=41, sex="female")


def make_study(
    nct_id: str,
    *,
    minimum_age: str | None = "18 Years",
    maximum_age: str | None = None,
    sex: str = "ALL",
    phases: tuple[str, ...] = ("PHASE3",),
    sites: tuple[tuple[float, float], ...] = ((PORTLAND_LAT, PORTLAND_LON),),
) -> Study:
    """A study with only the fields ranking looks at. Everything else is filler."""
    return Study(
        nct_id=nct_id,
        brief_title=f"Study {nct_id}",
        official_title=None,
        overall_status="RECRUITING",
        status_verified_date=None,
        last_update_post_date=None,
        study_type="INTERVENTIONAL",
        primary_purpose="TREATMENT",
        phases=phases,
        enrollment_count=None,
        conditions=(),
        lead_sponsor=None,
        eligibility=Eligibility(
            criteria_text="",
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            sex=sex,
            healthy_volunteers=False,
            std_ages=(),
        ),
        locations=tuple(
            Location(
                facility=f"Site {index}",
                city="Somewhere",
                state=None,
                country="United States",
                status="RECRUITING",
                latitude=lat,
                longitude=lon,
            )
            for index, (lat, lon) in enumerate(sites)
        ),
    )


def order(*studies: Study, profile: PatientProfile = ADULT, at_portland: bool = True) -> list[str]:
    ranked = rank_studies(
        studies,
        profile,
        PORTLAND_LAT if at_portland else None,
        PORTLAND_LON if at_portland else None,
    )
    return [study.nct_id for study in ranked]


# --------------------------------------------------------------------------
# The first rule: a conflict sends a trial down, and never off the list
# --------------------------------------------------------------------------


def test_a_trial_the_person_conflicts_with_sorts_below_one_they_do_not() -> None:
    paediatric = make_study("NCT00000002", minimum_age="10 Years", maximum_age="17 Years")
    adult = make_study("NCT00000001")

    assert order(paediatric, adult) == ["NCT00000001", "NCT00000002"]


def test_nothing_is_ever_dropped_by_ranking() -> None:
    """`docs/decisions/0002`. Hiding a conflict is the one thing this tool must not do."""
    studies = (
        make_study("NCT00000001", minimum_age="10 Years", maximum_age="17 Years"),
        make_study("NCT00000002", sex="MALE"),
        make_study("NCT00000003"),
    )
    ranked = rank_studies(studies, ADULT, PORTLAND_LAT, PORTLAND_LON)

    assert len(ranked) == len(studies)
    assert {s.nct_id for s in ranked} == {s.nct_id for s in studies}
    # And the conflicted ones really are conflicted, so the test is about ranking
    # rather than about three trials that all happen to be fine.
    conflicted = [s.nct_id for s in studies if hard_filter(s, ADULT).is_ruled_out]
    assert sorted(conflicted) == ["NCT00000001", "NCT00000002"]


def test_a_conflict_outranks_distance() -> None:
    """A conflicting trial next door still sorts below a clean one far away."""
    near_conflict = make_study(
        "NCT00000002",
        minimum_age="10 Years",
        maximum_age="17 Years",
        sites=((PORTLAND_LAT, PORTLAND_LON),),
    )
    far_clean = make_study("NCT00000001", sites=((42.3601, -71.0589),))  # Boston

    assert order(near_conflict, far_clean) == ["NCT00000001", "NCT00000002"]


# --------------------------------------------------------------------------
# The second rule: nearer first
# --------------------------------------------------------------------------


def test_nearer_sites_come_first() -> None:
    boston = make_study("NCT00000001", sites=((42.3601, -71.0589),))
    portland = make_study("NCT00000002", sites=((PORTLAND_LAT, PORTLAND_LON),))
    chicago = make_study("NCT00000003", sites=((41.8781, -87.6298),))

    assert order(boston, portland, chicago) == [
        "NCT00000002",
        "NCT00000003",
        "NCT00000001",
    ]


def test_distance_is_measured_to_the_nearest_site_not_the_first_one() -> None:
    """The geo trap again, this time as it affects the order rather than the card."""
    boston_then_portland = make_study(
        "NCT00000001", sites=((42.3601, -71.0589), (PORTLAND_LAT, PORTLAND_LON))
    )
    chicago_only = make_study("NCT00000002", sites=((41.8781, -87.6298),))

    assert order(boston_then_portland, chicago_only) == ["NCT00000001", "NCT00000002"]


def test_a_study_with_no_located_site_sorts_last_not_first() -> None:
    """Unknown distance must never beat a real one. Zero would be a lie."""
    nowhere = make_study("NCT00000001", sites=())
    portland = make_study("NCT00000002", sites=((PORTLAND_LAT, PORTLAND_LON),))

    assert distance_to_nearest_site(nowhere, PORTLAND_LAT, PORTLAND_LON) == math.inf
    assert order(nowhere, portland) == ["NCT00000002", "NCT00000001"]


def test_with_no_coordinates_every_distance_is_unknown_and_the_order_still_settles() -> None:
    a = make_study("NCT00000002", sites=((PORTLAND_LAT, PORTLAND_LON),))
    b = make_study("NCT00000001", sites=((42.3601, -71.0589),))

    # Nothing to compare, so it falls through to phase and then the identifier.
    assert order(a, b, at_portland=False) == ["NCT00000001", "NCT00000002"]


# --------------------------------------------------------------------------
# The third rule: phase, as a tie-break and not as advice
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phases", "expected"),
    [
        (("EARLY_PHASE1",), 0),
        (("PHASE1",), 1),
        (("PHASE2",), 2),
        (("PHASE3",), 3),
        (("PHASE4",), 4),
        (("NA",), UNKNOWN_PHASE),
        ((), UNKNOWN_PHASE),
        (("SOMETHING_NEW",), UNKNOWN_PHASE),
        # A study listed as phase 1/2 sorts with the phase 1 studies.
        (("PHASE1", "PHASE2"), 1),
    ],
)
def test_phase_rank(phases: tuple[str, ...], expected: int) -> None:
    assert phase_rank(phases) == expected


def test_phase_breaks_a_tie_between_equally_close_trials() -> None:
    late = make_study("NCT00000001", phases=("PHASE4",))
    early = make_study("NCT00000002", phases=("PHASE1",))

    assert order(late, early) == ["NCT00000002", "NCT00000001"]


def test_a_study_with_no_phase_sorts_after_every_stated_phase() -> None:
    none_stated = make_study("NCT00000001", phases=("NA",))
    phase4 = make_study("NCT00000002", phases=("PHASE4",))

    assert order(none_stated, phase4) == ["NCT00000002", "NCT00000001"]


# --------------------------------------------------------------------------
# The order must be total: two identical calls cannot differ
# --------------------------------------------------------------------------


def test_trials_alike_in_every_ranked_respect_are_ordered_by_identifier() -> None:
    b = make_study("NCT00000002")
    a = make_study("NCT00000001")
    c = make_study("NCT00000003")

    assert order(b, a, c) == ["NCT00000001", "NCT00000002", "NCT00000003"]


def test_the_same_input_always_produces_the_same_order() -> None:
    studies = (
        make_study("NCT00000003", phases=("PHASE1",)),
        make_study("NCT00000001", minimum_age="10 Years", maximum_age="17 Years"),
        make_study("NCT00000002", sites=()),
    )
    first = order(*studies)
    for _ in range(5):
        assert order(*studies) == first


# --------------------------------------------------------------------------
# Against a real recorded search
# --------------------------------------------------------------------------


def test_the_paediatric_trial_sinks_below_the_adult_ones_in_real_data() -> None:
    payload = json.loads((FIXTURE_DIR / "search_ms_portland.json").read_text())
    studies = tuple(parse_study(raw) for raw in payload["studies"])

    ranked = rank_studies(studies, ADULT, PORTLAND_LAT, PORTLAND_LON)
    ids = [study.nct_id for study in ranked]

    # NCT06408259 enrols 10-17 year olds; our person is 41.
    assert ids[-1] == "NCT06408259"
    assert len(ids) == len(studies)
