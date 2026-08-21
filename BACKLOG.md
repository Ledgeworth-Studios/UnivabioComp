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

- [ ] **W1-2** `DOING` — ClinicalTrials.gov v2 client.
  Done when: `whynot/registry.py` can search by condition + status + geo radius
  and fetch one study by NCT ID; typed dataclasses for the fields we use;
  responses cached to SQLite keyed by request; tests use recorded fixtures and
  make **no** network calls. Verified API facts are in `docs/PLAN.md` — read them,
  especially that the geo filter returns every site worldwide, not just near ones.

- [ ] **W1-3** `READY` — Deterministic hard filters.
  Done when: `whynot/hardfilter.py` decides age / sex / healthy-volunteer
  eligibility from the structured fields alone, with no model call. Parses the
  registry's age strings (`"18 Years"`, `"6 Months"`, absent bounds). Returns a
  reason string for each rejection. Unit-tested against real fixture records
  including missing and unusual bounds.

- [ ] **W1-4** `READY` — Criteria splitter.
  Done when: given a raw `eligibilityCriteria` blob, produces a list of discrete
  criteria each tagged inclusion or exclusion, preserving the exact source text
  for quoting. Handles the common layouts (`Inclusion Criteria:` / `Exclusion
  Criteria:` headers, `*` and `-` bullets, numbered lists, and blobs with no
  headers at all). Tested on at least six real records of differing shape.

- [ ] **W1-5** `READY` — Three-valued judge, the spike.
  Done when: one Claude call takes a hardcoded patient profile plus one trial's
  split criteria and returns, per criterion, `MET` / `NOT_MET` / `UNKNOWN` with a
  plain-English reason and the quoted source line. Uses structured outputs so the
  shape is guaranteed. Run it against five real trials by hand and paste the
  output into the journal. **This is the go/no-go.** If the verdicts are
  incoherent, say so plainly in the journal and mark the task BLOCKED rather than
  tuning prompts for hours — the human needs to know early.

- [ ] **W1-6** `READY` — End-to-end terminal walkthrough.
  Done when: `python -m whynot.demo "<free text situation>"` runs the whole chain
  — extract profile, query registry, hard filter, split, judge, rank, print — and
  produces readable output for a real query. Still no web UI.

## Week 2 — profile extraction and the shell (Aug 30 – Sep 5)

- [ ] **W2-1** `READY` — Profile extraction from free text via structured outputs.
- [ ] **W2-2** `READY` — FastAPI backend exposing search + judge, key server-side only.
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

- [ ] **D-1** `READY` — GitHub Actions workflow running `just check` on push.
  Done when: `.github/workflows/check.yml` installs `uv`, runs `uv sync --extra dev`
  and `just check` on push and pull request, and a push has produced one green run
  visible with `gh run list`. Rationale: `docs/decisions/0001` treats the remote as
  the backup, but a backup nobody checks can hold broken code. Actions minutes are
  free on this public repository.
