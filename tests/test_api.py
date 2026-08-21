"""Tests for the deterministic search endpoint.

Every registry response here is a real payload recorded by
`tools/record_fixtures.py` and replayed through `httpx.MockTransport`. Nothing
calls the network — `tests/conftest.py` turns any attempt into a loud failure.

Three of these tests are not about HTTP at all. They pin claims the project makes
about itself: that the search path never involves a model, that the nearest site
is computed rather than guessed, and that no response ever tells a person they
are eligible. Those are the claims most likely to quietly stop being true.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from whynot.api import DISCLAIMER, app, get_registry_client
from whynot.registry import RegistryClient, RegistryError

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"

# Downtown Portland, Oregon — the point the search fixture was recorded around.
PORTLAND_LAT, PORTLAND_LON = 45.5152, -122.6784


@pytest.fixture
def search_payload() -> dict:
    return json.loads((FIXTURE_DIR / "search_ms_portland.json").read_text())


def client_for(payload: dict, *, record: list | None = None) -> TestClient:
    """A TestClient whose registry layer answers with a recorded payload."""

    def handler(request: httpx.Request) -> httpx.Response:
        if record is not None:
            record.append(request)
        return httpx.Response(200, json=payload)

    def override():
        registry = RegistryClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        try:
            yield registry
        finally:
            registry.close()

    app.dependency_overrides[get_registry_client] = override
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------
# The promises this module makes about itself
# --------------------------------------------------------------------------


def test_the_search_path_contains_no_model_call() -> None:
    """`whynot/api.py` must stay deterministic — plan, 'deterministic where it can be'.

    Checked by reading the source rather than by trusting the docstring. If
    somebody later adds a judge call to this module, this fails and points them
    at W2-2b, which is where the judge endpoint belongs.
    """
    source = (Path(__file__).resolve().parents[1] / "whynot" / "api.py").read_text()
    for forbidden in ("anthropic", "ANTHROPIC_API_KEY", "openai"):
        assert forbidden not in source, f"{forbidden} appeared on the deterministic search path"


def test_importing_the_api_pulls_in_no_model_client() -> None:
    assert "anthropic" not in sys.modules


def test_no_response_ever_claims_a_person_is_eligible(search_payload: dict) -> None:
    """Rigor rule 1. The tool says 'may qualify', and says who can actually confirm."""
    body = client_for(search_payload).post("/api/search", json={"condition": "x"}).json()

    assert body["disclaimer"] == DISCLAIMER
    # The plan's exact wording for rule 1, pinned here so the server cannot stop
    # saying it — every client renders whatever this sends.
    assert "You may qualify — only the study team can confirm." in body["disclaimer"]

    # Scanned over the trial data only. The disclaimer is the one place the
    # phrase "you are eligible" may appear, because there it is being denied.
    flat = json.dumps(body["trials"]).lower()
    for claim in ("you are eligible", "you qualify", "you match", "eligible for this"):
        assert claim not in flat


# --------------------------------------------------------------------------
# Health
# --------------------------------------------------------------------------


def test_health_reports_ok(search_payload: dict) -> None:
    assert client_for(search_payload).get("/api/health").json() == {"status": "ok"}


# --------------------------------------------------------------------------
# Search: the request reaches the registry as the plan describes
# --------------------------------------------------------------------------


def test_search_passes_the_geo_filter_and_condition_through(search_payload: dict) -> None:
    requests: list[httpx.Request] = []
    client = client_for(search_payload, record=requests)

    client.post(
        "/api/search",
        json={
            "condition": "multiple sclerosis",
            "latitude": PORTLAND_LAT,
            "longitude": PORTLAND_LON,
            "radius_miles": 50,
        },
    )

    params = requests[0].url.params
    assert params["query.cond"] == "multiple sclerosis"
    assert params["filter.overallStatus"] == "RECRUITING"
    assert params["filter.geo"] == f"distance({PORTLAND_LAT},{PORTLAND_LON},50mi)"


def test_recruiting_only_can_be_switched_off(search_payload: dict) -> None:
    requests: list[httpx.Request] = []
    client_for(search_payload, record=requests).post(
        "/api/search", json={"condition": "multiple sclerosis", "recruiting_only": False}
    )
    assert "filter.overallStatus" not in requests[0].url.params


# --------------------------------------------------------------------------
# Search: the response carries what a card needs
# --------------------------------------------------------------------------


def test_each_trial_carries_its_registry_facts_and_a_link_to_the_source(
    search_payload: dict,
) -> None:
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )

    assert body["returned"] == len(body["trials"])
    assert body["trials"], "the recorded fixture has trials in it"

    for trial in body["trials"]:
        assert trial["nct_id"].startswith("NCT")
        assert trial["brief_title"]
        # Rigor rule 5: our copy goes stale, so always link out to the registry.
        assert trial["url"] == f"https://clinicaltrials.gov/study/{trial['nct_id']}"
        assert trial["overall_status"]


def test_each_trial_carries_the_three_structured_checks_with_their_source(
    search_payload: dict,
) -> None:
    body = (
        client_for(search_payload)
        .post(
            "/api/search",
            json={"condition": "multiple sclerosis", "age_years": 41, "sex": "female"},
        )
        .json()
    )

    for trial in body["trials"]:
        fields = [check["field"] for check in trial["hard_checks"]]
        assert fields == ["age", "sex", "healthy volunteers"]
        for check in trial["hard_checks"]:
            assert check["verdict"] in {"MET", "NOT_MET", "UNKNOWN"}
            # Rigor rule 2: every reason is traceable to registry wording.
            assert check["reason"]
            assert check["source"]


def test_a_child_is_ruled_out_of_adult_trials_by_the_structured_fields(
    search_payload: dict,
) -> None:
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis", "age_years": 7})
        .json()
    )

    adult_trials = [t for t in body["trials"] if t["age_range"].startswith("18 Years")]
    assert adult_trials, "the fixture should contain at least one adults-only trial"
    for trial in adult_trials:
        assert trial["ruled_out_by_structured_fields"] is True
        age_check = next(c for c in trial["hard_checks"] if c["field"] == "age")
        assert age_check["verdict"] == "NOT_MET"
        assert "7 years old" in age_check["reason"]


def test_saying_nothing_about_yourself_produces_questions_not_exclusions(
    search_payload: dict,
) -> None:
    """The product's argument in one test: silence is UNKNOWN, never NOT_MET."""
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )

    for trial in body["trials"]:
        verdicts = {c["verdict"] for c in trial["hard_checks"]}
        assert "NOT_MET" not in verdicts
        assert trial["ruled_out_by_structured_fields"] is False


