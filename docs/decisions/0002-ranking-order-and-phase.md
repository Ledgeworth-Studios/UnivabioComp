# 0002 — Trials with conflicts are ranked down, never hidden; phase is a tie-break

Date: 2026-08-21

## Context

Task W3-2 asks for a ranking: "hard conflicts, then distance, then phase". Two
parts of that are judgement calls that a later run should not silently reverse.

## Decisions

**A trial the person conflicts with is sorted to the bottom and still shown.**

The alternative — filtering it out — is what every other trial finder does, and
it is the exact behaviour this project exists to argue against. The product is
called "Why Not This Trial". A person who searches and sees four results cannot
tell whether a fifth was removed for a reason they could have argued with: a
birthday next month, a sex field they answered hastily, a diagnosis recorded
under a different name. A person who sees five, one of them greyed with "this
trial enrols ages 10 Years to 17 Years; you told us you are 41 years old", knows
precisely what happened and can decide for themselves whether it is worth a phone
call.

This also keeps the ranking honest about its own limits. The conflicts it can see
are the *structured* ones — age, sex, healthy-volunteer — which are three fields
out of an eligibility section that usually runs to a dozen paragraphs. Hiding a
trial on the strength of three fields would imply a confidence the code does not
have.

**Phase is a tie-break, and the interface must never present it as a
recommendation.**

Sorting by phase in either direction can be read as advice. Earlier-phase first
reads as "newest science first"; later-phase first reads as "safest first".
Both are claims about which trials are better to join, and this tool does not
make claims like that — `CLAUDE.md`'s hard rules say never invent medical logic,
and a sort order is logic.

But two trials with the same conflict status at the same distance still need
*some* order, or the results shuffle between identical calls. So phase is used,
ascending, in the registry's own enumeration order
(`EARLY_PHASE1 < PHASE1 < PHASE2 < PHASE3 < PHASE4 < anything else`), on the
narrow grounds that it is more meaningful than sorting by the alphabet and it is
reproducible. It is documented in `whynot/ranking.py` as a tie-break, and nothing
in the interface labels the order as quality.

If the human entrant wants the opposite direction, it is one line in
`PHASE_ORDER` and one test.

**Unknown sorts last, everywhere.**

A study with no located site has an unknown distance, and a study with no phase
has an unknown phase. Both go to the end. Treating unknown as zero would let a
trial we know nothing about outrank a clinic nine miles away — wrong, and wrong
in a way that would look deliberate.

## Consequences

Results always contain every trial the registry returned for the query, so the
count on screen matches the count the registry reported. A future task that wants
to hide anything — non-patient trials, W3-4, is the obvious candidate — has to
argue for it separately rather than inheriting permission from the ranking.
