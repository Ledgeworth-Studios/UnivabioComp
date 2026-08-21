# 0001 — Repository is the only shared state; attribution is human-only

Date: 2026-08-21

## Context

This project is built by scheduled, unattended runs that fire every five hours
and have no memory of each other. Two constraints follow.

## Decisions

**All continuity lives in the repository.** `CLAUDE.md` (contract), `BACKLOG.md`
(queue), `docs/journal/` (handoff). A run that leaves knowledge only in its own
context has lost it. The `DOING` marker is committed *before* work starts so an
interrupted run is detectable rather than invisible.

**Commits are attributed to the human entrant only.** No AI co-author trailers,
no AI author identity, no generated-by footers. The repository has a local
`user.name` / `user.email` set for this purpose; runs commit plainly and let it
stand.

**Push after every task.** Originally pushes were batched to conserve GitHub
Actions minutes. That rationale was wrong — this repository is public, and public
repositories get unlimited free standard-runner minutes. Batching had a real cost
and no benefit: on 2026-08-21 the working tree was deleted while two commits were
unpushed, and that work was unrecoverable. The remote is the backup.

**`~/Documents/GitHub` is a symlink to `~/GitHub`.** It is not a second clone.
This is recorded because it was misread as duplicate state once, and acting on
that misreading is what destroyed the working tree.

## Consequences

More commits and more pushes than a human-paced project would produce. That is
the intended trade: cheap, frequent, recoverable checkpoints over tidy history.
