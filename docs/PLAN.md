# Why Not This Trial — technical plan

## The idea in one paragraph

Everyone builds trial *search*. Nobody builds trial *rejection*. A patient or
caregiver describes their situation in plain English; the app finds recruiting
trials nearby and, for each one, says which eligibility criteria are met, which
are not, and which cannot be determined from what the user told us. The criteria
it cannot determine become **questions to ask the study coordinator** — which is
the actual deliverable the user walks away with, and the thing no existing tool
provides.

## Why three-valued verdicts

Each criterion resolves to `MET`, `NOT_MET`, or `UNKNOWN`. Never a binary match
score, never a percentage.

Most criteria honestly resolve to `UNKNOWN` — they need a lab value, a scan, or a
date nobody typed into a text box. A binary matcher has to fake those. Making
`UNKNOWN` a first-class verdict means the system is never lying, and it converts
the model's genuine uncertainty into the product's most useful output.

The dangerous failure is `NOT_MET` where the truth is `UNKNOWN`: that tells a real
person they don't qualify for a trial they might qualify for. The eval weights
that error specifically.

## Architecture: deterministic where it can be

The registry returns two kinds of data and they get opposite treatment.

**Structured fields** — `minimumAge`, `maximumAge`, `sex`, `healthyVolunteers`.
Filter these in plain Python. The answer is provable, free, and reproducible. No
model touches them.

**Free-text criteria** — one blob of inclusion/exclusion bullets written for
investigators. This is the *only* place a model is permitted to reason.

Pipeline:

| # | Step | Kind |
|---|------|------|
| 1 | Free text → structured patient profile | model |
| 2 | Show profile back as editable chips | deterministic |
| 3 | Query registry: condition + RECRUITING + geo radius | deterministic |
| 4 | Hard filters on structured fields | deterministic |
| 5 | Split criteria, judge each three ways with source quote | model |
| 6 | Rank: conflicts, then distance, then phase | deterministic |
| 7 | Render card + coordinator questions | deterministic |

Sorting, filtering, and arithmetic are never delegated to a model.

## Verified API facts

Checked against the live API on 2026-08-21. Do not re-derive from memory.

- ClinicalTrials.gov **API v2 needs no API key**. Public and unauthenticated.
- A condition + status + geo query returns in roughly 0.3 s.
- Geo filter syntax: `filter.geo=distance(<lat>,<lon>,50mi)`.
- Eligibility age/sex/healthy-volunteer arrive as **structured fields**.
- Inclusion and exclusion criteria arrive as **one free-text blob**, bulleted
  under `Inclusion Criteria:` and `Exclusion Criteria:` headers — but not always;
  handle records with neither header.
- **Trap:** the geo filter matches the *study*, then the response returns **every
  site worldwide** for that study. Computing the nearest site is your job. A naive
  implementation shows a London clinic to someone in Portland.
- **Trap:** not every trial enrols patients. Some enrol clinics, providers, or
  health systems (verified example: `NCT06251323`, whose criteria describe
  federally qualified health centres, not people). Detect and label these; never
  present them as a patient match.

## Model usage

Default `claude-opus-5`. Adaptive thinking is on by default on that model.
Structured outputs via `output_config: {format: ...}` — not the deprecated
`output_format`. Cache the scoring rubric in the system prompt; the per-trial
criteria are the volatile part and go after the cache breakpoint.

Rough cost: extraction is one call per session and is negligible. Judging is the
volume — about 1.5k in / 600 out per trial, so roughly 2.2¢ per trial or 45¢ for
a twenty-trial search on Opus 5. Haiku 4.5 runs the same step at about 0.45¢ per
trial. **Do not pick the cheaper tier by guessing — task W4-4 decides it on eval
numbers.** Build the eval set through the Batch API at half price.

## Rigor rules the code must enforce

These are not aspirational. They are testable and they go in from the start.

1. **Never assert eligibility.** The wording is "you may qualify — only the study
   team can confirm." A tool that says "you are eligible" makes a claim it cannot
   support.
2. **Every reason is traceable.** Each verdict shows the registry sentence it came
   from. No unsourced claims about a trial.
3. **No diagnosis, no treatment advice.** The tool reads a public registry. That
   is the whole scope, and it is stated in the UI.
4. **Nothing stored server-side.** The profile lives in the browser session. Say
   so on screen.
5. **Always link out.** Registry data goes stale; show the trial's status and
   date and link to the source so nothing depends on our copy.

## Out of scope

Not building, and not to be re-proposed without a `docs/decisions/` entry:
training any model (needs a GPU that is not on this machine), medical imaging,
user accounts or stored history, a chatbot wrapper (the chips and cards *are* the
trustworthiness argument), and support for every disease at once — the code stays
general but the demo is one coherent disease area.

## Competition constraints

UnivaBio, deadline 2026-10-06 23:45 EDT, target submit 2026-10-03.
Deliverables: working interactive prototype, demo video, one-page PDF, public
repo. Scored out of 25 across Idea & Innovation, Implementation, Health Impact &
Rigor, Design & Usability, Presentation.

**The rules require the entrant to walk judges through the code.** AI assistance
is explicitly encouraged by the organisers, but comprehension is not optional.
This is why every run writes a plain-English journal entry: read end to end, the
journal is meant to teach the codebase to the person who has to defend it.
