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
- [x] **W2-2** `DONE` — FastAPI backend: the deterministic search path.
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
  **Done 2026-08-21:** `whynot/api.py`, 16 tests, verified against the live
  registry as well as against fixtures. See `docs/journal/2026-08-21-0534-W2-2.md`.

- [ ] **W2-2b** `BLOCKED` — FastAPI judge endpoint, key server-side only.
  Blocked on W1-5: there is no judge to expose, and there will not be one until
  the `ANTHROPIC_API_KEY` arrives. Done when: `POST /api/judge` takes one trial's
  split criteria plus a profile and returns the three-valued verdicts; the key is
  read server-side only and never reaches the browser; a test asserts the key
  never appears in any response body.
- [x] **W2-3** `DONE` — React + Vite + TS frontend skeleton, one working query path.
  Done-criteria written 2026-08-21 (the line had none; the backlog's own rule says
  a task without checkable criteria gets marked done while broken).
  Done when: `web/` holds a Vite + React + TypeScript app; `npm run build`
  succeeds, which includes the TypeScript check, and `npm run lint` passes. One
  page takes a condition, a location and the optional profile fields, calls
  `POST /api/search` on the W2-2 backend, and renders one card per trial showing
  the title, the recruiting status, the nearest site with its distance, the three
  structured checks with their verdicts and reasons, and a link to the trial's own
  registry page. The disclaimer from the API response is displayed, and the word
  "eligible" is never used to describe the user. The dev server proxies `/api` to
  the backend so no CORS configuration is needed. `just web` starts it, the README
  says so, and GitHub Actions builds `web/` on push so a broken frontend cannot sit
  unnoticed. Design, states and accessibility are Week 5 — this is the skeleton.
  **Done 2026-08-21:** `web/`, verified in a browser against the live registry —
  form to Vite proxy to API to registry to rendered cards, no console errors. See
  `docs/journal/2026-08-21-0541-W2-3.md`.

- [x] **W2-4** `DONE` — Editable profile chips; user can correct any extracted field.
  Done-criteria written 2026-08-21 (the line had none).
  **Not blocked, though it mentions extraction.** `docs/PLAN.md`'s pipeline marks
  step 2, "show profile back as editable chips", **deterministic**. The chips are
  buildable now against the fields the form already collects; W2-1 later fills the
  same object from free text instead of the user typing it. Building the chips now
  is what makes W2-1 small on the day the key arrives.
  Done when: `web/src/profile.ts` holds one `Profile` type carrying everything the
  app believes about the user, and the function that turns it into a search
  request — so there is exactly one place a field can live. `web/src/ProfileChips.tsx`
  renders one chip per field; a field the user has not given renders as a visibly
  different "not said" chip; any chip can be edited in place and any optional chip
  can be cleared back to "not said". Editing re-runs the search. The interface
  states in words that a blank field becomes a question for the study team, never
  an exclusion. Verified in a browser against the live registry: changing the age
  chip from 41 to 12 flips a paediatric trial's age verdict from conflict to
  no-conflict, and clearing the age chip turns it to "ask the study team".
  `npm run lint` and `npm run build` pass; CI green.
  **Done 2026-08-21:** verified in a browser — 41 / 12 / cleared each produce a
  different, correct verdict on the same two trials. See
  `docs/journal/2026-08-21-0546-W2-4.md`.


## Week 3 — the product (Sep 6–12)

- [ ] **W3-1** `BLOCKED` — Verdict cards: reasons with source quotes, nearest site + distance.
  **Blocked on W1-5, the judge, and therefore on the API key.** Read this before
  assuming there is nothing to do here: the *deterministic* half of this task
  already shipped in W2-3 and W2-4. Cards exist; each of the three structured
  checks already shows its verdict, a plain-English reason and the registry
  wording it came from; the nearest site and its distance are already on every
  card. What is missing is the same treatment for the **free-text criteria** —
  one verdict per criterion, each quoting the registry line it was judged from —
  and that is exactly what the judge produces. There is no useful version of this
  card without it, so this is not split the way W2-2 was; it is simply waiting.
  Done when: each criterion on a card carries `MET` / `NOT_MET` / `UNKNOWN`, the
  model's reason, and the verbatim source line, alongside the structured checks
  that are already there.
