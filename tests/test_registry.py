"""Tests for the ClinicalTrials.gov client.

Every response here is a real registry payload recorded by
`tools/record_fixtures.py`. Nothing calls the network.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from whynot.registry import (
    RegistryClient,
    RegistryError,
    ResponseCache,
    cache_key,
    miles_between,
    parse_study,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"

# Downtown Portland, Oregon — the point the search fixture was recorded around.
PORTLAND_LAT, PORTLAND_LON = 45.5152, -122.6784


def client_serving(payload: dict, *, record: list | None = None) -> RegistryClient:
    """A RegistryClient whose HTTP layer always answers with `payload`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if record is not None:
            record.append(request)
        return httpx.Response(200, json=payload)

    return RegistryClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))


# --------------------------------------------------------------------------
# Request building
# --------------------------------------------------------------------------


def test_search_sends_the_documented_geo_filter_syntax(load_fixture):
    requests: list[httpx.Request] = []
    client = client_serving(load_fixture("search_ms_portland.json"), record=requests)

    client.search(
        "multiple sclerosis",
        latitude=PORTLAND_LAT,
        longitude=PORTLAND_LON,
        radius_miles=50,
        page_size=5,
    )

    params = requests[0].url.params
    assert params["query.cond"] == "multiple sclerosis"
    assert params["filter.overallStatus"] == "RECRUITING"
    assert params["filter.geo"] == "distance(45.5152,-122.6784,50mi)"
    assert params["countTotal"] == "true"


def test_search_without_coordinates_sends_no_geo_filter(load_fixture):
    requests: list[httpx.Request] = []
    client = client_serving(load_fixture("search_ms_portland.json"), record=requests)

    client.search("multiple sclerosis")

    assert "filter.geo" not in requests[0].url.params


def test_fetch_study_uses_the_single_study_endpoint(load_fixture):
    requests: list[httpx.Request] = []
    client = client_serving(load_fixture("study_NCT06251323.json"), record=requests)

    client.fetch_study("nct06251323")

    assert requests[0].url.path.endswith("/studies/NCT06251323")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def test_search_parses_the_recorded_page(load_fixture):
    client = client_serving(load_fixture("search_ms_portland.json"))

    result = client.search("multiple sclerosis")

    assert result.total_count == 6
    assert len(result.studies) == 5
    first = result.studies[0]
    assert first.nct_id == "NCT06441617"
    assert first.overall_status == "RECRUITING"
    assert first.url == "https://clinicaltrials.gov/study/NCT06441617"
    assert first.eligibility.criteria_text.startswith("Inclusion Criteria:")


def test_fetch_study_parses_a_single_record(load_fixture):
    client = client_serving(load_fixture("study_NCT06251323.json"))

    study = client.fetch_study("NCT06251323")

    assert study.nct_id == "NCT06251323"
    assert study.eligibility.minimum_age == "18 Years"
    assert study.eligibility.sex == "ALL"
    assert study.eligibility.healthy_volunteers is True
    # This trial's structured fields look like a patient trial, but its criteria
    # enrol federally qualified health centres. Labelling that is W3-4's job;
    # the point here is that the client hands the text over untouched.
    assert "FQHC" in study.eligibility.criteria_text


def test_absent_age_bounds_parse_as_none(load_fixture):
    payload = load_fixture("search_ms_portland.json")
    by_id = {parse_study(s).nct_id: parse_study(s) for s in payload["studies"]}

    # NCT06433752 has a minimum age and no maximum — an extremely common shape.
    assert by_id["NCT06433752"].eligibility.minimum_age == "18 Years"
    assert by_id["NCT06433752"].eligibility.maximum_age is None


def test_a_record_with_no_nct_id_is_an_error():
    with pytest.raises(RegistryError):
        parse_study({"protocolSection": {"identificationModule": {}}})


def test_an_empty_record_does_not_crash_the_parser():
    with pytest.raises(RegistryError):
        parse_study({})


# --------------------------------------------------------------------------
# The geo trap
# --------------------------------------------------------------------------


def test_nearest_location_is_not_the_first_location(load_fixture):
    """The trap from docs/PLAN.md, demonstrated on real data.

    Every study in this fixture was selected because it has a site within 50
    miles of Portland — and every one of them lists a site thousands of miles
    away *first*. Showing `locations[0]` would put a clinic in Alabama at the top
    of a Portland user's results.
    """
    payload = load_fixture("search_ms_portland.json")
    studies = [parse_study(s) for s in payload["studies"]]

    for study in studies:
        nearest, distance = study.nearest_location(PORTLAND_LAT, PORTLAND_LON)
        assert distance <= 50, f"{study.nct_id} matched the 50mi filter but has no site within it"
        first_distance = miles_between(
            PORTLAND_LAT, PORTLAND_LON, study.locations[0].latitude, study.locations[0].longitude
        )
        assert first_distance > 50, f"{study.nct_id} happens to list its near site first"


def test_nearest_location_is_none_when_no_site_has_coordinates():
    study = parse_study(
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000000", "briefTitle": "T"},
                "contactsLocationsModule": {"locations": [{"facility": "Somewhere"}]},
            }
        }
    )
    assert study.nearest_location(PORTLAND_LAT, PORTLAND_LON) is None


def test_miles_between_matches_a_known_distance():
    # Portland OR to Seattle WA is about 145 miles great-circle.
    distance = miles_between(45.5152, -122.6784, 47.6062, -122.3321)
    assert 140 < distance < 150


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------


def test_cache_key_ignores_parameter_order():
    assert cache_key("/studies", {"a": 1, "b": 2}) == cache_key("/studies", {"b": 2, "a": 1})