def test_criteria_come_back_split_tagged_and_quotable(search_payload: dict) -> None:
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )

    with_criteria = [t for t in body["trials"] if t["criteria"]]
    assert with_criteria, "the fixture should contain criteria text"

    for trial in with_criteria:
        for criterion in trial["criteria"]:
            assert criterion["kind"] in {"INCLUSION", "EXCLUSION", "UNCLASSIFIED"}
            assert criterion["text"]
            # The verbatim slice is what lets the interface quote the registry.
            assert criterion["source_text"]


# --------------------------------------------------------------------------
# The geo trap
# --------------------------------------------------------------------------


def test_the_site_returned_is_the_nearest_one_not_the_first_one(search_payload: dict) -> None:
    """`docs/PLAN.md`: the registry returns every site worldwide for a matching study.

    The recorded Portland search is the proof case — each of these trials lists a
    site thousands of miles away *before* its Portland site. Showing
    `locations[0]` would put that far site on a Portland user's card.
    """
    body = (
        client_for(search_payload)
        .post(
            "/api/search",
            json={
                "condition": "multiple sclerosis",
                "latitude": PORTLAND_LAT,
                "longitude": PORTLAND_LON,
            },
        )
        .json()
    )

    sited = [t for t in body["trials"] if t["nearest_site"]]
    assert sited, "the fixture's studies have located sites"

    for trial in sited:
        assert trial["nearest_site"]["distance_miles"] < 50
        # More sites exist than the one shown — that is the trap being avoided.
        assert trial["site_count"] >= 1

    raw = {
        s["protocolSection"]["identificationModule"]["nctId"]: s for s in search_payload["studies"]
    }
    checked = 0
    for trial in sited:
        first = raw[trial["nct_id"]]["protocolSection"]["contactsLocationsModule"]["locations"][0]
        if first.get("city") in (None, "Portland"):
            continue
        checked += 1
        assert trial["nearest_site"]["city"] != first.get("city"), (
            "the first listed site was returned instead of the nearest one"
        )

    # Without this the test could pass by checking nothing at all. In the
    # recorded fixture every study lists a distant site first — Washington D.C.,
    # Loma Linda, Birmingham, Los Angeles, Palo Alto — so every one of them is a
    # real case of the trap.
    assert checked == len(sited) == 5