- [x] **W3-2** `DONE` — Ranking: hard conflicts, then distance, then phase.
  Done-criteria written 2026-08-21 (the line had none). Fully deterministic and
  unblocked: all three inputs are already in the search response.
  Done when: `whynot/ranking.py` orders a list of studies for one profile, and
  `/api/search` returns them in that order rather than the registry's. The order
  is: trials with no structured conflict first; within those, nearer sites before
  farther ones; then earlier phase before later. Trials with a conflict are
  **kept, not hidden** — this tool's whole point is explaining why something does
  not fit, and dropping them silently would be the one thing it exists not to do.
  Every part of the comparison is total and reproducible: no trial may sort
  differently between two identical calls, so ties break on NCT id last. Missing
  data sorts last rather than first — a trial with no located site must not
  outrank one that is nine miles away. Unit-tested with real fixture records
  covering: conflict versus none, distance ordering, phase ordering, no
  coordinates given at all, a study with no located sites, and stability of ties.
  A test asserts no trial is dropped by ranking. `just check` green.
  **Done 2026-08-21:** `whynot/ranking.py`, 21 tests, the phase-direction and
  never-hide decisions written up in `docs/decisions/0002`. Verified live: the
  same six trials reorder completely between age 41 and age 12 and none is
  dropped. See `docs/journal/2026-08-21-0552-W3-2.md`.

- [x] **W3-3** `DONE` — "Questions to ask the study coordinator", generated from UNKNOWNs.
  Done-criteria written 2026-08-21 (the line had none). **Split at the same seam
  as W2-2:** the machinery and the structured-field questions are buildable now;
  the bulk of the questions come from the judge's `UNKNOWN` verdicts and are
  W3-3b below.
  The insight this task turns on: an `UNKNOWN` has two causes and they need
  opposite treatment. *The registry did not say* — an unreadable age bound, a
  blank healthy-volunteer field — is a question only the study team can answer.
  *You did not say* — no age, no sex — is not a question for anyone; it is
  something the person can fill in themselves, and asking a coordinator "how old
  am I" would be absurd. Conflating the two would make the headline deliverable
  of this project look foolish.
  Done when: `whynot/questions.py` turns a study plus a profile into (a)
  questions for the study team, each with the registry wording that prompted it,
  and (b) prompts for fields the person could fill in themselves. Neither ever
  asserts eligibility. The two lists come back on each trial from `/api/search`
  and are rendered on the card, with the "you could tell us" prompts pointing at
  the chips from W2-4. A trial with nothing open says so rather than showing an
  empty box. Unit-tested against all four `UNKNOWN` sources in `hardfilter.py`,
  including a test that a `MET` or `NOT_MET` check never produces a question.
  `just check` green, and the panel verified in a browser on live data.
  **Done 2026-08-21:** `whynot/questions.py`, 12 tests plus 3 endpoint tests.
  Verified live on `NCT06446232`, which shows both kinds at once. Measured while
  doing it: across 130 live trials only one produced a study-team question — the
  structured fields rarely leave anything open, which is the argument for W3-3b.
  See `docs/journal/2026-08-21-0558-W3-3.md`.


- [ ] **W3-3b** `BLOCKED` — Coordinator questions from the judged free-text criteria.
  Blocked on W1-5. Most of what a person should ask a coordinator comes from the
  criteria the judge could not resolve — a lab value, a scan, a date nobody typed
  in — and there is no judge until the key arrives. Done when: every `UNKNOWN`
  verdict on a criterion becomes a question quoting the criterion it came from,
  merged into the same panel W3-3 builds.
- [x] **W3-4** `DONE` — Detect and label non-patient trials (some enroll clinics, not people).
  Done-criteria written 2026-08-21 (the line had none). Unblocked and
  deterministic — the verified example `NCT06251323` is already recorded at
  `tests/fixtures/registry/study_NCT06251323.json`.
  **The hazard to design against:** a false positive here hides a trial from
  somebody who could have joined it, which is the same class of harm as a
  `NOT_MET` that should have been `UNKNOWN`. So detection must need corroboration
  rather than one keyword, must show its evidence, and must never state the
  conclusion as fact.
  Done when: `whynot/nonpatient.py` decides, from the registry's own fields and
  the criteria text, whether a study looks like it enrols organisations rather
  than individual people; it requires **at least two independent signals** before
  saying so, and returns the signals it found so the interface can show them. The
  card shows a caution worded as a possibility, never a verdict, and always
  pointing the reader at the study team. Trials are **labelled, not hidden and not
  reordered** — record why in `docs/decisions/`. Tested against `NCT06251323`
  (must be flagged, with its evidence) and against every study in
  `search_ms_portland.json` (none may be flagged — a false positive on an
  ordinary patient trial is the failure mode that matters). `just check` green
  and the caution verified in a browser on live data.
  **Done 2026-08-21:** `whynot/nonpatient.py`, 12 tests plus 2 endpoint tests,
  reasoning in `docs/decisions/0003`. Verified live: 1 of 40 recruiting type 2
  diabetes trials flagged, and it was `NCT06251323`.
  See `docs/journal/2026-08-21-0603-W3-4.md`.

