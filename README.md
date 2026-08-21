# Why Not This Trial

**Everybody builds clinical trial search. Nobody builds trial *rejection*.**

This tool tells you which eligibility criteria you meet, which you don't, and —
the useful part — which ones *nobody can tell from what you've said*. Those
become a printable list of questions to ask the study coordinator, which is the
thing you actually walk away with.

Built for [UnivaBio 2026](https://univabio.devpost.com/) (AI for Human Health).

> **Not medical advice.** This reads the public ClinicalTrials.gov registry. It
> does not diagnose, does not recommend treatment, and never tells you that you
> are eligible for a trial — only that you may qualify, and that the study team
> is who confirms it.

## See it in a minute

You need [`uv`](https://docs.astral.sh/uv/), [`just`](https://just.systems) and
[Node](https://nodejs.org) 20+. On a Mac: `brew install uv just node`.

```bash
git clone https://github.com/Ledgeworth-Studios/UnivabioComp.git
cd UnivabioComp
just install
just dev
```

Then open <http://localhost:5173>, and search **multiple sclerosis** near
**Portland, Oregon**.

**No API key is needed.** ClinicalTrials.gov's v2 API is public, and everything
described below runs against the live registry without credentials.

### What to try, and what to watch for

1. **Set the age chip to 41.** The paediatric MS trial says *"This trial enrols
   ages 10 Years to 17 Years; you told us you are 41 years old"* and drops to the
   bottom of the list. **It is not hidden** — see
   [`docs/decisions/0002`](docs/decisions/0002-ranking-order-and-phase.md) for why
   that matters.
2. **Change it to 12.** The same six trials re-sort and re-explain themselves;
   now the adult trials are the conflicts.
3. **Clear the age chip.** Every verdict becomes *"not settled"* and an invitation
   to fill it in — never *"you don't qualify"*.
   **Or search somewhere else entirely** — type *Tucson* into "search for somewhere
   else", press Find, and pick it.
4. **Look at the nearest site.** One of those trials has **91 sites worldwide**
   and the card shows the one 0.6 miles from downtown Portland. The registry lists
   Birmingham, Alabama first; showing that would send a Portland user to Alabama.
5. **Search *type 2 diabetes*.** One result carries a caution that its
   participants appear to be *health centres*, not people — with the evidence
   printed underneath.
6. **Press "Take these to your appointment"** for the printable sheet.

## What is built, and what is not

Honest, because a judge who finds this out during the demo has been misled.

| Step | Status |
|---|---|
| Search the registry by condition, status and distance | **Built** |
| Age / sex / healthy-volunteer checks, decided in plain Python | **Built** |
| Splitting the eligibility blob into quotable criteria | **Built** |
| Ranking, coordinator questions, non-patient detection, print sheet | **Built** |
| Web interface, editable profile chips | **Built** |
| **Reading the free-text criteria with a model** | **Not built** |
| Extracting a profile from a free-text sentence | **Not built** |
| The accuracy evaluation | Answer key built; needs the model to run |

The last three all wait on one thing: an `ANTHROPIC_API_KEY`, which the build
environment does not have. Everything that does *not* need a model was built and
tested instead, which is why the criteria are shown on each card in the registry's
own words with a note saying plainly that they have not been checked against you.

## Where to look in the code

`docs/PLAN.md` divides the work in two, and the split is the whole architecture:
**structured fields are decided in plain Python, and only the free-text criteria
may involve a model.** Sorting, filtering and arithmetic are never delegated.

    whynot/registry.py    ClinicalTrials.gov client. Read the module docstring:
                          the geo filter matches the *study*, then returns every
                          site worldwide, which is trap number one.
    whynot/hardfilter.py  Age, sex, healthy-volunteer — three-valued, no model.
    whynot/criteria.py    Splits one eligibility blob into tagged, quotable lines.
    whynot/ranking.py     Conflicts down, nearest first. Nothing is ever hidden.
    whynot/questions.py   The coordinator questions, split by *who can answer*.
    whynot/nonpatient.py  Trials that enrol clinics rather than people.
    whynot/geocode.py     Place names to coordinates. Half of it is the
                          OpenStreetMap usage policy, obeyed rather than cited.
    whynot/api.py         The HTTP layer. Contains no model call, and three tests
                          fail if one is ever added.
    web/src/profile.ts    One object holding everything we believe about you.
                          Every field is null until you say otherwise.

Start with [`docs/PLAN.md`](docs/PLAN.md), then
[`docs/decisions/`](docs/decisions/) — five decisions where a reasonable person
could have chosen differently, each with the alternative that was rejected.

## Running it other ways

**Both halves separately** — `just serve` in one terminal, `just web` in another.

**As one server, the way it deploys** — the interface and API share a single
origin, which is why there is no CORS configuration anywhere in this project:

```bash
just web-check    # builds web/dist
just serve        # serves the API *and* the page on :8000
```

**The API on its own** — `just serve`, then <http://localhost:8000/docs> for
interactive documentation of every endpoint. For example:

```bash
curl -s localhost:8000/api/search -H 'content-type: application/json' -d '{
  "condition": "multiple sclerosis",
  "latitude": 45.5152, "longitude": -122.6784, "radius_miles": 50,
  "age_years": 41, "sex": "female"
}'
```

A `Dockerfile` builds the interface and API into one image. **It has never been
built** — the machine this was developed on cannot reach Docker Hub — so treat it
as a draft (`W5-5c` in the backlog).

## The one-page description

[`docs/one-pager.pdf`](docs/one-pager.pdf) is the submission one-pager. The words
are in [`docs/one-pager.md`](docs/one-pager.md) so they can be edited and
reviewed in a diff; `just one-pager` re-renders the PDF and **fails if the result
runs to more than one page**.

## The demo video

[`docs/demo-script.md`](docs/demo-script.md) is a shot-by-shot script — what is
on screen, what is said over it, and how long each beat takes, measured from the
word counts rather than estimated. Every figure it quotes names the journal entry
where it was verified, so it can be re-checked before recording.

## Development

```bash
just check        # Python: lint, format check, 179 tests
just web-check    # web: lint, 69 tests, type check, build
```

Both run on every push. **No test touches the network** — every registry response
is a recorded fixture, and `tests/conftest.py` turns a real request into a
failure.

## Repository layout

    CLAUDE.md         operating contract for the automated build agents
    BACKLOG.md        the task queue, with what is blocked and why
    whynot/           the Python package
    web/              the interface (Vite + React + TypeScript)
    tests/            recorded fixtures; no network
    tools/            fixture recorder, eval-set builder, build-run lock
    docs/PLAN.md      technical plan, verified API facts, the five rigor rules
    docs/journal/     one entry per build run, in plain English
    docs/decisions/   design decisions and their rejected alternatives
    Dockerfile        one image: built interface + API (never built — W5-5c)

## How this was built

Almost entirely by scheduled, unattended agent runs, five hours apart, none of
which remembered the previous one. [`CLAUDE.md`](CLAUDE.md) is the contract they
work to and [`docs/journal/`](docs/journal/) is the record: one entry per task, in
plain English, written so that reading it end to end teaches the codebase.

Commits are attributed to the human entrant, who is responsible for the work and
can explain it.
