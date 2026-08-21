% Why Not This Trial
% Everybody builds clinical trial search. Nobody builds trial rejection.

## The problem

There are about 70,000 trials recruiting worldwide, and finding one is not the
hard part. Working out whether you could actually join it is. Eligibility is
written for investigators — a dozen paragraphs of clinical prose per study — and
every tool that tries to match a patient against it does the same thing: returns
a list, or a percentage, and leaves the person to guess what a 63% match means.

The information a patient can act on is not the list. It is the specific reason
one trial is closed to them, and the specific questions they should ask about the
ones that aren't.

## What this does

- **Explains the rejection.** Not "no match" — *"this trial enrols ages 10 to 17;
  you told us you are 41"*, with the registry's own sentence printed underneath.
- **Treats "we don't know" as an answer.** Every criterion resolves to `MET`,
  `NOT_MET`, or `UNKNOWN`. Most honestly resolve to `UNKNOWN` — they need a lab
  value, a scan, a date nobody typed into a text box.
- **Turns those unknowns into questions for the study coordinator**, on a page
  you can print and take to an appointment. That is the thing you walk away with.
- **Never hides a trial you conflict with.** It sorts to the bottom, explained.
  A person who sees four results cannot tell whether a fifth was removed for a
  reason they could have argued with.

## Why three-valued verdicts

A binary matcher has to fake the unknowns. Making `UNKNOWN` a first-class verdict
means the system is never lying, and it converts the model's genuine uncertainty
into the product's most useful output.

The dangerous failure is `NOT_MET` where the truth is `UNKNOWN`: telling a real
person they don't qualify for a trial they might qualify for. The evaluation
weights that error specifically, and the code is built around avoiding it — an
unstated age stays null the whole way to the search rather than defaulting to
zero, because zero would rule the person out of every adult trial in the registry.

## Two things found in the real registry

- **The distance filter is a trap.** Filter by 50 miles of Portland and the API
  matches the *study*, then returns **every site that study has, worldwide**, in
  its own order. One trial in the demo has 91 sites and lists Birmingham, Alabama
  first. The obvious implementation sends a Portland patient to Alabama.
- **Not every trial enrols people.** `NCT06251323` reads as an adult type 2
  diabetes study — ages 18 and up, all sexes, healthy volunteers accepted — and
  its participants are federally qualified health centres. Flagged, with the
  evidence shown, never hidden.

## What is built

The registry client, the deterministic age/sex/healthy-volunteer checks, criteria
splitting, ranking, coordinator questions, non-patient detection, the printable
sheet and the web interface — all working against the live registry, no API key
required. 248 tests, none of which touch the network.

Reading the free-text criteria with a model, and the accuracy evaluation that
measures it, are built up to the point where they need an API key the build
environment did not have. The eligibility criteria are shown on every card in the
registry's own words, labelled plainly as not yet checked against you.

## Built with

Python, FastAPI and the ClinicalTrials.gov v2 API; React, TypeScript and Vite.
Sorting, filtering and arithmetic are never delegated to a model — only the
free-text criteria are.

github.com/Ledgeworth-Studios/UnivabioComp
