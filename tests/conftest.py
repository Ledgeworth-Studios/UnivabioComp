"""Shared test setup.

The one rule this file enforces: **no test may touch the network.** Fixtures are
recorded to disk by `tools/record_fixtures.py` and replayed through
`httpx.MockTransport`. If a test ever constructs a real HTTP client by accident,
the autouse fixture below turns that into a loud failure instead of a slow,
flaky, internet-dependent pass.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "registry"


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def refuse(self, request):
        raise AssertionError(
            f"a test tried to make a real network request to {request.url}. "
            "Record a fixture with tools/record_fixtures.py instead."
        )

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)


@pytest.fixture
def load_fixture():
    def _load(name: str) -> dict:
        return json.loads((FIXTURE_DIR / name).read_text())

    return _load