def test_without_coordinates_there_is_no_distance_claim(search_payload: dict) -> None:
    """We would rather say nothing than say a distance we cannot compute."""
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )
    assert all(trial["nearest_site"] is None for trial in body["trials"])


# --------------------------------------------------------------------------
# Bad input and upstream failure
# --------------------------------------------------------------------------


def test_a_blank_condition_is_rejected_before_the_registry_is_called(
    search_payload: dict,
) -> None:
    requests: list[httpx.Request] = []
    response = client_for(search_payload, record=requests).post(
        "/api/search", json={"condition": ""}
    )
    assert response.status_code == 422
    assert requests == []


def test_an_impossible_latitude_is_rejected(search_payload: dict) -> None:
    response = client_for(search_payload).post(
        "/api/search", json={"condition": "x", "latitude": 999, "longitude": 0}
    )
    assert response.status_code == 422


def test_a_registry_outage_is_reported_as_an_upstream_failure() -> None:
    def override():
        class Broken:
            def search(self, *args, **kwargs):
                raise RegistryError("503 from the registry")

            def close(self):
                pass

        yield Broken()

    app.dependency_overrides[get_registry_client] = override
    response = TestClient(app).post("/api/search", json={"condition": "multiple sclerosis"})

    assert response.status_code == 502
    assert "ClinicalTrials.gov did not answer" in response.json()["detail"]


# --------------------------------------------------------------------------
# Ranking (W3-2) — the endpoint must return the ranked order, not the registry's
# --------------------------------------------------------------------------


def test_the_endpoint_returns_trials_in_ranked_order(search_payload: dict) -> None:
    from whynot.profile import PatientProfile
    from whynot.ranking import rank_studies
    from whynot.registry import parse_study

    body = (
        client_for(search_payload)
        .post(
            "/api/search",
            json={
                "condition": "multiple sclerosis",
                "latitude": PORTLAND_LAT,
                "longitude": PORTLAND_LON,
                "age_years": 41,
                "sex": "female",
            },
        )
        .json()
    )

    expected = rank_studies(
        tuple(parse_study(raw) for raw in search_payload["studies"]),
        PatientProfile(age_years=41, sex="female"),
        PORTLAND_LAT,
        PORTLAND_LON,
    )
    assert [t["nct_id"] for t in body["trials"]] == [s.nct_id for s in expected]

    # And the order is not simply the registry's, or this test proves nothing.
    registry_order = [
        raw["protocolSection"]["identificationModule"]["nctId"] for raw in search_payload["studies"]
    ]
    assert [t["nct_id"] for t in body["trials"]] != registry_order


