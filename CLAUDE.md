# Operating contract for automated build agents

You are one run in a long, interrupted build. **You have no memory of any previous
run.** Everything you need is in this repository. Everything the next run needs,
you must write down before you exit.

Read this file, then `BACKLOG.md`, then the newest two files in `docs/journal/`.
That is your entire context. Do not assume anything not written there.

## What this project is

"Why Not This Trial" — a clinical-trial finder whose distinguishing feature is
that it explains **why you don't qualify** and turns everything it is unsure
about into questions to ask a study coordinator. Full rationale: `docs/PLAN.md`.

Submission: UnivaBio hackathon, deadline **2026-10-06 23:45 EDT**. Target submit
date is **2026-10-03**, leaving three days of slack. Do not spend the slack.

## Attribution — read this before your first commit

**Never record Claude, Anthropic, or any AI tool as an author or contributor of
this repository.** Specifically:

- Do **not** add `Co-Authored-By: Claude` (or any AI co-author) trailer.
- Do **not** set `user.name` or `user.email` to Claude or Anthropic, and do not
  pass `-c user.name=...` to override the configured identity.
- Do **not** sign commits, PRs, or generated files with an AI byline, and do not
  add "Generated with…" footers.

The repository is configured with the correct identity already. Commit with a
plain `git commit` and let the configured author stand. Verify before you push:

    git log --format='%an <%ae>' | sort -u        # must list only the human
    git log --format='%B' | grep -i 'co-authored\|claude\|anthropic'   # must be empty

## Where the repository lives

Canonical path: `/Users/patrickbosma/GitHub/UnivabioComp`

`~/Documents/GitHub` is a **symlink** to `~/GitHub`. If you encounter that path,
it is the *same directory*, not a second clone. Never "clean up a duplicate" —
there isn't one, and deleting it destroys the only working tree.

## The loop you are part of

Work through tasks one at a time, in this cycle, and **repeat the cycle** until
there are no `READY` tasks left or the run ends for reasons outside your control:

1. Read `BACKLOG.md`. Find the first task with status `READY`.
2. Change its status to `DOING` and commit that change **before** starting work.
   This is how a run that dies partway is detected by the next run.
3. Do the task. Only that task — do not fold the next one into it.
4. Run the checks (below). They must pass.
5. Set the task to `DONE`, add anything you discovered as new `READY` tasks.
6. Write a journal entry (below).
7. Commit, then push.
8. Go back to step 1.

Your run will most likely end by hitting a usage limit somewhere in the middle of
this cycle. That is expected and is not a failure. It is also exactly why step 2
exists: the next run, five hours later, reads the `DOING` marker and knows where
you stopped. Leave the repository in a state that says what happened.

If the first task you find is already `DOING`, a previous run died there. Inspect
the working tree, finish or revert it, note what happened in the journal, and
continue.

## Hard rules

- **One task per commit, one journal entry per task.** A run may work through
  many tasks, but never batch them: a commit covering three tasks cannot be
  reverted cleanly, and a journal entry covering three tasks teaches nothing.
- **Never mark a task DONE that you did not verify.** The done-criteria are
  written on each task. If you cannot meet them, set the task back to `READY`,
  write down precisely what blocked you, and stop. A blocked task honestly
  reported is worth more than a task falsely closed.
- **Never invent medical logic.** This tool reads a public registry. It does not
  diagnose, does not advise treatment, and never asserts that a person is
  eligible for a trial — only that they *may* qualify and should ask.
- **Never commit secrets.** No API keys, no `.env`. Check before every commit.
- **Never delete a directory you did not create in this run.** If something looks
  like stray duplicate state, write it in the journal and leave it alone.
- **Do not restructure work that is already done** to suit your preferences.
  If you think an earlier decision was wrong, write it in `docs/decisions/` and
  add a `READY` task proposing the change. Do not unilaterally rewrite.
- **Write code the human can explain to a judge.** This is a competition rule,
  not a style preference: the entrant must be able to walk judges through the
  code. Prefer the obvious implementation. No clever abstractions, no dependency
  that saves ten lines and costs an explanation.

## Checks that must pass before DONE

    just check        # if a justfile exists; otherwise:
    ruff check . && ruff format --check . && pytest -q

If the project has no tests yet because you are early in the backlog, say so
explicitly in the journal rather than silently skipping.

## Journal entry — required, every run

Write `docs/journal/YYYY-MM-DD-HHMM-<task-id>.md`:

```
# <task-id> — <one line: what changed>

**Status:** DONE | BLOCKED
**Files touched:** ...

## What I did
Plain English. Assume the reader is the human entrant who has not read the code.

## Why I did it this way
The decision and the alternative you rejected.

## What the next run should know
Anything surprising. Anything half-finished. Anything you would want told to you
if you were starting cold — because the next run is you, starting cold.
```

The "What I did" section is not bookkeeping. The human has to explain this
codebase to judges on camera. Write it so that reading the journal end to end
teaches the codebase.

## Push rule

**Push after every task.** Do not batch pushes.

This repository is public, so GitHub Actions minutes are unlimited and free —
there is no cost to pushing often. The cost runs the other way: work that exists
only in the local clone has no backup, and unpushed commits have already been
lost once on this project. The remote is the backup. Use it.

## Vault

Mirror each journal entry into the Obsidian vault when the vault is reachable at
`~/Desktop/Claude/Projects/UnivaBio/`. If that path does not exist, you are
running somewhere without the vault — skip it, and note the skip in the journal.
Never fail a run because the vault is absent.
