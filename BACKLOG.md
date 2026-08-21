# Backlog

One task per commit. Statuses: `READY` → `DOING` → `DONE`, or `BLOCKED`.
Take the **first** `READY` task in file order. Do not skip ahead, do not batch.

When you add a task, give it done-criteria a stranger could check. A task whose
completion is a matter of opinion will be marked done while broken.

Week groups exist so slippage is visible. If a week's tasks are unfinished when
its dates pass, that is information — record it in the journal, do not quietly
reflow the schedule.

---

## Week 1 — prove the pipeline (Aug 21–29)

Goal: answer the one question that could sink the project — can a model judge
real registry eligibility prose reliably enough to build a product on? No UI.
Terminal output is fine. Ugly is fine. Wrong-looking is the point of finding out.

- [x] **W1-1** `DONE` — Python project skeleton.
  Done when: `pyproject.toml` with `ruff` + `pytest`, package `whynot/`, a
  `justfile` with `check`, `lint`, `test`; `just check` exits 0 on an empty test
  suite; `.gitignore` covers `.venv/`, `__pycache__/`, `.env`, `*.db`.

- [x] **W1-2** `DONE` — ClinicalTrials.gov v2 client.
  Done when: `whynot/registry.py` can search by condition + status + geo radius
  and fetch one study by NCT ID; typed dataclasses for the fields we use;
  responses cached to SQLite keyed by request; tests use recorded fixtures and
  make **no** network calls. Verified API facts are in `docs/PLAN.md` — read them,
  especially that the geo filter returns every site worldwide, not just near ones.

- [x] **W1-3** `DONE` — Deterministic hard filters.
  Done when: `whynot/hardfilter.py` decides age / sex / healthy-volunteer
  eligibility from the structured fields alone, with no model call. Parses the
  registry's age strings (`"18 Years"`, `"6 Months"`, absent bounds). Returns a
  reason string for each rejection. Unit-tested against real fixture records
  including missing and unusual bounds.

- [x] **W1-4** `DONE` — Criteria splitter.
  Done when: given a raw `eligibilityCriteria` blob, produces a list of discrete
  criteria each tagged inclusion or exclusion, preserving the exact source text
  for quoting. Handles the common layouts (`Inclusion Criteria:` / `Exclusion
  Criteria:` headers, `*` and `-` bullets, numbered lists, and blobs with no
  headers at all). Tested on at least six real records of differing shape.

- [ ] **W1-5** `BLOCKED` — Three-valued judge, the spike.
  **Unblock note:** the key is expected at `.env` in the repo root (gitignored).
  macOS GUI apps do not read `~/.zshrc`, so an `export` in a shell profile will
  NOT reach a scheduled run — read `.env` explicitly rather than relying on the
  inherited environment. If `.env` is absent, stay BLOCKED; do not go looking for
  credentials belonging to other tools on this machine.
  **Blocked on a credential the agent cannot and must not create.** There is no
  `ANTHROPIC_API_KEY` in the build environment; an unauthenticated call to
  `api.anthropic.com` returns `401 authentication_error` (checked 2026-08-21).
  **To unblock:** the human puts a key in the environment the scheduled run sees
  — `export ANTHROPIC_API_KEY=...` in the shell profile the task inherits, or a
  `.env` file, which is already gitignored and must stay uncommitted. Nothing
  else about this task is blocked; the inputs it needs are all built and tested.
  Done when: one Claude call takes a hardcoded patient profile plus one trial's
  split criteria and returns, per criterion, `MET` / `NOT_MET` / `UNKNOWN` with a
  plain-English reason and the quoted source line. Uses structured outputs so the
  shape is guaranteed. Run it against five real trials by hand and paste the
  output into the journal. **This is the go/no-go.** If the verdicts are
  incoherent, say so plainly in the journal and mark the task BLOCKED rather than
  tuning prompts for hours — the human needs to know early.

- [ ] **W1-6** `BLOCKED` — End-to-end terminal walkthrough.
  **Blocked by the same missing `ANTHROPIC_API_KEY` as W1-5.** The chain this
  task prints contains two model steps — profile extraction and judgement — so it
  cannot be demonstrated end to end without a key. Unblocks the moment W1-5 does.
  Done when: `python -m whynot.demo "<free text situation>"` runs the whole chain
  — extract profile, query registry, hard filter, split, judge, rank, print — and
  produces readable output for a real query. Still no web UI.

## Week 2 — profile extraction and the shell (Aug 30 – Sep 5)

- [ ] **W2-1** `BLOCKED` — Profile extraction from free text via structured outputs.
  Same missing `ANTHROPIC_API_KEY` as W1-5. This is a model step by definition.
- [ ] **W2-2** `DOING` — FastAPI backend: the deterministic search path.
  **Split from the original W2-2 on 2026-08-21.** As written it said "search +
  judge", and the judge does not exist — W1-5 is blocked on a missing API key, so
  the task could not have been finished as one piece. The half that needs no key
  is this one; the judge endpoint is W2-2b below. Nothing was descoped.
  Done when: `whynot/api.py` defines a FastAPI app with `GET /api/health` and
  `POST /api/search`. The search body carries a condition, the caller's latitude,
  longitude and radius, and the structured profile fields `hardfilter.py` already
  understands. The response carries, per trial: NCT id, title, overall status,
  phase, the registry URL, the last-update date, the three hard-filter checks
  (field, verdict, reason, quoted source), the split criteria with their exact
  source text and inclusion/exclusion tag, and the **nearest** site with its
  distance in miles computed from the caller's coordinates — never the first site
  in the registry's list (`docs/PLAN.md`, the geo trap). No model call anywhere on
  this path: `whynot/api.py` must not read `ANTHROPIC_API_KEY` or import an LLM
  client, and a test asserts that. Tested with `fastapi.testclient.TestClient`
  against the recorded fixtures, no network. `just check` green, and the README
  states the one command that starts it.

