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
