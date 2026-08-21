"""The HTTP layer for the deterministic half of the pipeline.

`docs/PLAN.md` splits the work in two. Steps 3, 4 and 6 — query the registry,
filter on the structured fields, and sort — are arithmetic, and are done in plain
Python. Only step 5, reading the free-text eligibility criteria, is allowed to
involve a model. **This module is entirely the first kind.** It makes no model
call, holds no API key, and does not import a model client; `tests/test_api.py`
asserts all three, because "the search path stays deterministic" is a claim that
rots the moment nobody is checking it.

The judge endpoint is a separate task (W2-2b) and is blocked until there is a key
to make it with.

Run it:

    uv run uvicorn whynot.api:app --reload

Two endpoints:

    GET  /api/health   is the server up
    POST /api/search   condition + where you are + what you told us  ->  trials

What comes back per trial is deliberately raw material rather than a verdict: the
registry's own facts, the three structured-field checks with the sentence each
came from, and every eligibility criterion with the exact text it was cut from so
the interface can quote it. Nothing here decides that a person is eligible — see
`DISCLAIMER`, and rigor rule 1 in the plan.

**Nothing is written to disk.** The profile arrives in the request body, is used
for one search, and is never stored (rigor rule 4). The response cache is off
unless `WHYNOT_CACHE_DB` is set, which is for the eval and the fixture recorder,
not for a server answering real people — `docs/decisions/0005` explains why that
default changed.

**What does leave this machine:** the condition and the coordinates go to
ClinicalTrials.gov, because that is how the search works. The age, sex and
healthy-volunteer answers do **not** — they never leave this server, and are used
only to compare against what the registry sends back. The interface says so in
those words rather than claiming nothing is sent anywhere.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from whynot.criteria import Criterion, split_criteria
from whynot.hardfilter import HardCheck, describe_age_range, hard_filter
from whynot.nonpatient import CAUTION, assess
from whynot.profile import PatientProfile
from whynot.questions import open_questions
from whynot.ranking import rank_studies
from whynot.registry import RegistryClient, RegistryError, ResponseCache, Study

#: Rigor rule 1, in the plan's own words, and owned here rather than in the
#: interface. Any client of this API — the web page, the printable sheet, a
#: future one — gets the same sentence, and cannot render results without it.
#: `tests/test_api.py` pins the exact phrase.
DISCLAIMER = (
    "You may qualify — only the study team can confirm. This tool reads the "
    "public ClinicalTrials.gov registry and cannot check everything a trial "
    "requires, so anything it is unsure about is a question to ask them."
)

#: Off unless somebody asks for it. See `docs/decisions/0005`.
#:
#: The cache stores each registry response body and the time it arrived. Nothing
#: a user typed is written down verbatim — but the *response* to "multiple
#: sclerosis near Portland" is a list of multiple sclerosis trials in Portland,
#: so what was searched for is plain to anyone reading the file. Rigor rule 4
#: says nothing is stored server-side, and the interface tells people so.
#:
#: The cache exists for reproducibility — a demo re-run, an eval re-run and the
#: fixture recorder all wanting the same bytes — and every one of those has an
#: operator rather than a patient. So it is opt-in: set WHYNOT_CACHE_DB and you
#: get it. A server answering real people persists nothing.
CACHE_PATH = os.environ.get("WHYNOT_CACHE_DB")

app = FastAPI(
    title="Why Not This Trial",
    summary="Clinical-trial search that explains why you might not qualify.",
    version="0.1.0",
)


# --------------------------------------------------------------------------
# The registry client, injected so tests can serve recorded fixtures
# --------------------------------------------------------------------------


def get_registry_client() -> Iterator[RegistryClient]:
    """One registry client per request.

    Declared as a FastAPI dependency rather than a module-level global so the
    tests can replace it with a client whose HTTP layer reads fixtures off disk.
    Production and tests then run the identical code path.
    """
    client = RegistryClient(cache=ResponseCache(CACHE_PATH) if CACHE_PATH else None)
    try:
        yield client
    finally:
        client.close()


# --------------------------------------------------------------------------
# What a caller sends
# --------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """A condition, a place, and whatever the person chose to tell us.

    Every field describing the person is optional, and that is the product's
    whole argument: a blank field produces `UNKNOWN` and a question for the study
    coordinator, never a guess. See `whynot/profile.py`.
    """

    condition: str = Field(min_length=1, description="e.g. 'multiple sclerosis'")
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_miles: int = Field(default=50, ge=1, le=500)
    recruiting_only: bool = True
    max_results: int = Field(default=20, ge=1, le=50)

    age_years: float | None = Field(default=None, ge=0, le=130)
    sex: str | None = None
    is_healthy_volunteer: bool | None = None
    conditions: list[str] = Field(default_factory=list)

    def to_profile(self) -> PatientProfile:
        return PatientProfile(
            age_years=self.age_years,
            sex=self.sex,
            is_healthy_volunteer=self.is_healthy_volunteer,
            conditions=tuple(self.conditions),
        )


# --------------------------------------------------------------------------
# What a caller gets back
# --------------------------------------------------------------------------


class CheckOut(BaseModel):
    """One structured-field decision, with the registry wording behind it."""

    field: str
    verdict: str
    reason: str
    source: str | None


class CriterionOut(BaseModel):
    """One eligibility criterion. `source_text` is verbatim so it can be quoted."""

    index: int
    kind: str
    text: str
    source_text: str


class SignalOut(BaseModel):
    """One piece of evidence that a study may not enrol individual people."""

    name: str
    explanation: str
    quote: str | None


class NonPatientNoticeOut(BaseModel):
    """Shown only when at least two signals agree. See `docs/decisions/0003`."""

    caution: str
    signals: list[SignalOut]


class CoordinatorQuestionOut(BaseModel):
    """Something only the study team can answer, ready to be read down a phone."""

    question: str
    because: str
    source: str | None


class SelfAnswerableOut(BaseModel):
    """Something the person could tell us — points at a chip they can edit."""

    field: str
    prompt: str


class SiteOut(BaseModel):
    """The site closest to the caller — never simply the first one listed."""

    facility: str | None
    label: str
    city: str | None
    state: str | None
    country: str | None
    status: str | None
    distance_miles: float


class TrialOut(BaseModel):
    nct_id: str
    brief_title: str
    official_title: str | None
    overall_status: str | None
    study_type: str | None
    phases: list[str]
    lead_sponsor: str | None
    conditions: list[str]
    enrollment_count: int | None
    #: Rigor rule 5 — always link out, because our copy goes stale.
    url: str
    last_update_post_date: str | None
    status_verified_date: str | None

    age_range: str
    sex: str
    accepts_healthy_volunteers: bool | None

    hard_checks: list[CheckOut]
    #: True when a *structured* field rules the person out — an age or sex bound,
    #: never an interpretation of the free text. The criteria are not judged here.
    ruled_out_by_structured_fields: bool
    criteria: list[CriterionOut]

    #: W3-3. Split by who can answer: the study team, or the person themselves.
    #: Questions raised by the free-text criteria are W3-3b and need the judge.
    questions_for_the_study_team: list[CoordinatorQuestionOut]
    you_could_tell_us: list[SelfAnswerableOut]

    #: W3-4. Present only when the study looks like it enrols clinics or health
    #: systems rather than people. Never used to hide or reorder the trial.
    may_not_enrol_individuals: NonPatientNoticeOut | None

    nearest_site: SiteOut | None
    site_count: int


class SearchResponse(BaseModel):
    disclaimer: str
    total_count: int | None
    returned: int
    #: Ranked by `whynot/ranking.py`: no structured conflict first, then nearest,
    #: then phase, then NCT id. Trials the person conflicts with are ranked down
    #: and still returned — see `docs/decisions/0002`.
    trials: list[TrialOut]


# --------------------------------------------------------------------------
# Turning our dataclasses into the response shape
# --------------------------------------------------------------------------


def _check_out(check: HardCheck) -> CheckOut:
    return CheckOut(
        field=check.field,
        verdict=check.verdict.value,
        reason=check.reason,
        source=check.source,
    )


def _criterion_out(criterion: Criterion) -> CriterionOut:
    return CriterionOut(
        index=criterion.index,
        kind=criterion.kind.value,
        text=criterion.text,
        source_text=criterion.source_text,
    )


def _nearest_site_out(study: Study, request: SearchRequest) -> SiteOut | None:
    """The closest site to the caller, or None if we cannot work it out.

    The geo trap from `docs/PLAN.md`: the registry filters which *studies* match a
    radius, then returns **every** site worldwide for each one. Showing
    `locations[0]` puts an Alabama clinic at the top of a Portland user's results.
    Distance is computed here, from the caller's own coordinates.
    """
    if request.latitude is None or request.longitude is None:
        return None
    nearest = study.nearest_location(request.latitude, request.longitude)
    if nearest is None:
        return None
    location, miles = nearest
    return SiteOut(
        facility=location.facility,
        label=location.label,
        city=location.city,
        state=location.state,
        country=location.country,
        status=location.status,
        distance_miles=round(miles, 1),
    )


def _non_patient_out(study: Study) -> NonPatientNoticeOut | None:
    """The caution, or nothing at all when the evidence does not corroborate."""
    assessment = assess(study)
    if not assessment.looks_like_organisations:
        return None
    return NonPatientNoticeOut(
        caution=CAUTION,
        signals=[
            SignalOut(name=s.name, explanation=s.explanation, quote=s.quote)
            for s in assessment.signals
        ],
    )


def build_trial(study: Study, request: SearchRequest) -> TrialOut:
    """Everything the interface needs about one trial, and nothing invented."""
    profile = request.to_profile()
    result = hard_filter(study, profile)
    questions = open_questions(study, profile)
    return TrialOut(
        nct_id=study.nct_id,
        brief_title=study.brief_title,
        official_title=study.official_title,
        overall_status=study.overall_status,
        study_type=study.study_type,
        phases=list(study.phases),
        lead_sponsor=study.lead_sponsor,
        conditions=list(study.conditions),
        enrollment_count=study.enrollment_count,
        url=study.url,
        last_update_post_date=study.last_update_post_date,
        status_verified_date=study.status_verified_date,
        age_range=describe_age_range(study.eligibility),
        sex=study.eligibility.sex or "ALL",
        accepts_healthy_volunteers=study.eligibility.healthy_volunteers,
        hard_checks=[_check_out(c) for c in result.checks],
        ruled_out_by_structured_fields=result.is_ruled_out,
        criteria=[_criterion_out(c) for c in split_criteria(study.eligibility.criteria_text)],
        questions_for_the_study_team=[
            CoordinatorQuestionOut(question=q.question, because=q.because, source=q.source)
            for q in questions.for_the_study_team
        ],
        you_could_tell_us=[
            SelfAnswerableOut(field=item.field, prompt=item.prompt)
            for item in questions.you_could_tell_us
        ],
        may_not_enrol_individuals=_non_patient_out(study),
        nearest_site=_nearest_site_out(study, request),
        site_count=len(study.locations),
    )


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    client: Annotated[RegistryClient, Depends(get_registry_client)],
) -> SearchResponse:
    try:
        found = client.search(
            request.condition,
            status=("RECRUITING",) if request.recruiting_only else (),
            latitude=request.latitude,
            longitude=request.longitude,
            radius_miles=request.radius_miles,
            page_size=request.max_results,
        )
    except RegistryError as exc:
        # The registry being unreachable is not our bug and not the user's
        # fault; say which upstream failed rather than returning a bare 500.
        raise HTTPException(
            status_code=502, detail=f"ClinicalTrials.gov did not answer: {exc}"
        ) from exc

    ordered = rank_studies(found.studies, request.to_profile(), request.latitude, request.longitude)
    trials = [build_trial(study, request) for study in ordered]
    return SearchResponse(
        disclaimer=DISCLAIMER,
        total_count=found.total_count,
        returned=len(trials),
        trials=trials,
    )


# --------------------------------------------------------------------------
# Serving the built interface (W5-5)
# --------------------------------------------------------------------------

#: Where `npm run build` puts the interface. Present in the container image and
#: after a local `just web-check`; absent on a machine that has only ever run the
#: Python side, which is why none of this is required for the API to start.
WEB_DIST = Path(__file__).resolve().parents[1] / "web" / "dist"


def mount_web_interface(application: FastAPI, dist: Path = WEB_DIST) -> bool:
    """Serve the built page from the same origin as the API.

    Same origin is the whole point, and it is a security decision rather than a
    convenience one: the alternative is enabling cross-origin requests on the
    API, and a CORS policy is a thing that gets loosened one afternoon to unblock
    somebody and never tightened again. There is no CORS configuration anywhere
    in this project, and this is why there does not need to be.

    Returns False and changes nothing when the interface has not been built, so
    `uvicorn whynot.api:app` still works for API-only development.
    """
    if not (dist / "index.html").is_file():
        _explain_the_missing_interface(application)
        return False

    application.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @application.get("/{full_path:path}", include_in_schema=False)
    def serve_index(full_path: str) -> FileResponse:
        """Hand every unknown path to the page.

        A single-page interface owns its own routing, so `/anything` has to
        return the page rather than a 404 — otherwise a reload on any URL but
        the root breaks.

        `/api/...` is deliberately excluded. Without that, a typo in an API path
        would return HTML with a 200, and the caller would be left parsing a web
        page as JSON and wondering what happened. An unknown API path is an API
        error and says so.
        """
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"No such endpoint: /{full_path}")
        return FileResponse(dist / "index.html")

    return True


def _explain_the_missing_interface(application: FastAPI) -> None:
    """Say why there is no page here, rather than returning a bare 404.

    Somebody following the README who runs `just serve` before `just web-check`
    lands on `/` and gets a 404 with no clue whether the project is broken, the
    port is wrong, or they missed a step. A judge with ten minutes will not go
    hunting. One sentence naming the command is the whole fix.
    """

    @application.get("/", include_in_schema=False)
    def interface_not_built() -> HTMLResponse:
        return HTMLResponse(
            "<!doctype html><meta charset='utf-8'>"
            "<title>Why Not This Trial — interface not built</title>"
            '<main style="font-family: system-ui, sans-serif; max-width: 34rem; '
            'margin: 4rem auto; padding: 0 1rem; line-height: 1.6">'
            "<h1>The API is running. The page has not been built.</h1>"
            "<p>Build it, then start the server again:</p>"
            '<pre style="background:#f2f6fa; padding:1rem; border-radius:6px">'
            "just web-check\njust serve</pre>"
            "<p>The API itself is working — try "
            "<a href='/docs'>/docs</a> or <a href='/api/health'>/api/health</a>.</p>"
            "</main>",
            status_code=503,
        )


#: Done at import so a container serves the page with no extra wiring. When
#: `web/dist` is absent the API still starts, and `/` explains what to run.
mount_web_interface(app)
