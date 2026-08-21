"""Record real ClinicalTrials.gov responses to disk as test fixtures.

Run this by hand when a fixture needs refreshing:

    uv run python tools/record_fixtures.py

Tests never call the network. They replay whatever this script last wrote into
`tests/fixtures/registry/`. Keeping the recorder in the repository is what makes
"these fixtures are real registry data" a checkable claim rather than an
assertion — anyone can re-run it and diff the result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from whynot.registry import API_BASE_URL, STUDY_FIELDS  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "registry"

# Portland, Oregon. Chosen because it is far from the US east coast, which makes
# the "every site worldwide comes back" trap visible in the recorded data.
PORTLAND = (45.5152, -122.6784)

SEARCHES = {
    "search_ms_portland.json": {
        "query.cond": "multiple sclerosis",
        "filter.overallStatus": "RECRUITING",
        "filter.geo": f"distance({PORTLAND[0]},{PORTLAND[1]},50mi)",
        "fields": ",".join(STUDY_FIELDS),
        "pageSize": 5,
        "countTotal": "true",
    },
}

# Individual studies worth freezing:
#   NCT06251323 — enrols health centres, not people (docs/PLAN.md trap 2)
STUDIES = ["NCT06251323"]


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30.0, headers={"Accept": "application/json"}) as client:
        for name, params in SEARCHES.items():
            response = client.get(f"{API_BASE_URL}/studies", params=params)
            response.raise_for_status()
            _write(name, response.json())

        for nct_id in STUDIES:
            response = client.get(
                f"{API_BASE_URL}/studies/{nct_id}", params={"fields": ",".join(STUDY_FIELDS)}
            )
            response.raise_for_status()
            _write(f"study_{nct_id}.json", response.json())


def _write(name: str, payload: object) -> None:
    path = FIXTURE_DIR / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {path.relative_to(Path.cwd())} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
