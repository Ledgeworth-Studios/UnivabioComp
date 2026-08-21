# Demo video script

**Before you record, check two things.**

1. **The length limit.** As written this runs **3:13**. The limit was not
   confirmed — `univabio.devpost.com` returns nothing readable to an automated
   fetch, so nobody has verified it from this repository. Look it up on the
   submission page.
   **If the limit is three minutes, drop Beat 4 (`[CUT 3]`) and it comes to
   2:52.** Cut further in the order marked **[CUT n]**; the script is arranged so
   dropping them costs supporting material and never the argument.
2. **That the demo still runs.** Registry data changes. Do a full rehearsal the
   day you record — every number spoken below is quoted from a real run and each
   one names where it was verified, so you can check it rather than trust it.

Set up beforehand: `just install`, then `just dev`, browser at
<http://localhost:5173>, window at a size where the trial cards are readable.
Search **multiple sclerosis**, near **Portland, Oregon**, **50 miles**.

---

## Beat 1 — the problem (0:00–0:25)

**On screen:** you, or a still of a real eligibility criteria block from
ClinicalTrials.gov — a wall of clinical prose.

> About seventy thousand clinical trials are recruiting right now. Finding one
> isn't the hard part — working out whether you could actually join it is.
> Eligibility is written for investigators: a dozen paragraphs of clinical prose
> per study.
>
> Every tool that helps does the same thing. It hands you a list, or a percentage.
> Nobody knows what a sixty-three per cent match means.

## Beat 2 — the idea, in one sentence (0:25–0:40)

**On screen:** the app, freshly loaded, nothing searched yet.

> Everybody builds trial search. I built trial *rejection*. It tells you which
> criteria you don't meet and why — and, more usefully, which ones nobody could
> tell from what you've said. Those become questions for the study team.

## Beat 3 — the live run, and the whole argument (0:40–1:33)

**This is the beat that has to land. Do not cut it.**

**On screen:** search multiple sclerosis near Portland. Six results.

> Six recruiting trials near Portland. I haven't told it anything about myself
> yet.

**Click the Age chip, type 41, press Enter.**

> Now watch this one.

**On screen:** the paediatric trial, now last, marked as a conflict.

> *"This trial enrols ages 10 to 17; you told us you are 41."* Not "no match" —
> the actual reason, with the registry's own sentence printed underneath so you
> can check it.
>
> And it's still on the list — at the bottom, explained. Hide it, and you'd never
> know whether it went for a reason you could argue with: a birthday next month, a
> field you answered too quickly.

**Change the age chip to 12.**

> Same six trials. Different person. Everything re-explains itself — now the adult
> trials are the conflicts, and the children's trial is at the top.

**Clear the age chip (the × on it).**

> And if I say nothing at all, nothing is held against me. It doesn't guess. It
> says *not settled* and offers to ask.

*Verified in `docs/journal/2026-08-21-0546-W2-4.md` and re-checked from a clean
clone in `docs/journal/2026-08-21-1012-W6-1.md`.*

## Beat 4 — a real trap in real data (1:33–1:54) **[CUT 3]**

**On screen:** point at the nearest-site line on the BRIUMVI trial.

> This trial has ninety-one sites. The registry's distance filter matches the
> *study*, then hands back every one of them in its own order — and lists
> Birmingham, Alabama first.
>
> The obvious implementation sends a Portland patient to Alabama. This one
> measures every site and shows the one six-tenths of a mile away.

*Verified in `docs/journal/2026-08-21-0534-W2-2.md`.*

## Beat 5 — the thing you walk away with (1:54–2:22)

**On screen:** scroll to the questions on a card, then click **Take these to your
appointment**.

> Everything it couldn't determine becomes a question — and it's careful about
> who can answer. If the registry didn't say, that's for the study team. If *you*
> didn't say, that's not a question for anybody; it's a box you can fill in.
> Asking a research nurse how old you are would be absurd.
>
> And this is the deliverable. One page: which trials, where, what would stop you,
> what to ask.

*Verified in `docs/journal/2026-08-21-0558-W3-3.md` and
`docs/journal/2026-08-21-0607-W3-5.md`.*

## Beat 6 — rigor (2:22–2:42) **[CUT 2]**

**On screen:** search **type 2 diabetes**; find the flagged trial.

> This reads like an adult diabetes study — eighteen and up, all sexes, healthy
> volunteers welcome. Its participants are health centres. You cannot enrol.
>
> So it's flagged, with the evidence shown — and still not hidden, because the
> detection is a guess and you should be able to overrule it.

*Verified in `docs/journal/2026-08-21-0603-W3-4.md`.*

## Beat 7 — what's built, honestly (2:42–3:13)

**On screen:** the "what this tool will and won't do" panel, or the README's
built/not-built table.

> All of that runs against the live registry, with no API key. What isn't built
> is reading the criteria with a model, and the evaluation that measures it — both
> stopped where they needed a key I didn't have.
>
> So the criteria sit on every card in the registry's own words, labelled as not
> yet checked. Because the one thing this must never do is say *you don't qualify*
> when the honest answer is that nobody knows.

---

## If you get an API key before recording

Then the eval number exists, and **it goes at the start of Beat 7**, replacing the
"what isn't built" paragraph:

> Across a labelled set of real registry criteria, the judge agreed with a human
> reviewer on __%. And the number I care about most is this one: it said
> *"you don't qualify"* when the truth was *"nobody can tell"* __ times.

Do not speak that sentence with a number in it until `just check` has produced
one — and note that five labels in the eval set need a human review before the
figure means anything (`docs/journal/2026-08-21-0613-W4-1.md`).

## Where the timings come from

Each beat's duration is its spoken word count at **150 words a minute**, which is
an unhurried speaking pace. They are measured, not estimated — if you rewrite a
beat, re-measure rather than guessing:

```bash
python3 - <<'EOF'
import pathlib, re
text = pathlib.Path("docs/demo-script.md").read_text()
total = 0
for b in re.split(r"^## ", text, flags=re.M):
    title = b.splitlines()[0] if b.strip() else ""
    if not title.startswith("Beat "):
        continue
    words = sum(len(l[2:].split()) for l in b.splitlines() if l.startswith("> "))
    total += words
    print(f"{title[:44]:46} {words:4d}w ~{words / 150 * 60:5.1f}s")
print(f"{'TOTAL':46} {total:4d}w ~{total / 150 * 60:5.1f}s")
EOF
```

Only lines beginning `> ` count — those are the ones you say out loud. If you
speak faster than 150 a minute, you have slack; do not use it to add a beat.

## Cut order

If you need to be shorter than three minutes, drop in this order:

- **[CUT 1]** the second half of Beat 1 — go straight from "seventy thousand
  trials" to Beat 2.
- **[CUT 2]** Beat 6, the health-centres trial.
- **[CUT 3]** Beat 4, the ninety-one sites.

Beats 2, 3, 5 and 7 are the submission. Do not cut those: they are the idea, the
proof, the deliverable, and the honesty.

## Things not to say

- Never *"you're eligible"* or *"you qualify"*. The tool never says it and neither
  should the video. *"Nothing here rules you out"* is the claim it supports.
- Do not call it accurate, or say it was tested, in a way that implies the
  criteria judging works. It is not built.
- Do not say the interface is accessible. Contrast, keyboard paths and semantics
  were measured and fixed, but it has never been tested with a screen reader
  (`docs/journal/2026-08-21-0923-W5-3.md`).
