# 0004 — What a verdict means on an exclusion criterion, and who may write the answer key

Date: 2026-08-21

## Context

W4-1 builds the eval set the judge will be marked against. Writing it surfaced
two questions that W1-5 (the judge itself, still blocked on an API key) had left
implicit. Both have to be settled before the judge is written, not after, because
either one silently corrupts every number Week 4 produces.

## Decisions

### A verdict answers one fixed question, whatever kind of criterion it is

> **`MET` means: this criterion, as written, describes the person.**

For an inclusion criterion that reads naturally — "age 18 to 55" is `MET` for a
41-year-old, and they are a step closer to qualifying.

For an **exclusion** criterion it inverts, and this is the trap: "Diagnosis of
progressive forms of MS" is `MET` for somebody who has progressive MS — and being
`MET` there is what *rules them out*. `MET` never means "good news". It means the
sentence is true of this person.

The alternative convention — `MET` meaning "this criterion is satisfied in the
direction of enrolling" — was rejected because it requires the judge to work out
the criterion's polarity before answering, and polarity is exactly the thing that
is easy to get wrong in a blob of prose with inconsistent headers (W1-4 found
records with the headers written as bullets, and records with no headers at all).
Under the chosen convention the judge answers a question about a sentence and a
person, and the *interface* applies the polarity, using the inclusion/exclusion
tag `whynot/criteria.py` already produces.

**W1-5's prompt must state this convention explicitly.** If the judge assumes the
other one, every exclusion criterion in the eval scores backwards, and the overall
number will still look plausible.

### An agent may propose a label. It may not confirm one.

The eval set is the answer key. If the same class of system writes the answers and
the key, the number measures agreement rather than correctness — and that number
is going in front of competition judges, attached to a claim about a medical tool.

So every pair in the eval set carries:

- `expected` — the proposed verdict,
- `basis` — the reasoning, in a sentence, so it can be argued with,
- `needs_human_review` — whether confirming it takes judgement,
- `reviewed_by` — who confirmed it. Empty until a person does.

And `whynot/evalset.py` will not hand a pair to the scoring code if it needs human
review and has not had it. Not a warning — it is excluded from the count, and the
exclusions are reported alongside the score.

**Labels that do not need review** are the ones derivable by reading alone: the
profile says nothing whatever about MRI lesions, so a criterion about MRI lesions
is `UNKNOWN`; the profile says 41 and the criterion says 18 to 55, so it is `MET`.
No clinical knowledge is involved in either. Requiring a human for those would
stall the eval for no gain — and they are the majority of the interesting cases,
because `NOT_MET`-where-the-truth-is-`UNKNOWN` is the error `docs/PLAN.md` weights
hardest and it lives precisely in the "profile is silent" category.

**Labels that do need review** are the interpretive ones: whether somebody's own
statement that they have MS satisfies "confirmed diagnosis of MS by a physician",
or whether "relapsing-remitting MS" excludes them from a trial that bars
"progressive forms". Those are marked, and they are the human's to settle.

## Consequences

W4-2 cannot report a complete accuracy figure until a person reviews the flagged
pairs. That is a real dependency on the human, alongside the API key, and it
should be stated wherever the eval number is presented: how many pairs were
scored, and how many were held back for want of a review.
