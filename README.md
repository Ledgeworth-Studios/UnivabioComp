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

## Repository layout

    CLAUDE.md         operating contract for automated build agents
    BACKLOG.md        the task queue
    docs/PLAN.md      technical plan, verified API facts, rigor rules
    docs/journal/     one entry per build run, in plain English
    docs/decisions/   design decisions and their rejected alternatives

## Development

    just check        # lint, format check, tests
