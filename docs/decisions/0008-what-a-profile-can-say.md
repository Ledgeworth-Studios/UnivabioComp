# 0008 — A profile holds what a person says in a sentence, and nothing more

Date: 2026-08-21

## Context

`PatientProfile` had four fields: age, sex, healthy-volunteer, and a list of
condition names. Almost every criterion that actually decides a trial is
unanswerable from those — "diagnosed within the last five years", "not previously
treated with ocrelizumab", "EDSS score of 0 to 5.5".

That is measurable rather than theoretical. The W4-1 eval set came out **27
`UNKNOWN` against 2 `MET` and 2 `NOT_MET`**, and it came out that way because the
profile cannot describe anybody. It makes a good instrument for the error we care
most about and a weak one for everything else.

## Decisions

**Three fields are added:** when they were diagnosed, what they are being treated
with now, and what they have been treated with before.

    diagnosed_year        "diagnosed in 2019"
    current_treatments    "I'm on ocrelizumab"
    past_treatments       "I was on interferon for a few years"

**The test each field had to pass: would a person say this in a sentence about
their situation, unprompted?** Not "would a trial want to know" — a trial would
want to know fifty things. The pipeline's first step is meant to be *free text in,
profile out* (`W2-1`), and a field that nobody would ever say out loud is a field
the extraction step can never fill. It would sit empty forever and quietly make
every criterion touching it `UNKNOWN`, which is where we already are.

Those three pass. People say when they were diagnosed, and what they are on. It
is how anybody describes a long-term condition.

**What was rejected, and why.**

*Lab values and disease scores* — EDSS, A1c, ejection fraction. A trial cares
enormously; a person does not volunteer them, and asking would turn this into a
clinical intake form. Criteria needing them stay `UNKNOWN` and become questions
for the study team, **which is the product working, not the product failing.**

*Pregnancy, and anything else a trial screens for but a stranger should not be
asked.* The tool has no business collecting it, and a criterion about it is
exactly the sort of thing the coordinator questions exist to raise.

*A free-text "anything else" box.* Tempting, and it would collect real
information. But nothing downstream could use it without a model reading it, so
it would be a field with no consumer wearing the costume of a feature — and it
would collect sensitive text this project has promised not to keep.

**Every field is optional, and `null` when unstated — never `""` or `0`.** The
existing rule, restated because there are now more fields to get it wrong on.
`web/src/profile.test.ts` guards it.

**Every field must have a consumer.** This project keeps rediscovering the same
defect in different costumes: something built, plausible, and read by nothing.
The three fields are consumed today by the chips, by the printable sheet a person
takes to an appointment, and by the eval set. A test walks every key of the
profile and asserts it reaches a chip, so a field cannot be added and left
invisible.

## Consequences

The eval set can now express criteria that resolve to something other than
`UNKNOWN`, which makes it a better instrument for W4-2 — though the labels for
anything interpretive still need the human review `docs/decisions/0004` requires.

The extraction step W2-1 has three more fields to fill, all of which appear in an
ordinary sentence, which is what it will be given.

**The list is not meant to grow much.** If a fourth field is proposed, it has to
pass the same test — would somebody say it unprompted — and find a consumer before
it is added. "A trial would want to know" is not a reason; that is what the
coordinator questions are for.
