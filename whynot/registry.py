"""Read-only client for the ClinicalTrials.gov REST API, version 2.

Everything in this module is deterministic. It fetches records, caches them,
and reshapes the handful of fields the rest of the app uses into plain
dataclasses. No model is involved and no judgement is made here.

Two facts about this API drive the design, both verified against the live
service (see `docs/PLAN.md`):

1. The API needs no key. It is public and unauthenticated.
2. `filter.geo` selects **studies**, not **sites**. A study is returned if any
   one of its locations falls inside the radius — and then the response lists
   *every* location that study has, worldwide. The first location in the list is
   frequently on another continent. Finding the nearest site is this module's
   job, which is why `Study.nearest_location` exists.
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

API_BASE_URL = "https://clinicaltrials.gov/api/v2"

#: The protocol modules we ask for. Requesting a subset keeps responses small
#: and, more usefully, keeps the recorded test fixtures readable. If you add a
#: field to a dataclass below, add its module here or it will silently be None.
STUDY_FIELDS = (
    "protocolSection.identificationModule",
    "protocolSection.statusModule",
    "protocolSection.sponsorCollaboratorsModule",
    "protocolSection.conditionsModule",
    "protocolSection.designModule",
    "protocolSection.eligibilityModule",
    "protocolSection.contactsLocationsModule",
)

MILES_PER_KM = 0.621371
EARTH_RADIUS_KM = 6371.0088


class RegistryError(RuntimeError):
    """The registry returned something we cannot use."""


# --------------------------------------------------------------------------
# Value types
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Location:
    """One site where a study is being run."""

    facility: str | None
    city: str | None
    state: str | None
    country: str | None
    status: str | None
    latitude: float | None
    longitude: float | None

    @property
    def label(self) -> str:
        """A short human-readable place name, e.g. 'Portland, Oregon, United States'."""
        parts = [p for p in (self.city, self.state, self.country) if p]
        return ", ".join(parts) if parts else (self.facility or "Unknown location")

    @property
    def is_recruiting(self) -> bool:
        """Whether this *site* is open to someone who approaches it today.

        A study's overall status and an individual site's status are different
        facts, and the registry publishes both. A study can be `RECRUITING`
        overall while the site nearest to you is `WITHDRAWN`. Only `RECRUITING`
        counts here: `ENROLLING_BY_INVITATION` is deliberately excluded, because
        a person who rings up cannot enrol themselves in one.
        """
        return self.status == "RECRUITING"


@dataclass(frozen=True)
class Eligibility:
    """The eligibility module, split the way the plan says to treat it.

    `criteria_text` is the free-text blob — the only part a model may read.
    Everything else is structured and gets decided in plain Python (W1-3).
    """

    criteria_text: str
    minimum_age: str | None
    maximum_age: str | None
    sex: str | None
    healthy_volunteers: bool | None
    std_ages: tuple[str, ...]


@dataclass(frozen=True)
class Study:
    """The fields of one registry record that this project actually uses."""

    nct_id: str
    brief_title: str
    official_title: str | None
    overall_status: str | None
    status_verified_date: str | None
    last_update_post_date: str | None
    study_type: str | None
    #: `designInfo.primaryPurpose` — TREATMENT, PREVENTION, DIAGNOSTIC,
    #: HEALTH_SERVICES_RESEARCH and so on. Added for W3-4: a study whose purpose
    #: is health services research is one of the signals that it may be enrolling
    #: clinics rather than people.
    primary_purpose: str | None
    phases: tuple[str, ...]
    enrollment_count: int | None
    conditions: tuple[str, ...]
    lead_sponsor: str | None
    eligibility: Eligibility
    locations: tuple[Location, ...]

    @property
    def url(self) -> str:
        """The public registry page. Rigor rule 5: always link out to the source."""
        return f"https://clinicaltrials.gov/study/{self.nct_id}"

    def nearest_location(self, latitude: float, longitude: float) -> tuple[Location, float] | None:
        """Return the closest site to a point and its distance in miles.

        Returns None when no location on the study carries coordinates. This is
        the fix for the geo trap described in the module docstring: the API hands
        back every site worldwide, so the caller must never assume
        ``study.locations[0]`` is anywhere near the user.
        """
        return self._nearest(latitude, longitude, self.locations)

    def nearest_recruiting_location(
        self, latitude: float, longitude: float
    ) -> tuple[Location, float] | None:
        """The closest site that is actually enrolling, or None if none is.

        Kept separate from `nearest_location` because the two answer different
        questions and a person needs both: the nearest site is a true fact about
        the trial, and the nearest *enrolling* site is the one they can act on.
        """
        recruiting = tuple(loc for loc in self.locations if loc.is_recruiting)
        return self._nearest(latitude, longitude, recruiting)

    def _nearest(
        self, latitude: float, longitude: float, locations: tuple[Location, ...]
    ) -> tuple[Location, float] | None:
        """Closest of `locations` to a point, ignoring any without coordinates."""
        candidates = [
            (loc, miles_between(latitude, longitude, loc.latitude, loc.longitude))
            for loc in locations
            if loc.latitude is not None and loc.longitude is not None
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda pair: pair[1])


@dataclass(frozen=True)
class SearchResult:
    """One page of search results."""

    studies: tuple[Study, ...]
    total_count: int | None
    next_page_token: str | None


# --------------------------------------------------------------------------
# Geography
# --------------------------------------------------------------------------


def miles_between(
    lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None
) -> float:
    """Great-circle distance in miles between two points (the haversine formula).

    Arithmetic like this is deliberately done in Python and never delegated to a
    model — see the "deterministic where it can be" section of `docs/PLAN.md`.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return math.inf
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a)) * MILES_PER_KM


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def _text(value: Any) -> str | None:
    """Normalise a JSON string field: missing, null and blank all become None."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def parse_location(raw: dict[str, Any]) -> Location:
    geo = raw.get("geoPoint") or {}
    return Location(
        facility=_text(raw.get("facility")),
        city=_text(raw.get("city")),
        state=_text(raw.get("state")),
        country=_text(raw.get("country")),
        status=_text(raw.get("status")),
        latitude=geo.get("lat"),
        longitude=geo.get("lon"),
    )


def parse_study(raw: dict[str, Any]) -> Study:
    """Turn one raw API study record into a `Study`.

    The API omits absent fields rather than sending nulls, so every lookup here
    tolerates a missing key. A trial with no upper age limit simply has no
    `maximumAge`; that is normal, not an error.
    """
    protocol = raw.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    conditions = protocol.get("conditionsModule") or {}
    eligibility = protocol.get("eligibilityModule") or {}
    contacts = protocol.get("contactsLocationsModule") or {}
    sponsor = (protocol.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}

    nct_id = _text(identification.get("nctId"))
    if not nct_id:
        raise RegistryError("study record has no nctId")

    return Study(
        nct_id=nct_id,
        brief_title=_text(identification.get("briefTitle")) or nct_id,
        official_title=_text(identification.get("officialTitle")),
        overall_status=_text(status.get("overallStatus")),
        status_verified_date=_text(status.get("statusVerifiedDate")),
        last_update_post_date=_text((status.get("lastUpdatePostDateStruct") or {}).get("date")),
        study_type=_text(design.get("studyType")),
        primary_purpose=_text((design.get("designInfo") or {}).get("primaryPurpose")),
        phases=tuple(design.get("phases") or ()),
        enrollment_count=(design.get("enrollmentInfo") or {}).get("count"),
        conditions=tuple(conditions.get("conditions") or ()),
        lead_sponsor=_text(sponsor.get("name")),
        eligibility=Eligibility(
            criteria_text=eligibility.get("eligibilityCriteria") or "",
            minimum_age=_text(eligibility.get("minimumAge")),
            maximum_age=_text(eligibility.get("maximumAge")),
            sex=_text(eligibility.get("sex")),
            healthy_volunteers=eligibility.get("healthyVolunteers"),
            std_ages=tuple(eligibility.get("stdAges") or ()),
        ),
        locations=tuple(parse_location(loc) for loc in contacts.get("locations") or ()),
    )


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------


class ResponseCache:
    """A SQLite table of raw API responses, keyed by the request that produced them.

    The registry is public and rate-limit-friendly, so this is not about being
    polite to the server. It is about reproducibility: a demo re-run, an eval
    re-run and a test all see the same bytes, and a flaky network cannot change
    an answer mid-recording.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            "  key TEXT PRIMARY KEY,"
            "  url TEXT NOT NULL,"
            "  fetched_at TEXT NOT NULL,"
            "  body TEXT NOT NULL)"
        )
        self._connection.commit()

    def get(self, key: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT body FROM responses WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, url: str, body: dict[str, Any]) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO responses (key, url, fetched_at, body) VALUES (?, ?, ?, ?)",
            (key, url, datetime.now(UTC).isoformat(), json.dumps(body)),
        )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def cache_key(path: str, params: dict[str, Any]) -> str:
    """A stable key for one request. Sorting the params makes it order-independent."""
    encoded = urllib.parse.urlencode(sorted(params.items()), doseq=False)
    return hashlib.sha256(f"GET {path}?{encoded}".encode()).hexdigest()


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------


