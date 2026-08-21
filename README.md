# Why Not This Trial

A clinical-trial finder that explains **why you don't qualify** — and turns
everything it can't determine into questions to ask the study coordinator.

Built for [UnivaBio 2026](https://univabio.devpost.com/) (AI for Human Health).

> **Not medical advice.** This tool reads the public ClinicalTrials.gov registry.
> It does not diagnose, does not recommend treatment, and never tells you that you
> are eligible for a trial — only that you may qualify and should ask.

## Status

Early. See [`BACKLOG.md`](BACKLOG.md) for what's built and what isn't, and
[`docs/journal/`](docs/journal/) for a run-by-run account of how it got that way.

## How it works

Free-text description of a situation → structured profile → registry query →
deterministic filters on age/sex → model judgement on the free-text eligibility
criteria → ranked trials, each with reasons and coordinator questions.

Every criterion gets one of three verdicts — `MET`, `NOT_MET`, or `UNKNOWN` —
and `UNKNOWN` is the interesting one. Full rationale in [`docs/PLAN.md`](docs/PLAN.md).

## Running the API

    just install
    just serve

That starts the search API on <http://127.0.0.1:8000>, with interactive
documentation at <http://127.0.0.1:8000/docs> — every endpoint below can be tried
from that page without writing any code.

**No API key is needed for this part.** ClinicalTrials.gov's v2 API is public and
unauthenticated, and the search path deliberately contains no model call:

    GET  /api/health   is the server up
    POST /api/search   a condition, where you are, and whatever you chose to tell
                       us about yourself -> matching trials, each with the
                       age/sex/healthy-volunteer checks, their eligibility
                       criteria split into quotable lines, and the site nearest
                       to you

An example, using coordinates for downtown Portland, Oregon:

    curl -s localhost:8000/api/search -H 'content-type: application/json' -d '{
      "condition": "multiple sclerosis",
      "latitude": 45.5152, "longitude": -122.6784, "radius_miles": 50,
      "age_years": 41, "sex": "female"
    }'

Reading the free-text criteria — the part that needs a model, and therefore an
`ANTHROPIC_API_KEY` — is a separate endpoint that has not been built yet
(`W2-2b` in the backlog).

## Running the web interface

    just dev

That starts the API and the page together and opens on
<http://localhost:5173>. Type a condition, pick somewhere to search near, and
optionally say your age and sex — every field about you is optional, and leaving
one blank produces a question for the study team rather than a guess.

To run the two halves separately, `just serve` in one terminal and `just web` in
another. See [`web/README.md`](web/README.md).

## Repository layout

    CLAUDE.md         operating contract for automated build agents
    BACKLOG.md        the task queue
    whynot/           the package: registry client, filters, criteria, API
    tests/            every registry response is a recorded fixture; no test
                      touches the network
    tools/            recorder for those fixtures, and the build-run lock
    docs/PLAN.md      technical plan, verified API facts, rigor rules
    docs/journal/     one entry per build run, in plain English
    docs/decisions/   design decisions and their rejected alternatives

## Development

    just check        # Python: lint, format check, tests
    just web-check    # web: lint, unit tests, type check, build
    just serve        # run the API locally
    just dev          # run the API and the web interface together
