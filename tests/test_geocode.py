"""Tests for turning a typed place name into coordinates.

Every response here was recorded from the real Nominatim service by
`tools/record_geocode_fixtures.py`. Nothing calls the network.

Half of these are not about geocoding at all — they are about the OSM
Foundation's usage policy, which runs on donated servers with, in their words,
"very limited capacity". A rate limit that is documented and not enforced is a
rate limit that gets exceeded by the first impatient user.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from whynot.geocode import (
    ATTRIBUTION,
    MIN_SECONDS_BETWEEN_REQUESTS,
    USER_AGENT,
    Geocoder,
    GeocodingError,
    parse_place,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "geocode"


def load(name: str) -> list:
    return json.loads((FIXTURE_DIR / name).read_text())


class FakeClock:
    """A clock and a sleep that move only when told to."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def geocoder_for(payload: list, *, record: list | None = None, clock: FakeClock | None = None):
    clock = clock or FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        if record is not None:
            record.append(request)
        return httpx.Response(200, json=payload)

    return Geocoder(
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), headers={"User-Agent": USER_AGENT}
        ),
        sleep=clock.sleep,
        clock=clock.monotonic,
    ), clock


# --------------------------------------------------------------------------
# The thing the task was filed for
# --------------------------------------------------------------------------


def test_somebody_in_tucson_can_search_near_home() -> None:
    """The whole point: the preset list of six cities never included Tucson."""
    geocoder, _ = geocoder_for(load("tucson.json"))
    places = geocoder.search("Tucson")

    assert len(places) == 1
    assert "Tucson" in places[0].name
    assert places[0].latitude == pytest.approx(32.22, abs=0.05)
    assert places[0].longitude == pytest.approx(-110.97, abs=0.05)


def test_an_ambiguous_place_returns_every_candidate() -> None:
    """ "Portland" is a real ambiguity and the person has to resolve it, not us.

    Picking the first result would silently search Oregon for somebody in Maine.
    """
    geocoder, _ = geocoder_for(load("portland.json"))
    places = geocoder.search("Portland")

    assert len(places) == 5
    names = " | ".join(p.name for p in places)
    assert "Oregon" in names
    assert "Maine" in names
    assert "Australia" in names


def test_a_place_that_does_not_exist_returns_nothing_rather_than_guessing() -> None:
    geocoder, _ = geocoder_for(load("nowhere.json"))
    assert geocoder.search("zzzzqqxnotaplace") == ()


def test_an_empty_query_never_reaches_the_service() -> None:
    requests: list[httpx.Request] = []
    geocoder, _ = geocoder_for(load("tucson.json"), record=requests)

    assert geocoder.search("   ") == ()
    assert requests == []


# --------------------------------------------------------------------------
# The usage policy, enforced rather than documented
# --------------------------------------------------------------------------


def test_requests_are_at_least_a_second_apart() -> None:
    """ "An absolute maximum of 1 request per second." Enforced, not hoped for."""
    requests: list[httpx.Request] = []
    geocoder, clock = geocoder_for(load("portland.json"), record=requests)

    geocoder.search("Portland")
    geocoder.search("Tucson")
    geocoder.search("Boston")

    assert len(requests) == 3
    # Two waits, because the first request had nothing to wait for.
    assert len(clock.slept) == 2
    assert all(waited >= MIN_SECONDS_BETWEEN_REQUESTS - 1e-9 for waited in clock.slept)


def test_time_already_spent_counts_towards_the_wait() -> None:
    """A slow lookup should not be followed by a full second of doing nothing."""
    geocoder, clock = geocoder_for(load("portland.json"))

    geocoder.search("Portland")
    clock.now += 0.75
    geocoder.search("Tucson")

    assert clock.slept == [pytest.approx(0.25)]


def test_the_user_agent_identifies_this_project() -> None:
    """Generic library defaults are explicitly not acceptable to the service."""
    requests: list[httpx.Request] = []
    geocoder, _ = geocoder_for(load("tucson.json"), record=requests)
    geocoder.search("Tucson")

    agent = requests[0].headers["user-agent"]
    assert agent == USER_AGENT
    assert "why-not-this-trial" in agent
    assert "github.com" in agent


def test_a_repeated_search_does_not_repeat_the_request() -> None:
    """The policy warns that repeating identical queries can get a client blocked."""
    requests: list[httpx.Request] = []
    geocoder, _ = geocoder_for(load("portland.json"), record=requests)

    first = geocoder.search("Portland")
    again = geocoder.search("  portland  ")

    assert first == again
    assert len(requests) == 1, "the second search should have been served from memory"


def test_the_cache_is_only_in_memory(tmp_path, monkeypatch) -> None:
    """Rigor rule 4 and `docs/decisions/0005`: nothing a user types is written down.

    A file of place names with timestamps is a record of where people were
    looking, which is exactly what that decision exists to prevent.
    """
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())

    geocoder, _ = geocoder_for(load("portland.json"))
    geocoder.search("Portland")
    geocoder.search("Portland")

    assert set(tmp_path.iterdir()) == before


def test_attribution_names_openstreetmap() -> None:
    assert "OpenStreetMap" in ATTRIBUTION


# --------------------------------------------------------------------------
# When it goes wrong
# --------------------------------------------------------------------------


def test_a_service_failure_is_reported_not_swallowed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="down")

    geocoder = Geocoder(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(GeocodingError):
        geocoder.search("Portland")


def test_a_result_missing_coordinates_is_dropped_rather_than_crashing() -> None:
    assert parse_place({"display_name": "Nowhere"}) is None
    assert parse_place({"lat": "1.0", "lon": "2.0"}) is None
    assert parse_place({"display_name": "X", "lat": "not a number", "lon": "2.0"}) is None
    assert parse_place({"display_name": "X", "lat": "1.5", "lon": "2.5"}) is not None
