"""One build run at a time.

On 2026-08-21 two scheduled runs fired at the same time on this repository. The
second one noticed the first by hand, stood down, and nothing was lost — but it
noticed by *reading the git log and thinking about it*, which is not a guarantee.
This script makes it a guarantee.

    uv run python tools/runlock.py acquire     # at the start of a run
    uv run python tools/runlock.py tick        # after each commit
    uv run python tools/runlock.py release     # at the end of a run
    uv run python tools/runlock.py status      # who holds it, if anyone

`acquire` exits **0** if this run may proceed and **1** if a live run already
holds the lock. `CLAUDE.md` tells runs to stand down on a non-zero exit.

## Why a heartbeat file and not `flock`

The obvious answer is an operating-system lock — `flock(2)` on a file. It does
not work here. A scheduled agent run is not one process: it is dozens of short
shell commands, one after another, each exiting before the next begins. An OS
lock dies with the process that took it, so it would be released between the
first command and the second.

So the lock is a *file with a timestamp in it*, and a run proves it is still
alive by touching that timestamp. A lock nobody has touched for
`STALE_AFTER_MINUTES` is assumed to belong to a run that died, and the next run
takes it over and says so out loud.

Creating the file uses `O_CREAT | O_EXCL`, which the operating system guarantees
is atomic: if two runs try to create it in the same instant, exactly one wins.
That is the part that has to be exactly right, and it is one line.

## The two numbers

`STALE_AFTER_MINUTES = 90` sits between two real durations. A run works for well
over an hour, so the window must be longer than the gap between its commits, or
a live run would be judged dead. Scheduled runs are five hours apart, so a lock
left behind by a crashed run is always long stale by the time the next one asks
for it. Ninety minutes clears both.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

#: A lock untouched for this long belongs to a run that died. See module docstring.
STALE_AFTER_MINUTES = 90

#: Lives in the repository root, and is gitignored: it is machine state, not project state.
DEFAULT_LOCK_PATH = Path(__file__).resolve().parents[1] / ".runlock"


def lock_path() -> Path:
    """Where the lock file lives. The environment variable exists for the tests."""
    override = os.environ.get("WHYNOT_RUNLOCK")
    return Path(override) if override else DEFAULT_LOCK_PATH


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class LockRecord:
    """What one holder wrote into the lock file."""

    run_id: str
    host: str
    started: str
    last_seen: str
    label: str

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2, sort_keys=True) + "\n"

    @staticmethod
    def from_json(text: str) -> LockRecord:
        data = json.loads(text)
        return LockRecord(
            run_id=str(data["run_id"]),
            host=str(data.get("host", "?")),
            started=str(data.get("started", "?")),
            last_seen=str(data["last_seen"]),
            label=str(data.get("label", "")),
        )


def _new_run_id() -> str:
    """A readable, unique-enough name for one run: when it started and its pid."""
    return f"{_now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"


def age_minutes(record: LockRecord, path: Path) -> float:
    """How long since the holder last proved it was alive.

    Falls back to the file's modification time when `last_seen` is unreadable, so
    a corrupt lock still ages out instead of blocking the project forever.
    """
    try:
        seen = datetime.fromisoformat(record.last_seen)
    except (TypeError, ValueError):
        seen = datetime.fromtimestamp(path.stat().st_mtime, UTC)
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    return (_now() - seen).total_seconds() / 60.0


def read_lock(path: Path) -> LockRecord | None:
    """The current holder, or None if the file is missing or unreadable.

    An unreadable lock file is reported as a holder with an unknown identity
    rather than as "no lock", so that a corrupt file is never silently ignored —
    it ages out through `age_minutes` instead.
    """
    if not path.exists():
        return None
    try:
        return LockRecord.from_json(path.read_text())
    except (OSError, ValueError, KeyError):
        stamp = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        return LockRecord(
            run_id="unreadable",
            host="?",
            started=stamp,
            last_seen=stamp,
            label="lock file could not be parsed",
        )


def _write_record(path: Path, record: LockRecord) -> None:
    path.write_text(record.to_json())


def acquire(path: Path, label: str, stale_after: float) -> tuple[bool, str]:
    """Take the lock. Returns (may_proceed, message_for_the_human).

    Three outcomes, and the caller can tell them apart from the message:
      - nobody held it        -> taken
      - a live run holds it   -> refused, caller must stand down
      - a dead run holds it   -> taken over, loudly
    """
    record = LockRecord(
        run_id=_new_run_id(),
        host=socket.gethostname(),
        started=_now().isoformat(),
        last_seen=_now().isoformat(),
        label=label,
    )

    try:
        # O_EXCL is the whole lock: the OS guarantees only one caller creates the file.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w") as handle:
            handle.write(record.to_json())
        return True, f"lock acquired by run {record.run_id}"

    held = read_lock(path)
    if held is None:
        # It was released in the moment between our failed create and this read.
        _write_record(path, record)
        return True, f"lock acquired by run {record.run_id} (previous holder released it)"

    idle = age_minutes(held, path)
    if idle < stale_after:
        return False, (
            f"STAND DOWN: run {held.run_id} on {held.host} holds this lock and was "
            f"alive {idle:.0f} minutes ago (started {held.started}). "
            "Do not touch the repository. Write a one-line journal entry and exit."
        )

    _write_record(path, record)
    return True, (
        f"took over a stale lock: run {held.run_id} last checked in {idle:.0f} minutes ago "
        f"(limit {stale_after:.0f}). It probably died mid-task — inspect the working tree "
        f"and say so in the journal. This run is {record.run_id}."
    )


def tick(path: Path) -> tuple[bool, str]:
    """Prove this run is still alive. Called after every commit."""
    record = read_lock(path)
    if record is None:
        return False, "no lock file to tick — run `just lock` first"
    _write_record(
        path,
        LockRecord(
            run_id=record.run_id,
            host=record.host,
            started=record.started,
            last_seen=_now().isoformat(),
            label=record.label,
        ),
    )
    return True, f"run {record.run_id} checked in"


def release(path: Path) -> tuple[bool, str]:
    """Give the lock up at the end of a run."""
    record = read_lock(path)
    if record is None:
        return True, "no lock was held"
    path.unlink()
    return True, f"lock released by run {record.run_id}"


def status(path: Path, stale_after: float) -> tuple[bool, str]:
    record = read_lock(path)
    if record is None:
        return True, "nobody holds the lock"
    idle = age_minutes(record, path)
    state = "STALE" if idle >= stale_after else "live"
    return True, (
        f"{state}: run {record.run_id} on {record.host}, "
        f"started {record.started}, last seen {idle:.0f} minutes ago"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One build run at a time.")
    parser.add_argument("command", choices=["acquire", "tick", "release", "status"])
    parser.add_argument("--label", default="", help="free text describing this run")
    parser.add_argument(
        "--stale-minutes",
        type=float,
        default=STALE_AFTER_MINUTES,
        help="a lock untouched for this long is treated as abandoned",
    )
    args = parser.parse_args(argv)

    path = lock_path()
    if args.command == "acquire":
        ok, message = acquire(path, args.label, args.stale_minutes)
    elif args.command == "tick":
        ok, message = tick(path)
    elif args.command == "release":
        ok, message = release(path)
    else:
        ok, message = status(path, args.stale_minutes)

    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
