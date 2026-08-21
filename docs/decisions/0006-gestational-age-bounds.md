# 0006 — An age bound in weeks may be a pregnancy, so it is never grounds to rule somebody out

Date: 2026-08-21

## Context

The registry states eligibility ages as strings — `"18 Years"`, `"6 Months"`,
`"3 Days"`. `whynot/hardfilter.py` converts them all onto one scale and compares.

For one kind of trial that conversion is wrong, and wrong in the most dangerous
direction. `NCT01066728` states its bounds as **27 Weeks to 32 Weeks**, and its
criteria text says what they are: *"Infants between 27 and 32 weeks gestational
age hospitalized in the neonatal intensive or intermediate care units."* Those
are weeks **of pregnancy at birth**, not weeks of life.

Converted as ages since birth they become roughly 0.52 to 0.62 years. A
two-week-old baby is 0.04 years, falls outside, and the code said **`NOT_MET`** —
told the parents of a premature infant that their child does not qualify for a
trial their child may well qualify for. `docs/PLAN.md` names that error, `NOT_MET`
where the truth is `UNKNOWN`, as the one to weight above all others.

**The registry has no field distinguishing the two.** Only the prose says, and not
always.

## Decisions

**A bound in weeks between 20 and 45 is treated as possibly gestational.**

A human pregnancy runs about 40 weeks, and gestational ages get quoted from
roughly the edge of viability to a little past term. A bound inside that window
might be either kind. One outside it cannot be a pregnancy.

This matters because the naive fix — treat *every* bound in weeks as ambiguous —
breaks trials that are perfectly clear. `NCT06737159` enrols children from
**5 Weeks** to 24 Months, with bronchiolitis, admitted to hospital. Five weeks is
not a length of pregnancy. That trial can and should still give straight answers,
and there is a test saying so.

**When a bound may be gestational, the verdict is `UNKNOWN` — unless no reading
of it admits the person at all.**

This is the general principle, and it is worth stating beyond this case:

> **A `NOT_MET` requires that no reasonable reading of the registry's wording
> admits the person.** If one reading rules them out and another does not, we do
> not know, and `UNKNOWN` is the honest answer.

So for `NCT01066728`:

| Person | Verdict | Why |
|---|---|---|
| Two weeks old | `UNKNOWN` | Excluded read as age since birth; may qualify read as gestational. |
| Seven months old | `UNKNOWN` | *Inside* the bounds read as age since birth — but under the gestational reading the trial wants a baby born at 27–32 weeks, and the profile does not say. `MET` would be a claim we cannot support. |
| 41 years old | `NOT_MET` | No reading admits them. Under the gestational reading this trial enrols newborns, and they are not one. |

That last row matters: ambiguity is not an excuse to say nothing. Answering
`UNKNOWN` for every adult who searches would be noise, and noise is how a useful
`UNKNOWN` gets ignored.

**One signal is enough to become less certain — the opposite of `docs/decisions/
0003`.**

W3-4 requires *two* independent signals before it will label a trial as enrolling
organisations. Here a single signal — a bound in weeks, in the gestational range —
is enough to withhold a `NOT_MET`, even though the criteria text saying
"gestational" would be corroboration.

The rules point opposite ways because the errors do. There, a false positive
makes a claim about a trial and could bury it; corroboration is protection. Here,
the trigger *removes* a claim, so acting on one signal is the cautious direction,
and demanding corroboration would let the dangerous case through whenever a record
happened not to use the word.

**The newborn window is two years, and deliberately generous.** It decides only
whether we are willing to say `NOT_MET`, so erring large errs towards `UNKNOWN`.

## Consequences

A handful of neonatal trials will return `UNKNOWN` on age where they used to
return an answer, and the reason names the ambiguity and tells the reader to ask
the study team which they mean — which is exactly what a parent should ask.

The general principle above should be applied to any future reading of registry
data where two interpretations disagree. It is a better rule than the specific
one about weeks, and the specific one is only its first instance.