class RegistryClient:
    """Search the registry and fetch single studies.

    The HTTP client is injected so tests can hand in an `httpx.MockTransport`
    serving recorded fixtures. There is exactly one code path — tests exercise
    the same parsing, caching and URL building that production does, they just
    get their bytes from disk instead of the internet.
    """

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        cache: ResponseCache | None = None,
        base_url: str = API_BASE_URL,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = http_client or httpx.Client(
            timeout=30.0, headers={"Accept": "application/json"}
        )
        self._owns_http = http_client is None
        self.cache = cache
        self.max_retries = max_retries

    # -- public API --------------------------------------------------------

    def search(
        self,
        condition: str,
        *,
        status: tuple[str, ...] = ("RECRUITING",),
        latitude: float | None = None,
        longitude: float | None = None,
        radius_miles: int = 50,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> SearchResult:
        """Find studies for a condition, optionally near a point.

        `radius_miles` filters which *studies* come back. It does not filter the
        locations inside them; see `Study.nearest_location`.
        """
        params: dict[str, Any] = {
            "query.cond": condition,
            "fields": ",".join(STUDY_FIELDS),
            "pageSize": page_size,
            "countTotal": "true",
        }
        if status:
            params["filter.overallStatus"] = ",".join(status)
        if latitude is not None and longitude is not None:
            params["filter.geo"] = f"distance({latitude},{longitude},{radius_miles}mi)"
        if page_token:
            params["pageToken"] = page_token

        payload = self._get("/studies", params)
        return SearchResult(
            studies=tuple(parse_study(s) for s in payload.get("studies") or ()),
            total_count=payload.get("totalCount"),
            next_page_token=payload.get("nextPageToken"),
        )

    def fetch_study(self, nct_id: str) -> Study:
        """Fetch one study by its NCT identifier."""
        nct_id = nct_id.strip().upper()
        payload = self._get(f"/studies/{nct_id}", {"fields": ",".join(STUDY_FIELDS)})
        return parse_study(payload)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> RegistryClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -- plumbing ----------------------------------------------------------

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        key = cache_key(path, params)
        if self.cache is not None:
            cached = self.cache.get(key)
            if cached is not None:
                return cached

        url = f"{self.base_url}{path}"
        payload = self._get_with_retries(url, params)

        if self.cache is not None:
            self.cache.put(key, url, payload)
        return payload

    def _get_with_retries(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """One GET, retried on 429 and 5xx with a simple doubling backoff.

        Deliberately boring: three attempts, sleeping 1s then 2s. A 404 or other
        4xx is a real answer and is raised immediately rather than retried.
        """
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self._http.get(url, params=params)
            except httpx.HTTPError as exc:  # network-level failure
                last_error = exc
            else:
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = RegistryError(
                        f"registry returned HTTP {response.status_code} for {url}"
                    )
                elif response.status_code >= 400:
                    raise RegistryError(f"registry returned HTTP {response.status_code} for {url}")
                else:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise RegistryError(f"registry returned non-JSON for {url}") from exc

            if attempt < self.max_retries - 1:
                time.sleep(2**attempt)

        raise RegistryError(
            f"registry request failed after {self.max_retries} attempts: {url}"
        ) from last_error