- [x] **W3-5** `DONE` — Printable / shareable results page for the coordinator questions.
  Done-criteria written 2026-08-21 (the line had none).
  **Scope decision to make deliberately, because W3-3 measured the problem:** on
  today's data most trials raise no coordinator questions, since the interesting
  ones come from the free-text criteria and the judge is blocked. A page that only
  prints questions would usually be blank. So this page prints **what a person
  takes to an appointment**: which trials, where, what would stop them, what is
  not settled, and what to ask. That is useful now, and W3-3b's questions drop
  straight into the section already waiting for them.
  Done when: a button switches the page to a printable summary and back. The
  summary carries the date, what was searched with, the disclaimer, and per trial:
  title, NCT id, status, nearest site with distance, anything that would stop them
  (`NOT_MET` reasons with the registry wording), anything not settled, the
  questions for the study team, and the trial's URL **written out as text**,
  because a printed page cannot be clicked. Any non-patient caution from W3-4 is
  carried over. A `@media print` rule hides the buttons and the search controls so
  the paper copy has no dead furniture on it. Nothing on the page asserts
  eligibility. Verified in a browser on live data: the summary renders, the
  print-only styling is in effect, and the URLs appear as readable text.
  **Done 2026-08-21:** `web/src/PrintableSummary.tsx`. Verified in a browser on
  live data with and without an age stated; the `@media print` rule confirmed
  present in the live stylesheet rather than merely written.
  See `docs/journal/2026-08-21-0607-W3-5.md`.


## Week 4 — the eval (Sep 13–19)

- [x] **W4-1** `DONE` — Build a ~30-pair labelled eval set; store as versioned fixtures.
  Done-criteria written 2026-08-21 (the line had none). Buildable without the key:
  the pairs are real registry criteria and hand-written profiles. **Running** the
  eval over them is W4-2 and needs the model.
  **The methodological rule this task must respect:** the eval set is the answer
  key the model is marked against. If the same kind of system writes both the
  answers and the key, the number it produces is worthless — and that number is
  going in front of competition judges. So every label carries the reasoning
  behind it and a flag saying whether a person still needs to confirm it, and the
  scoring code must refuse to count a label nobody has confirmed when confirming
  it takes judgement.
  Done when: `whynot/evalset.py` loads a versioned JSON fixture of ~30 pairs, each
  pair naming the trial, the **verbatim** criterion text, a profile, the expected
  verdict, the reasoning, whether a human must confirm it, and who confirmed it
  (nobody, initially). The loader **rejects a pair whose criterion text does not
  appear verbatim in a recorded registry fixture**, so no invented criteria can
  enter the set. It exposes the subset that is safe to score without human review
  and refuses to hand over the rest. The verdict convention for exclusion criteria
  is written down in `docs/decisions/` — W1-5's judge must use the same one or
  every exclusion score is inverted. `just check` green.
  **Done 2026-08-21:** 31 pairs from four real trials and three profiles; 26
  scorable, **5 awaiting a human review** — that review is now a second human
  blocker on Week 4 alongside the API key. Polarity settled in
  `docs/decisions/0004`. See `docs/journal/2026-08-21-0613-W4-1.md`.

- [ ] **W4-2** `BLOCKED` — Eval harness reporting per-verdict accuracy, run via Batch API.
  Blocked on W1-5: there is no judge to run over the eval set. The set itself is
  built and validated (W4-1) and the harness has a definite shape waiting for it —
  it must score only `scorable_pairs()` and report `held_back()` alongside the
  number, per `docs/decisions/0004`.
  **Second, separate blocker, and it is not the key:** five labels in
  `tests/fixtures/eval/criteria_v1.json` are proposals awaiting a human review.
  Until somebody fills in their `reviewed_by`, those five cannot be scored. The
  questions to settle are listed in `docs/journal/2026-08-21-0613-W4-1.md`.
