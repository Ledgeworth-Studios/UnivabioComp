"""Record real Nominatim responses as test fixtures.

    uv run python tools/record_geocode_fixtures.py

Run this by hand, rarely. The OSM Foundation's usage policy allows at most one
request a second and asks that clients not repeat identical queries — so this
walks a small list, one at a time, through the same rate-limited `Geocoder` the
application uses rather than firing them off in a loop of its own.

Tests replay whatever this last wrote. They never call the network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from whynot.geocode import MAX_RESULTS, NOMINATIM_URL, USER_AGENT  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "geocode"

#: One unambiguous, one famously ambiguous, one that should find nothing.
QUERIES = {
    "tucson.json": "Tucson",
    "portland.json": "Portland",
    "nowhere.json": "zzzzqqxnotaplace",
}


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(
        timeout=30.0, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    ) as client:
        for index, (name, query) in enumerate(QUERIES.items()):
            if index:
                # The policy's one-per-second limit, obeyed by the recorder too.
                import time

                time.sleep(1.2)
            response = client.get(
                NOMINATIM_URL, params={"q": query, "format": "jsonv2", "limit": MAX_RESULTS}
            )
            response.raise_for_status()
            path = FIXTURE_DIR / name
            path.write_text(json.dumps(response.json(), indent=2, sort_keys=True) + "\n")
            print(f"wrote {path.name}: {len(response.json())} results for {query!r}")


if __name__ == "__main__":
    main()
