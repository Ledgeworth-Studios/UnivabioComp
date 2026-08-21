"""Turning a typed place name into coordinates.

The registry's distance filter needs a latitude and longitude. Asking a person to
type coordinates is not a product, so until now the interface offered six
hard-coded cities — honest for a skeleton, useless to anybody in Tucson.

This asks **Nominatim**, the OpenStreetMap Foundation's geocoder. It is free, it
needs no key, and it is run on donated servers with, in the Foundation's own
words, "very limited capacity". Their usage policy is therefore not a formality,
and it shapes this module more than the problem does. `docs/decisions/0007`
records the reasoning; the four things the policy demands are:

**At most one request per second.** Enforced in `_wait_for_turn` rather than
hoped for. A person can type faster than that, and one impatient user must not
be able to get this project blocked.

**A User-Agent that identifies the application.** Generic library defaults are
explicitly insufficient, so `USER_AGENT` names the project and links to it.

**No auto-complete.** "Auto-complete search" is on the policy's forbidden list.
The interface has a button, and looking up a place is something the person asks
for — never something a keystroke triggers.

**Attribution.** Displayed in the interface, next to the results it produced.

## Why the server does this and not the browser

The browser could call Nominatim directly and save a hop. It would also hand the
user's IP address, and the place they are looking for, straight to a third party
the user never chose to talk to. Doing it here means OpenStreetMap sees this
server asking about a town, and nothing about who wanted to know.

## The cache is in memory and stays there

Nominatim asks that results be cached, and warns that repeating identical queries
can get a client classified as faulty. But rigor rule 4 says nothing a user types
is written to disk, and `docs/decisions/0005` turned off the response cache for
exactly that reason. A file of place names with timestamps is a record of where
people were looking, which is precisely what that decision exists to prevent.

So the cache lives in this process and dies with it. It satisfies the policy's
intent — a repeated search does not produce a repeated request — and writes
nothing down.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

#: The policy is explicit that a generic library default is not acceptable.
USER_AGENT = (
    "why-not-this-trial/0.1 (clinical trial finder; "
    "+https://github.com/Ledgeworth-Studios/UnivabioComp)"
)

#: "No heavy uses (an absolute maximum of 1 request per second)."
MIN_SECONDS_BETWEEN_REQUESTS = 1.0

#: Shown wherever a geocoded place appears. Required by the ODbL.
ATTRIBUTION = "Place search by OpenStreetMap contributors"

#: More than a handful of choices is not a choice, it is a list to read.
MAX_RESULTS = 5


class GeocodingError(RuntimeError):
    """The geocoder could not be reached or did not answer usefully."""


@dataclass(frozen=True)
class Place:
    """One candidate for a typed place name."""

    #: What to show the person, e.g. "Portland, Multnomah County, Oregon, USA".
    name: str
    latitude: float
    longitude: float


class Geocoder:
    """Looks up place names, politely.

    The HTTP client is injected so tests replay a recorded response and never
    touch the network — the same arrangement `whynot/registry.py` uses, and for
    the same reason: production and tests run the identical code path.
    """

    def __init__(
        self,
        http_client: httpx.Client | None = None,
        *,
        min_interval: float = MIN_SECONDS_BETWEEN_REQUESTS,
        sleep: object = time.sleep,
        clock: object = time.monotonic,
    ) -> None:
        self._http = http_client or httpx.Client(
            timeout=10.0, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        self._owns_http = http_client is None
        self._min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: float | None = None
        # One lock, because two browser requests arriving together must not each
        # decide it is their turn. The rate limit is per *service*, not per user.
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[Place, ...]] = {}

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Geocoder:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _wait_for_turn(self) -> None:
        """Hold the caller until at least `min_interval` has passed since the last."""
        now = self._clock()  # type: ignore[operator]
        if self._last_request_at is not None:
            waited = now - self._last_request_at
            if waited < self._min_interval:
                self._sleep(self._min_interval - waited)  # type: ignore[operator]
        self._last_request_at = self._clock()  # type: ignore[operator]

    def search(self, query: str) -> tuple[Place, ...]:
        """Candidates for a typed place name, best first. Empty if none match."""
        key = " ".join(query.split()).lower()
        if not key:
            return ()

        with self._lock:
            if key in self._cache:
                return self._cache[key]

            self._wait_for_turn()
            try:
                response = self._http.get(
                    NOMINATIM_URL,
                    params={"q": query, "format": "jsonv2", "limit": MAX_RESULTS},
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise GeocodingError(str(exc)) from exc

            places = tuple(
                place for place in (parse_place(raw) for raw in payload) if place is not None
            )
            self._cache[key] = places
            return places


def parse_place(raw: dict) -> Place | None:
    """One Nominatim result, or None when it is missing what we need."""
    name = raw.get("display_name")
    try:
        latitude = float(raw["lat"])
        longitude = float(raw["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not name:
        return None
    return Place(name=str(name), latitude=latitude, longitude=longitude)