- [ ] **W4-3** `BLOCKED` — Measure the dangerous error specifically: `NOT_MET` where truth is `UNKNOWN`.
  Blocked on W4-2, and so on W1-5 and the key. Note the eval set is already
  weighted for exactly this measurement — 27 of its 31 pairs expect `UNKNOWN`,
  because that is where this error hides.
- [ ] **W4-4** `BLOCKED` — Decide the model tier on the eval numbers. Write it up in `docs/decisions/`.
  Blocked on W4-2 producing numbers. `docs/PLAN.md` is explicit that this decision
  is not to be made by guessing, so it cannot be brought forward.

## Week 5 — design and deploy (Sep 20–26)

- [ ] **W5-1** `DOING` — Loading, empty, and error states for every async path.
  Done-criteria written 2026-08-21 (the line had none). There is exactly one async
  path — the search — reached two ways: the opening form, and committing a chip
  edit.
  Done when: (a) a search in flight keeps the previous results on screen, marked
  as being updated, instead of blanking the page — a chip edit currently makes
  every card vanish and reappear; (b) a failure the user can do something about
  says so, and offers to try again — "Failed to fetch" is the browser's words, not
  ours; (c) the empty result distinguishes "nothing recruiting for that condition"
  from "nothing within the radius", and suggests the specific next move; (d) **an
  out-of-order response can never be displayed.** Two quick chip edits can have
  their responses arrive in the wrong order, and showing verdicts computed for a
  profile the person has already corrected is the worst bug this page could have.
  Every one of the four verified in a browser, (b) by actually stopping the
  backend and (d) by a test, since a race cannot be verified by looking at it.
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

- [ ] **D-4** `READY` — Turn a typed place name into coordinates (geocoding).
  Found while building W2-3. The registry's distance filter needs a latitude and
  longitude, and asking a person to type coordinates is not a product — so
  `web/src/places.ts` currently offers a hard-coded list of six cities. That is
  honest for a skeleton and embarrassing for a submission: a user in Tucson
  cannot search near home.
  Done when: the user types a place name and the app searches near it. Decide the
  geocoding service in a `docs/decisions/` entry first — the constraint that
  matters is that it must not need a paid key, and must not send the user's
  location to a service that logs it against them. Nominatim (OpenStreetMap) is
  the obvious candidate and has a usage policy that must be read before it is
  used. Keep the preset cities as a fallback for when geocoding fails, and keep
  "Anywhere", because searching with no location is a real query.

- [ ] **D-5** `READY` — Unit tests for the web interface.
  Found while doing W2-4. Everything under `web/` is checked only by the
  TypeScript compiler, the linter, and a person driving a browser. `profile.ts`
  now holds logic worth pinning — above all that an unstated field is `null` and
  never `0` or `""`, because a default there would turn "I didn't say" into a
  claim the user never made, and produce `NOT_MET` against every adult trial.
  Done when: a test runner is installed in `web/` (vitest is the obvious choice —
  it is Vite's own and needs no extra build configuration), `npm test` runs it,
  `just web-check` and the CI web job run it too, and there are tests covering:
  an unstated field stays null through `toSearchRequest`, clearing a chip returns
  a field to null, and `describe()` marks unstated fields as unsaid. Do not test
  the visual layout — Week 5 will change all of it.

- [ ] **D-6** `READY` — `PatientProfile` cannot describe a real patient.
  Found while building the W4-1 eval set. The profile has four fields — age, sex,
  healthy-volunteer, and a list of condition names — so almost any criterion that
  actually decides a trial is unanswerable from it: "diagnosed in 2019",
  "currently on ocrelizumab", "EDSS 3.5", "two relapses in the last two years".
  The eval set came out 27 `UNKNOWN` against 2 `MET` and 2 `NOT_MET` for this
  reason, which makes it a good instrument for the dangerous error and a weak one
  for everything else.
  Done when: `PatientProfile` can carry the things a person actually says about
  themselves, with every field still optional and still defaulting to "not said";
  the chips in `web/` show them; and the eval set gains pairs that exercise them.
  **Do not turn this into a medical questionnaire** — the fields should be
  whatever a person naturally writes in a sentence about their situation, because
  W2-1 has to be able to extract them from exactly that. Decide the field list in
  a `docs/decisions/` entry before writing code.
