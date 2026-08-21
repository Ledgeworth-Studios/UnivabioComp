"""Tests for the one-run-at-a-time lock.

The property that matters is not "a file gets written". It is: **when several
runs ask for the lock at the same instant, exactly one is told to proceed.**
`test_only_one_of_many_simultaneous_runs_wins` is the test that checks that, and
it does it the honest way — by starting real, competing processes rather than by
calling the function twice in a row.

The rest of the tests pin the exit codes, because the exit code is the whole
interface: `CLAUDE.md` tells a run to stand down when `acquire` exits non-zero.
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import runlock  # noqa: E402

RUNLOCK_SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "runlock.py"


@pytest.fixture
def lock_file(tmp_path: Path) -> Path:
    return tmp_path / ".runlock"


def run_cli(lock_file: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the script the way a build run does: as a command, checking the exit code."""
    return subprocess.run(
        [sys.executable, str(RUNLOCK_SCRIPT), *args],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "WHYNOT_RUNLOCK": str(lock_file)},
    )


def backdate(lock_file: Path, minutes: float) -> None:
    """Pretend the holder last checked in `minutes` ago."""
    record = json.loads(lock_file.read_text())
    record["last_seen"] = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
    lock_file.write_text(json.dumps(record))


# --------------------------------------------------------------------------
# The property the lock exists for
# --------------------------------------------------------------------------


def test_only_one_of_many_simultaneous_runs_wins(lock_file: Path) -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: run_cli(lock_file, "acquire"), range(8)))

    winners = [r for r in results if r.returncode == 0]
    losers = [r for r in results if r.returncode == 1]
    assert len(winners) == 1, [r.stdout for r in results]
    assert len(losers) == 7
    assert all("STAND DOWN" in r.stdout for r in losers)

    # The lock names the run that won, not the last one to try.
    holder = json.loads(lock_file.read_text())["run_id"]
    assert holder in winners[0].stdout


def test_a_second_run_is_refused_while_the_first_is_alive(lock_file: Path) -> None:
    first = run_cli(lock_file, "acquire")
    assert first.returncode == 0

    second = run_cli(lock_file, "acquire")
    assert second.returncode == 1
    assert "STAND DOWN" in second.stdout

    # Being refused must not disturb the holder's record.
    assert json.loads(lock_file.read_text())["run_id"] in first.stdout


# --------------------------------------------------------------------------
# Staleness — a run that died must not block the project for ever
# --------------------------------------------------------------------------


def test_a_stale_lock_is_taken_over_and_the_takeover_is_announced(lock_file: Path) -> None:
    run_cli(lock_file, "acquire")
    backdate(lock_file, minutes=runlock.STALE_AFTER_MINUTES + 30)

    second = run_cli(lock_file, "acquire")
    assert second.returncode == 0
    assert "stale" in second.stdout
    assert "inspect the working tree" in second.stdout


def test_a_lock_just_under_the_limit_is_still_respected(lock_file: Path) -> None:
    run_cli(lock_file, "acquire")
    backdate(lock_file, minutes=runlock.STALE_AFTER_MINUTES - 5)
    assert run_cli(lock_file, "acquire").returncode == 1


def test_ticking_keeps_a_long_running_run_from_being_declared_dead(lock_file: Path) -> None:
    run_cli(lock_file, "acquire")
    backdate(lock_file, minutes=runlock.STALE_AFTER_MINUTES + 30)

    assert run_cli(lock_file, "tick").returncode == 0
    assert run_cli(lock_file, "acquire").returncode == 1


def test_an_unreadable_lock_file_ages_out_instead_of_blocking_for_ever(lock_file: Path) -> None:
    lock_file.write_text("this is not json")

    # While it is fresh we refuse, because we cannot prove nobody is there.
    assert run_cli(lock_file, "acquire").returncode == 1

    # With a long-enough age it is treated as abandoned. `--stale-minutes 0`
    # stands in for "the file's timestamp is older than the limit".
    assert run_cli(lock_file, "acquire", "--stale-minutes", "0").returncode == 0


# --------------------------------------------------------------------------
# The ordinary lifecycle
# --------------------------------------------------------------------------


def test_release_frees_the_lock_for_the_next_run(lock_file: Path) -> None:
    run_cli(lock_file, "acquire")
    assert run_cli(lock_file, "release").returncode == 0
    assert not lock_file.exists()
    assert run_cli(lock_file, "acquire").returncode == 0


def test_releasing_when_nothing_is_held_is_not_an_error(lock_file: Path) -> None:
    result = run_cli(lock_file, "release")
    assert result.returncode == 0
    assert "no lock was held" in result.stdout


def test_ticking_without_a_lock_fails_loudly(lock_file: Path) -> None:
    result = run_cli(lock_file, "tick")
    assert result.returncode == 1
    assert "just lock" in result.stdout


def test_status_reports_nobody_live_and_stale(lock_file: Path) -> None:
    assert "nobody holds the lock" in run_cli(lock_file, "status").stdout

    run_cli(lock_file, "acquire", "--label", "nightly build")
    assert "live:" in run_cli(lock_file, "status").stdout

    backdate(lock_file, minutes=runlock.STALE_AFTER_MINUTES + 1)
    assert "STALE:" in run_cli(lock_file, "status").stdout


def test_the_label_is_kept_so_status_can_say_what_the_run_was_doing(lock_file: Path) -> None:
    run_cli(lock_file, "acquire", "--label", "scheduled univabio-build")
    assert json.loads(lock_file.read_text())["label"] == "scheduled univabio-build"


# --------------------------------------------------------------------------
# The staleness window itself
# --------------------------------------------------------------------------


def test_the_stale_window_sits_between_the_two_real_durations() -> None:
    """A guard on the one number in this module that is a judgement call.

    It must be longer than a run's gap between commits (or a live run is judged
    dead) and shorter than the five hours between scheduled runs (or a crashed
    run's lock survives into the next run's turn).
    """
    assert 60 <= runlock.STALE_AFTER_MINUTES < 5 * 60