def test_cache_key_changes_with_the_parameters():
    assert cache_key("/studies", {"a": 1}) != cache_key("/studies", {"a": 2})


def test_a_cached_response_is_not_fetched_twice(tmp_path, load_fixture):
    payload = load_fixture("search_ms_portland.json")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload)

    cache = ResponseCache(tmp_path / "cache.db")
    client = RegistryClient(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)), cache=cache
    )

    first = client.search("multiple sclerosis")
    second = client.search("multiple sclerosis")

    assert len(requests) == 1
    assert first == second


def test_the_cache_survives_being_reopened(tmp_path, load_fixture):
    payload = load_fixture("search_ms_portland.json")
    key = "abc123"

    cache = ResponseCache(tmp_path / "cache.db")
    cache.put(key, "https://example.invalid/studies", payload)
    cache.close()

    reopened = ResponseCache(tmp_path / "cache.db")
    assert reopened.get(key) == payload
    assert reopened.get("not-a-key") is None


# --------------------------------------------------------------------------
# Failure handling
# --------------------------------------------------------------------------


def test_a_server_error_is_retried_then_succeeds(monkeypatch, load_fixture):
    monkeypatch.setattr("whynot.registry.time.sleep", lambda _seconds: None)
    payload = load_fixture("study_NCT06251323.json")
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=payload)

    client = RegistryClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.fetch_study("NCT06251323").nct_id == "NCT06251323"
    assert len(attempts) == 2


def test_a_not_found_is_raised_immediately_and_not_retried(monkeypatch):
    monkeypatch.setattr("whynot.registry.time.sleep", lambda _seconds: None)
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(404)

    client = RegistryClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RegistryError):
        client.fetch_study("NCT99999999")
    assert len(attempts) == 1


def test_persistent_server_errors_eventually_give_up(monkeypatch):
    monkeypatch.setattr("whynot.registry.time.sleep", lambda _seconds: None)
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(500)

    client = RegistryClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RegistryError):
        client.fetch_study("NCT06251323")
    assert len(attempts) == 3


# --------------------------------------------------------------------------
# The no-network guard itself
# --------------------------------------------------------------------------


def test_the_network_guard_actually_blocks_real_requests():
    with pytest.raises(AssertionError, match="real network request"):
        httpx.Client().get("https://clinicaltrials.gov/api/v2/studies")


def test_every_recorded_fixture_is_valid_json_and_parses():
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        payload = json.loads(path.read_text())
        records = payload.get("studies", [payload])
        for record in records:
            assert parse_study(record).nct_id.startswith("NCT")


# --------------------------------------------------------------------------
# D-7: a site's own status is not the study's overall status
# --------------------------------------------------------------------------


def _study_with_sites(*sites: tuple[str, float, float]):
    """A bare study carrying only the sites a test cares about.

    Each site is `(status, latitude, longitude)`. Built by hand rather than
    recorded, because the point being tested is the *relationship* between two
    sites — a near closed one and a far open one — and no recorded fixture can be
    relied on to keep that shape when it is re-recorded.
    """
    return parse_study(
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT00000001", "briefTitle": "T"},
                "statusModule": {"overallStatus": "RECRUITING"},
                "contactsLocationsModule": {
                    "locations": [
                        {
                            "facility": f"Site {index}",
                            "city": "Somewhere",
                            "country": "United States",
                            "status": status,
                            "geoPoint": {"lat": lat, "lon": lon},
                        }
                        for index, (status, lat, lon) in enumerate(sites)
                    ]
                },
            }
        }
    )


def test_is_recruiting_is_true_only_for_recruiting():
    """`ENROLLING_BY_INVITATION` is excluded on purpose — you cannot join one."""
    study = _study_with_sites(
        ("RECRUITING", PORTLAND_LAT, PORTLAND_LON),
        ("WITHDRAWN", PORTLAND_LAT, PORTLAND_LON),
        ("NOT_YET_RECRUITING", PORTLAND_LAT, PORTLAND_LON),
        ("ENROLLING_BY_INVITATION", PORTLAND_LAT, PORTLAND_LON),
    )
    assert [loc.is_recruiting for loc in study.locations] == [True, False, False, False]


def test_a_site_with_no_stated_status_is_not_treated_as_open():
    study = _study_with_sites((None, PORTLAND_LAT, PORTLAND_LON))
    assert study.locations[0].is_recruiting is False


def test_nearest_recruiting_location_skips_the_nearer_closed_site():
    """The whole of D-7 in one assertion.

    The withdrawn site is in Portland; the enrolling one is in Seattle, about 145
    miles away. `nearest_location` must still report the Portland site, because
    that is a true fact about the trial — and `nearest_recruiting_location` must
    report Seattle, because that is the one a person can act on.
    """
    study = _study_with_sites(
        ("WITHDRAWN", PORTLAND_LAT, PORTLAND_LON),
        ("RECRUITING", 47.6062, -122.3321),
    )

    nearest, near_miles = study.nearest_location(PORTLAND_LAT, PORTLAND_LON)
    assert nearest.status == "WITHDRAWN"
    assert near_miles < 1

    open_site, open_miles = study.nearest_recruiting_location(PORTLAND_LAT, PORTLAND_LON)
    assert open_site.status == "RECRUITING"
    assert 140 < open_miles < 150


def test_nearest_recruiting_location_is_none_when_nothing_is_enrolling():
    study = _study_with_sites(
        ("WITHDRAWN", PORTLAND_LAT, PORTLAND_LON),
        ("COMPLETED", 47.6062, -122.3321),
    )
    assert study.nearest_recruiting_location(PORTLAND_LAT, PORTLAND_LON) is None
    assert study.nearest_location(PORTLAND_LAT, PORTLAND_LON) is not None
