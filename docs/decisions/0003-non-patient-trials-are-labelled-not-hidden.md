# 0003 — Trials that look like they enrol organisations are labelled, not hidden

Date: 2026-08-21

## Context

Some registry entries that read like ordinary patient trials in fact enrol
clinics, practices or health systems. `docs/PLAN.md` names a verified example,
`NCT06251323`, and says: "Detect and label these; never present them as a patient
match."

Detection cannot be exact. The registry has no field that says "this study enrols
organisations". The evidence is a purpose code plus the way the eligibility text
is written, and both can be present in studies that really do enrol people.

## Decisions

**Detection requires at least two independent signals.**

One mention of a clinic or a practice in eligibility criteria means nothing.
Patient trials routinely say "currently hospitalised", "able to attend the study
site", "resident in a nursing home", "referred by a physician practice". Any of
those would trip a single-keyword rule. Requiring corroboration — the purpose
code *and* the wording, or two independent features of the wording — turns a
coincidence into a pattern. `tests/test_nonpatient.py` pins each of those four
ordinary phrases as insufficient on its own.

**The word list is short on purpose.** Every term had to survive one question:
could this word appear in the criteria of a trial that enrols people? "Hospital"
and "site" fail it and are deliberately absent. What is left — FQHC, health
system, clinic site, participating practices, patient population — is wording
that is hard to write about a single human being.

**A flagged trial is labelled, and is not hidden and not moved.**

This follows `docs/decisions/0002`, which deliberately did not grant permission to
remove anything from the results. It also follows from the direction of the risk.
A false positive that merely adds a caution costs the reader ten seconds. A false
positive that hides or demotes the trial costs them a study they could have
joined and never heard about — the same class of harm as a `NOT_MET` that should
have been `UNKNOWN`, which `docs/PLAN.md` says to weight hardest.

Ranking it down was tempting and was rejected for the same reason: quieter
consequences for our mistakes, worse consequences for the reader's.

**The caution is worded as a possibility, and shows its evidence.**

The wording is "may not be one you can join as a patient. We could be wrong — the
evidence is below, and the study team can tell you for certain", and the signals
that fired are printed underneath with the registry text they matched. A reader
who can see *why* the tool thinks this can overrule it. A test asserts the caution
never says "you cannot join" or "you are not eligible".

## Consequences

We will occasionally caution a trial that does enrol people. That is the intended
trade, and it is visible: the evidence is on the card, so the mistake is
inspectable rather than silent. If the registry ever adds a field stating the
unit of enrolment, this whole module should be replaced by it — there is a test
(`test_that_trial_looks_perfectly_ordinary_in_its_structured_fields`) that starts
failing if the structured fields ever become sufficient on their own.
