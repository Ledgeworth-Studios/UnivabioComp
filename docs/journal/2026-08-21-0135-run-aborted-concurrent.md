# run-aborted-concurrent — a second run was already building; this run stood down

**Status:** BLOCKED (deliberately — aborted to avoid corrupting a healthy run)
**Files touched:** this journal entry only. No code, no `BACKLOG.md`, no commits
to any task.

## What I did

Nothing to the build — on purpose. I found another agent run already working this
repository, alive and making good progress, so I stopped rather than trample it.

Here is how that unfolded, because the detection is the useful part.

I started at 01:26:36. My instructions say: if the working tree is dirty, a
previous run died mid-task, so work out what happened and finish it. The tree
*was* dirty, and `BACKLOG.md` had **W1-1** marked `DOING` with an uncommitted
project skeleton sitting next to it. That is exactly the fingerprint of a run
that died partway, so I began treating it as one. I read the skeleton and
verified W1-1's done-criteria honestly — `just check` passed, exit 0, ruff and
pytest clean, `.gitignore` covering the required paths — and went to mark it
`DONE`.

That edit failed, because the file no longer said what I had just read. In the
sixty seconds between my reading `BACKLOG.md` and my editing it, someone else had
marked W1-1 `DONE` and appended a new discovered task **D-1** that I had never
written. Files do not edit themselves, so I stopped changing things and went
looking for who did.

It was another run of this same scheduled task: process 36175, started 01:19:54,
about seven minutes before me. I confirmed it was genuinely alive rather than a
stalled process holding a stale tree, by watching two things at once over several
minutes — its accumulated CPU time (climbing steadily, 18.0s to 20.0s, so it is
executing, not hung) and the repository's commit history (advancing under me:
W1-1 committed, W1-2 marked `DOING`, W1-2 committed, W1-3 marked `DOING`). A dead
process does neither.

By the time I finished checking, that run had completed W1-1 and W1-2 with proper
journal entries for both and was into W1-3. It is doing the job correctly. So the
most useful thing I could do was get out of its way and leave a note explaining
why this run looks empty.

I made no commits, pushed nothing, and modified no file other than this entry.
The uncommitted files in the tree right now (`whynot/profile.py`,
`tools/record_fixtures.py`, a fixtures JSON) belong to the other run's current
task. **They are not abandoned work — do not clean them up.**

## Why I did it this way

The alternative was to keep working. I rejected it: two agents on one backlog is
worse than one agent, not twice as good. We would both take "the first READY
task" and get the same one, double-commit it, write duplicate journal entries,
and race each other on `git push`. Worse, the `DOING` marker is the only mechanism
this project has for detecting a dead run, and it only works if exactly one writer
touches it — two writers turn the recovery protocol itself into a source of
corruption.

I also deliberately did **not** add a task to `BACKLOG.md` about this, even though
the underlying problem deserves one. The other run is actively flipping statuses
in that exact file; me editing it concurrently is the precise failure I just
decided to avoid. The recommendation is below instead, for a run that has the repo
to itself.

## What the next run should know

**The big one: a dirty tree plus a `DOING` marker does not prove the previous run
died.** It might be alive and working, and it takes under a minute to tell the
difference. `CLAUDE.md` and the scheduled-task instructions both currently assume
dirty means dead. That assumption is wrong and it nearly made me stomp on a
healthy build.

Before adopting an in-progress task, check for a live peer:

```bash
ps -eo pid,%cpu,lstart,command | grep '[c]laude' | grep -v "$$"
```

If a `claude` process started before yours, sample its cumulative CPU twice about
twenty seconds apart (`ps -o time= -p <pid>`). If the number climbs, it is working
— stand down. Also just watch `git rev-parse HEAD` for a minute; if commits are
landing, you are not alone.

**The root cause is that this scheduled task has no concurrency guard**, so two
runs can overlap whenever one outlives its interval or a run is launched manually
while another is scheduled. Someone should add a lock — the simplest honest fix is
for the run to take an exclusive lockfile at start and exit immediately if it
cannot get it, for example wrapping the run in `flock -n
/tmp/univabio-build.lock`, or writing a PID file into the repo's ignored state and
checking that the recorded PID is not still alive. That is worth a `Discovered`
task; I did not add it myself for the reason given above.

**Nothing here needs repairing.** W1-1 and W1-2 are committed, verified and
journalled by the other run. W1-3 was in progress when I stopped. The one thing I
independently confirmed and can vouch for is that W1-1's done-criteria genuinely
pass — I ran `just check` myself and it exited 0 — so that task is not falsely
closed.

**D-1 (a GitHub Actions workflow running `just check` on push) was added by the
other run, not by me.** I mention it only so nobody mistakes it for orphaned or
duplicated state.
