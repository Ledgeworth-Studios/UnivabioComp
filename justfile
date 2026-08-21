# Task runner for "Why Not This Trial".
#
# `uv` creates and manages .venv from pyproject.toml; `uv run` makes sure the
# environment is in sync before running anything, so there is no "did you
# activate the venv?" step for a judge following the README.

# Everything that must pass before a task is marked DONE.
check: lint test

# Static checks: rules, then formatting.
lint:
    uv run ruff check .
    uv run ruff format --check .

# Reformat in place. Not part of `check` — `check` only ever reports.
fmt:
    uv run ruff format .

# The test suite. No test may touch the network.
test:
    uv run pytest

# Create/refresh the local environment.
install:
    uv sync --extra dev

# Start the API on http://127.0.0.1:8000 (docs at /docs).
serve port="8000":
    uv run uvicorn whynot.api:app --reload --port {{port}}

# Start the web interface on http://localhost:5173. Needs `just serve` running too.
web:
    cd web && npm run dev

# Both halves at once: API in the background, web in the foreground.
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run uvicorn whynot.api:app --reload --port 8000 &
    api=$!
    trap 'kill $api 2>/dev/null || true' EXIT
    cd web && npm run dev

# Type-check, lint and build the web interface. Not part of `check`, which is Python.
web-check:
    cd web && npm ci && npm run lint && npm run build

# --------------------------------------------------------------------------
# One build run at a time. See tools/runlock.py and the loop in CLAUDE.md.
# --------------------------------------------------------------------------

# Take the run lock. Exits non-zero if another run is alive — then STAND DOWN.
lock label="scheduled build run":
    uv run python tools/runlock.py acquire --label "{{label}}"

# Prove this run is still alive. Run after every commit.
tick:
    uv run python tools/runlock.py tick

# Give the lock up. Run at the end of the run, including a run that gave up.
unlock:
    uv run python tools/runlock.py release

# Who holds the lock, if anyone.
lock-status:
    uv run python tools/runlock.py status
