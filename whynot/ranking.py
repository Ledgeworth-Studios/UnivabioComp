"""The order trials are shown in.

Step 6 of the pipeline in `docs/PLAN.md`, and deliberately one of the
deterministic ones: "sorting, filtering, and arithmetic are never delegated to a
model." Given the same trials and the same profile this produces the same order
every time, and anyone can check why any trial sits where it does.

The order is:

1. **Trials with no structured conflict first.** A conflict here means an age,
   sex or healthy-volunteer bound that the person's own stated details fall
   outside of — never an interpretation of the free-text criteria.
2. **Then nearest first.** Distance to the closest site, computed from the
   person's coordinates.
3. **Then phase**, ascending. See the note below: this is a tie-break, not a
   recommendation.
4. **Then NCT id**, so the order is total and two identical calls cannot differ.

## Trials with conflicts are kept, not hidden

Sorting them to the bottom is the whole extent of it. Dropping them would be the
one thing this tool exists not to do: it is called "Why Not This Trial" because
explaining what would stop you is the product. A person who searches and sees
four trials has no idea whether the fifth was excluded for a reason they could
argue with. A person who sees five, one of them marked "this trial enrols ages 10
to 17; you told us you are 41", knows exactly where they stand.

## Missing data sorts last, never first

A trial with no located site has an unknown distance, not a distance of zero. If
unknown sorted first it would outrank a clinic nine miles away, which is both
wrong and the kind of wrong that looks like a feature. Unknown phase is treated
the same way.

## Phase is a tie-break and not advice

`docs/decisions/0002` records this. Ordering trials by phase in either direction
could be read as a claim about which trials are better to join, and this tool
does not make claims like that — it reads a registry. Phase is here only because
two trials with the same conflict status at the same distance need *some*
reproducible order, and the registry's own phase enumeration is a more meaningful
one than the alphabet. Nothing in the interface presents it as a ranking of
quality.
"""

from __future__ import annotations

import math

from whynot.hardfilter import hard_filter
from whynot.profile import PatientProfile
from whynot.registry import Study

#: The registry's own phase vocabulary, in the registry's own order.
PHASE_ORDER = {
    "EARLY_PHASE1": 0,
    "PHASE1": 1,
    "PHASE2": 2,
    "PHASE3": 3,
    "PHASE4": 4,
}

#: Where anything we do not recognise goes: last. `NA` — which the registry uses
#: for studies that are not drug trials and have no phase — lands here too, and
#: that is correct: it is not a phase, so it cannot take a place among them.
UNKNOWN_PHASE = len(PHASE_ORDER)


def phase_rank(phases: tuple[str, ...]) -> int:
    """Where a study's phase puts it in the order.

    A study may list more than one phase (`["PHASE1", "PHASE2"]` is common). The
    earliest is used, so a phase 1/2 trial sorts with the phase 1 trials rather
    than drifting later than a study that is only phase 1.
    """
    known = [PHASE_ORDER[phase] for phase in phases if phase in PHASE_ORDER]
    return min(known) if known else UNKNOWN_PHASE


def distance_to_nearest_site(
    study: Study, latitude: float | None, longitude: float | None
) -> float:
    """Miles to this study's closest site, or infinity if we cannot say.

    Infinity rather than None so it can be compared with real distances without
    any special case, and so unknown always sorts last.
    """
    if latitude is None or longitude is None:
        return math.inf
    nearest = study.nearest_location(latitude, longitude)
    return math.inf if nearest is None else nearest[1]


def sort_key(
    study: Study,
    profile: PatientProfile,
    latitude: float | None,
    longitude: float | None,
) -> tuple[int, float, int, str]:
    """The four things that decide a trial's place, in order of importance."""
    conflicted = 1 if hard_filter(study, profile).is_ruled_out else 0
    return (
        conflicted,
        distance_to_nearest_site(study, latitude, longitude),
        phase_rank(study.phases),
        study.nct_id,
    )


def rank_studies(
    studies: tuple[Study, ...],
    profile: PatientProfile,
    latitude: float | None = None,
    longitude: float | None = None,
) -> tuple[Study, ...]:
    """Order trials for one person. Returns every study handed in — none dropped."""
    return tuple(sorted(studies, key=lambda s: sort_key(s, profile, latitude, longitude)))
