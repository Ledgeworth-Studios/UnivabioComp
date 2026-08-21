# 0005 — The server keeps nothing, and the interface says exactly what it does send

Date: 2026-08-21

## Context

`docs/PLAN.md` rigor rule 4: *"Nothing stored server-side. The profile lives in
the browser session. Say so on screen."* The interface said so, in the footer:

> Nothing you type here is stored or sent anywhere else.

While scoping W5-4 I checked whether that was true. Both halves of it were wrong.

**"Sent anywhere else"** — the condition and the coordinates are sent to
ClinicalTrials.gov on every search. They have to be; that is what searching a
registry means. The sentence denied the product's own central mechanism.

**"Stored"** — `whynot/api.py` gave every request a `ResponseCache`, which wrote
each registry response body and the time it arrived into `.registry-cache.db`.
Nothing the user typed was written verbatim, and it would have been easy to call
that compliant. It isn't. The stored response to *"multiple sclerosis near
Portland"* is a list of multiple sclerosis trials in Portland, with a timestamp.
Anybody reading that file learns what was searched for, in all but name. Fourteen
such rows were on disk when I looked.

## Decisions

**The response cache is off by default. A server answering real people persists
nothing.**

The cache was built for reproducibility — a demo re-run, an eval re-run and the
fixture recorder all wanting identical bytes — and every one of those has an
*operator* rather than a patient in front of it. So it is opt-in: set
`WHYNOT_CACHE_DB` and you get a cache; do not, and there is no file. The class is
unchanged and the tools that need it still use it.

`tests/test_api.py` runs a search in an empty directory and asserts nothing
appeared. Not a comment promising it — a test that fails if it stops being true.

**The interface states what leaves the browser, precisely, instead of claiming
nothing does.**

Three separate facts, and they are different from each other:

- *Your condition and the place you picked* go to ClinicalTrials.gov. That is the
  search.
- *Your age, sex and whether you are a healthy volunteer* go to our server and no
  further. They are compared against what the registry sends back, and are never
  part of the outbound request. There is a test asserting they never appear in it.
- *Nothing is written down anywhere.*

That is longer than "nothing is stored or sent anywhere else". It has the
advantage of being true, and it is a better answer for a judge who asks.

## Consequences

A live server re-fetches from ClinicalTrials.gov every time, which the plan's own
timing note puts at roughly 0.3 seconds. That is the cost, and it is the right way
round: a repeated search is a little slower, and there is no file anywhere with a
record of who searched for what.

If a deployment ever needs caching for load, it must not be turned back on by
setting the variable and saying nothing. It needs a new decision here, addressing
what is stored, for how long, and what the interface then has to stop claiming.