def test_a_conflicting_trial_is_ranked_down_and_still_returned(search_payload: dict) -> None:
    """`docs/decisions/0002`: conflicts are explained, never hidden."""
    body = (
        client_for(search_payload)
        .post(
            "/api/search",
            json={
                "condition": "multiple sclerosis",
                "latitude": PORTLAND_LAT,
                "longitude": PORTLAND_LON,
                "age_years": 41,
            },
        )
        .json()
    )

    ids = [t["nct_id"] for t in body["trials"]]
    assert len(ids) == len(search_payload["studies"])
    # The paediatric trial is present, and it is last.
    assert "NCT06408259" in ids
    assert ids[-1] == "NCT06408259"
    last = body["trials"][-1]
    assert last["ruled_out_by_structured_fields"] is True


# --------------------------------------------------------------------------
# Coordinator questions (W3-3)
# --------------------------------------------------------------------------


def test_a_trial_carries_its_open_questions_split_by_who_can_answer(
    search_payload: dict,
) -> None:
    """Saying nothing about yourself should produce prompts, not questions."""
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )

    for trial in body["trials"]:
        # Nobody stated an age, so every trial with an age bound offers the chip.
        fields = [item["field"] for item in trial["you_could_tell_us"]]
        assert "age" in fields
        # And nothing about the person's own blank age is sent to a nurse.
        asked = " ".join(q["question"] for q in trial["questions_for_the_study_team"]).lower()
        assert "how old" not in asked


def test_a_fully_stated_profile_leaves_no_prompts_for_the_person(
    search_payload: dict,
) -> None:
    body = (
        client_for(search_payload)
        .post(
            "/api/search",
            json={
                "condition": "multiple sclerosis",
                "age_years": 41,
                "sex": "female",
                "is_healthy_volunteer": False,
            },
        )
        .json()
    )

    for trial in body["trials"]:
        assert trial["you_could_tell_us"] == []


def test_questions_never_claim_the_person_is_eligible(search_payload: dict) -> None:
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )

    text = json.dumps(
        [[t["questions_for_the_study_team"], t["you_could_tell_us"]] for t in body["trials"]]
    ).lower()
    for claim in ("you are eligible", "you qualify", "you don't qualify"):
        assert claim not in text


# --------------------------------------------------------------------------
# Non-patient trials (W3-4)
# --------------------------------------------------------------------------


def test_an_ordinary_search_carries_no_non_patient_caution(search_payload: dict) -> None:
    """The false positive is the failure that matters — see `docs/decisions/0003`."""
    body = (
        client_for(search_payload)
        .post("/api/search", json={"condition": "multiple sclerosis"})
        .json()
    )
    assert all(trial["may_not_enrol_individuals"] is None for trial in body["trials"])


def test_a_trial_that_enrols_health_centres_carries_the_caution_and_its_evidence() -> None:
    """`NCT06251323`, the verified example from `docs/PLAN.md`."""
    study = json.loads((FIXTURE_DIR / "study_NCT06251323.json").read_text())
    payload = {"studies": [study], "totalCount": 1}

    body = client_for(payload).post("/api/search", json={"condition": "diabetes"}).json()
    notice = body["trials"][0]["may_not_enrol_individuals"]

    assert notice is not None
    assert "may not be one you can join" in notice["caution"]
    assert len(notice["signals"]) >= 2
    assert all(signal["quote"] for signal in notice["signals"])

    # Labelled, not hidden: it is still in the results.
    assert body["returned"] == 1
    assert body["trials"][0]["nct_id"] == "NCT06251323"


# --------------------------------------------------------------------------
# Rigor rule 4 (W5-4) — nothing is stored server-side
# --------------------------------------------------------------------------


def test_a_search_writes_nothing_to_disk(search_payload: dict, tmp_path, monkeypatch) -> None:
    """The interface tells people nothing is kept. This is that promise, checked.

    Runs a search with the working directory somewhere empty and asserts nothing
    appeared. A cache file here would mean the response to "multiple sclerosis
    near Portland" — a list of MS trials in Portland — sitting on the server with
    a timestamp, which is what was searched for in all but name.
    """
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())

    response = client_for(search_payload).post(
        "/api/search",
        json={
            "condition": "multiple sclerosis",
            "latitude": PORTLAND_LAT,
            "longitude": PORTLAND_LON,
            "age_years": 41,
            "sex": "female",
        },
    )

    assert response.status_code == 200
    assert set(tmp_path.iterdir()) == before, "a search left something on disk"