- [ ] **W2-2b** `BLOCKED` — FastAPI judge endpoint, key server-side only.
  Blocked on W1-5: there is no judge to expose, and there will not be one until
  the `ANTHROPIC_API_KEY` arrives. Done when: `POST /api/judge` takes one trial's
  split criteria plus a profile and returns the three-valued verdicts; the key is
  read server-side only and never reaches the browser; a test asserts the key
  never appears in any response body.
- [ ] **W2-3** `READY` — React + Vite + TS frontend skeleton, one working query path.
- [ ] **W2-4** `READY` — Editable profile chips; user can correct any extracted field.

## Week 3 — the product (Sep 6–12)

- [ ] **W3-1** `READY` — Verdict cards: reasons with source quotes, nearest site + distance.
- [ ] **W3-2** `READY` — Ranking: hard conflicts, then distance, then phase.
- [ ] **W3-3** `READY` — "Questions to ask the study coordinator", generated from UNKNOWNs.
- [ ] **W3-4** `READY` — Detect and label non-patient trials (some enroll clinics, not people).
- [ ] **W3-5** `READY` — Printable / shareable results page for the coordinator questions.

## Week 4 — the eval (Sep 13–19)

- [ ] **W4-1** `READY` — Build a ~30-pair labelled eval set; store as versioned fixtures.
- [ ] **W4-2** `READY` — Eval harness reporting per-verdict accuracy, run via Batch API.
- [ ] **W4-3** `READY` — Measure the dangerous error specifically: `NOT_MET` where truth is `UNKNOWN`.
- [ ] **W4-4** `READY` — Decide the model tier on the eval numbers. Write it up in `docs/decisions/`.

## Week 5 — design and deploy (Sep 20–26)

- [ ] **W5-1** `READY` — Loading, empty, and error states for every async path.
- [ ] **W5-2** `READY` — Typography and layout pass; mobile down to 375px.
- [ ] **W5-3** `READY` — Accessibility: keyboard paths, focus states, colour contrast, semantics.
- [ ] **W5-4** `READY` — The rigor rules from `docs/PLAN.md` visible in the UI, not just honoured in code.
- [ ] **W5-5** `READY` — Deploy: single container, FastAPI serves built static files, public URL.

## Week 6 — submit (Sep 27 – Oct 3)

- [ ] **W6-1** `READY` — README a judge can follow from clone to running.
- [ ] **W6-2** `READY` — One-page project description PDF.
- [ ] **W6-3** `READY` — Demo video script: problem, live run, the eval number, finished-vs-planned.
- [ ] **W6-4** `BLOCKED` — Record and submit. **Human only.** An agent cannot record the
      demo video, and must not attempt the Devpost submission.

---

## Discovered

New tasks go here as runs find them. Move them into a week group if they belong
to one.

- [x] **D-1** `DONE` — GitHub Actions workflow running `just check` on push.
  Done when: `.github/workflows/check.yml` installs `uv`, runs `uv sync --extra dev`
  and `just check` on push and pull request, and a push has produced one green run
  visible with `gh run list`. Rationale: `docs/decisions/0001` treats the remote as
  the backup, but a backup nobody checks can hold broken code. Actions minutes are
  free on this public repository.

- [ ] **D-2** `READY` — Decide what to do about gestational age bounds.
  `whynot/hardfilter.py` converts every registry age string to years on one
  scale, so `"27 Weeks"` becomes 0.52 years. For preterm-infant trials (verified
  example `NCT01066728`, bounds `27 Weeks`–`32 Weeks`) that string is a
  *gestational* age, and the registry gives no field distinguishing gestational
  from postnatal. Converting it as postnatal could return `NOT_MET` for a
  neonate who actually qualifies — the exact error `docs/PLAN.md` says to weight
  hardest. Done when: a `docs/decisions/` entry states the chosen behaviour and
  `hardfilter.py` implements it with a test. Low priority — the demo disease area
  is adult — but it must not be forgotten silently.

- [x] **D-3** `DONE` — Stop two scheduled runs from working the repo at once.
  On 2026-08-21 two runs overlapped. The second correctly detected the first and
  stood down (`docs/journal/2026-08-21-0135-run-aborted-concurrent.md`), but only
  because it noticed by hand. `CLAUDE.md` currently says a dirty tree with a
  `DOING` marker means the previous run died — which is wrong; it may mean a run
  is alive and working, and acting on that reading would corrupt a healthy build.
  Done when: (a) the run takes an exclusive lock at start and exits immediately if
  it cannot get it, and (b) `CLAUDE.md`'s "if the first task is already DOING"
  paragraph tells the reader to check for a live peer *before* adopting the task.
  **Done 2026-08-21:** `tools/runlock.py` plus `just lock` / `tick` / `unlock`,
  wired into the loop in `CLAUDE.md`. Twelve tests including eight real competing
  processes racing for the lock. See `docs/journal/2026-08-21-0527-D-3.md`.