def test_the_response_cache_is_off_unless_asked_for() -> None:
    """Opt-in, so a server answering real people persists nothing by default."""
    import whynot.api

    assert whynot.api.CACHE_PATH is None or os.environ.get("WHYNOT_CACHE_DB")


def test_the_person_details_are_never_sent_to_the_registry(search_payload: dict) -> None:
    """Rule 4's other half, and a claim the interface now makes in words.

    The condition and coordinates have to go to ClinicalTrials.gov — that is the
    search. Age, sex and the healthy-volunteer answer must not: they are used
    here, against what the registry sends back, and nowhere else.
    """
    requests: list[httpx.Request] = []
    client_for(search_payload, record=requests).post(
        "/api/search",
        json={
            "condition": "multiple sclerosis",
            "latitude": PORTLAND_LAT,
            "longitude": PORTLAND_LON,
            "age_years": 41,
            "sex": "female",
            "is_healthy_volunteer": True,
        },
    )

    assert requests, "the search should have reached the registry"
    outbound = str(requests[0].url).lower()
    assert "multiple+sclerosis" in outbound or "multiple%20sclerosis" in outbound
    for private in ("41", "female", "healthy"):
        assert private not in outbound, f"{private!r} was sent to ClinicalTrials.gov"


# --------------------------------------------------------------------------
# Serving the interface (W5-5)
# --------------------------------------------------------------------------


def _built_web(tmp_path):
    """A stand-in for `web/dist`, so these tests do not need npm to have run."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>Why Not This Trial</title>")
    (dist / "assets" / "app.js").write_text("console.log('hi')")
    return dist


def test_the_api_starts_without_a_built_interface(tmp_path) -> None:
    """API-only development must not require npm to have run."""
    from fastapi import FastAPI

    from whynot.api import mount_web_interface

    assert mount_web_interface(FastAPI(), tmp_path / "not-built") is False


def test_an_unknown_path_returns_the_page_so_a_reload_does_not_break(tmp_path) -> None:
    from fastapi import FastAPI

    from whynot.api import mount_web_interface

    application = FastAPI()
    assert mount_web_interface(application, _built_web(tmp_path)) is True

    response = TestClient(application).get("/some/deep/link")
    assert response.status_code == 200
    assert "Why Not This Trial" in response.text


def test_an_unknown_api_path_is_an_api_error_not_a_web_page(tmp_path) -> None:
    """Otherwise a typo returns HTML with a 200 and the caller parses a page as JSON."""
    from fastapi import FastAPI

    from whynot.api import mount_web_interface

    application = FastAPI()
    mount_web_interface(application, _built_web(tmp_path))

    response = TestClient(application).get("/api/serch")
    assert response.status_code == 404
    assert "No such endpoint" in response.json()["detail"]
    assert "<!doctype html>" not in response.text.lower()


def test_the_interface_and_the_api_share_one_origin(tmp_path) -> None:
    """Which is why no CORS configuration exists anywhere in this project."""
    import whynot.api

    source = (Path(whynot.api.__file__)).read_text()
    assert "CORSMiddleware" not in source
    assert "allow_origins" not in source


def test_an_unbuilt_interface_explains_itself_instead_of_404ing(tmp_path) -> None:
    """A judge who runs `just serve` before `just web-check` should be told why."""
    from fastapi import FastAPI

    from whynot.api import mount_web_interface

    application = FastAPI()
    assert mount_web_interface(application, tmp_path / "not-built") is False

    response = TestClient(application).get("/")
    assert response.status_code == 503
    assert "just web-check" in response.text
    # And it must not pretend the whole thing is broken — the API is fine.
    assert "/api/health" in response.text
