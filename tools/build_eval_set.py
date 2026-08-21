"""Generate the eval-set fixture from recorded registry data.

Run when the set changes:

    uv run python tools/build_eval_set.py

The criterion text is pulled straight out of the recorded fixtures rather than
retyped, so it is verbatim by construction — `whynot/evalset.py` refuses any pair
whose text does not appear in the recorded corpus, and a transcription slip would
otherwise fail that check for a reason that has nothing to do with the label.

**What a human needs to do with this file:** every pair carries `expected` (the
proposed answer), `basis` (the reasoning) and `needs_human_review`. The reviewed
ones are labels anybody can check by reading — the profile says nothing about MRI
lesions, so a criterion about MRI lesions is UNKNOWN. The flagged ones take
judgement, and the scoring code will not count them until a person puts their name
in `reviewed_by`. See `docs/decisions/0004`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from whynot.criteria import split_criteria  # noqa: E402
from whynot.registry import parse_study  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_FIXTURES = ROOT / "tests" / "fixtures" / "registry"
OUT = ROOT / "tests" / "fixtures" / "eval" / "criteria_v1.json"

# The people. Every field is optional in this product, and these are deliberately
# thin, because a thin profile is what the tool actually receives.
PROFILES = {
    "adult-with-ms": {
        "age_years": 41,
        "sex": "female",
        "conditions": ["multiple sclerosis"],
    },
    "child-with-rrms": {
        "age_years": 12,
        "conditions": ["relapsing-remitting multiple sclerosis"],
    },
    "said-nothing-about-health": {
        "age_years": 34,
        "sex": "male",
        "conditions": [],
    },
    # Added with D-6, which gave the profile three fields a person would actually
    # say out loud. Before it, no pair in this set could resolve to anything but
    # UNKNOWN on a criterion about treatment history — there was nowhere to put
    # the answer.
    "adult-on-ocrelizumab": {
        "age_years": 38,
        "sex": "female",
        "conditions": ["relapsing-remitting multiple sclerosis"],
        "diagnosed_year": 2019,
        "current_treatments": ["ocrelizumab"],
        "past_treatments": ["interferon beta-1a"],
    },
    "adult-previously-on-briumvi": {
        "age_years": 45,
        "sex": "male",
        "conditions": ["multiple sclerosis"],
        "diagnosed_year": 2015,
        "current_treatments": [],
        "past_treatments": ["BRIUMVI"],
    },
}

SILENT = "The profile says nothing about this, so nobody can answer it from what we were told."

# (nct_id, criterion index, profile, expected, basis, needs_human_review)
PAIRS: list[tuple[str, int, str, str, str, bool]] = [
    # --- age, which is arithmetic ---
    (
        "NCT06441617",
        2,
        "adult-with-ms",
        "MET",
        "The profile states 41, and 41 is at least 22.",
        False,
    ),
    (
        "NCT06441617",
        2,
        "child-with-rrms",
        "NOT_MET",
        "The profile states 12, which is below 22.",
        False,
    ),
    (
        "NCT06441617",
        2,
        "said-nothing-about-health",
        "MET",
        "The profile states 34, which is at least 22.",
        False,
    ),
    # --- the profile is simply silent ---
    (
        "NCT06441617",
        1,
        "adult-with-ms",
        "UNKNOWN",
        "The profile records no country of residence.",
        False,
    ),
    (
        "NCT06441617",
        5,
        "adult-with-ms",
        "UNKNOWN",
        "The profile records nothing about languages spoken.",
        False,
    ),
    (
        "NCT06441617",
        4,
        "adult-with-ms",
        "UNKNOWN",
        "The profile holds no Fatigue Severity Scale score, and no way to derive one.",
        False,
    ),
    (
        "NCT06441617",
        6,
        "adult-with-ms",
        "UNKNOWN",
        "Willingness is not something the profile records.",
        False,
    ),
    ("NCT06441617", 7, "adult-with-ms", "UNKNOWN", SILENT, False),
    (
        "NCT06441617",
        8,
        "adult-with-ms",
        "UNKNOWN",
        "The profile holds no relapse or steroid history.",
        False,
    ),
    (
        "NCT06441617",
        9,
        "adult-with-ms",
        "UNKNOWN",
        "The profile holds no treatment history.",
        False,
    ),
    (
        "NCT06441617",
        10,
        "adult-with-ms",
        "UNKNOWN",
        "Whether the person is able and willing to consent is not recorded.",
        False,
    ),
    (
        "NCT06441617",
        12,
        "adult-with-ms",
        "UNKNOWN",
        "The profile records no other trial participation.",
        False,
    ),
    (
        "NCT06433752",
        1,
        "adult-with-ms",
        "UNKNOWN",
        "The profile records no prior infusions of anything.",
        False,
    ),
    (
        "NCT06433752",
        2,
        "adult-with-ms",
        "UNKNOWN",
        "The profile records no vaccination history.",
        False,
    ),
    ("NCT06433752", 3, "adult-with-ms", "UNKNOWN", "The profile records no infections.", False),
    (
        "NCT06433752",
        4,
        "adult-with-ms",
        "UNKNOWN",
        "The profile records no other trial participation.",
        False,
    ),
    (
        "NCT06408259",
        1,
        "child-with-rrms",
        "UNKNOWN",
        "The profile holds no relapse or MRI history.",
        False,
    ),
    ("NCT06408259", 2, "child-with-rrms", "UNKNOWN", "The profile holds no relapse count.", False),
    ("NCT06408259", 3, "child-with-rrms", "UNKNOWN", "The profile holds no MRI findings.", False),
    ("NCT06408259", 4, "child-with-rrms", "UNKNOWN", "The profile holds no EDSS score.", False),
    (
        "NCT06408259",
        6,
        "child-with-rrms",
        "UNKNOWN",
        "The profile lists one condition and says nothing about immune disease.",
        False,
    ),
    (
        "NCT06408259",
        7,
        "child-with-rrms",
        "UNKNOWN",
        "The profile records no cardiovascular, hepatic or neurological disease.",
        False,
    ),
    (
        "NCT06408259",
        8,
        "child-with-rrms",
        "UNKNOWN",
        "The criterion refers to requirements not published in the record, so nobody outside the "
        "study can answer it.",
        False,
    ),
    # --- a person who told us nothing about their health ---
    (
        "NCT06441617",
        3,
        "said-nothing-about-health",
        "UNKNOWN",
        "The profile lists no conditions at all, so whether they have a confirmed MS diagnosis is "
        "unanswerable.",
        False,
    ),
    ("NCT06441617", 4, "said-nothing-about-health", "UNKNOWN", SILENT, False),
    (
        "NCT06433752",
        0,
        "said-nothing-about-health",
        "UNKNOWN",
        "The profile lists no conditions, so an MS diagnosis cannot be confirmed or ruled out.",
        False,
    ),
    # --- the interpretive ones: a person has to settle these ---
    (
        "NCT06441617",
        0,
        "adult-with-ms",
        "UNKNOWN",
        "Proposed UNKNOWN: the profile records a condition, not whether consent has been given. A "
        "reviewer should confirm that consent is never inferable from a profile.",
        True,
    ),
    (
        "NCT06441617",
        3,
        "adult-with-ms",
        "UNKNOWN",
        "Proposed UNKNOWN: the person says they have MS, but the criterion asks for a diagnosis "
        "confirmed by a neurologist, which their own statement does not establish. A reviewer must "
        "decide whether self-reported diagnosis should ever count as MET.",
        True,
    ),
    (
        "NCT06408259",
        0,
        "child-with-rrms",
        "UNKNOWN",
        "Proposed UNKNOWN: the person states relapsing-remitting MS, but the criterion requires "
        "diagnosis by the 2017 McDonald criteria, which is a clinical determination. A reviewer "
        "must decide.",
        True,
    ),
    (
        "NCT06433752",
        0,
        "adult-with-ms",
        "UNKNOWN",
        "Proposed UNKNOWN: same question as the McDonald-criteria pair — does a self-reported "
        "diagnosis satisfy 'confirmed'? A reviewer should answer it once, consistently, for every "
        "pair like this.",
        True,
    ),
    # --- pairs the D-6 fields make answerable ---
    (
        "NCT06433752",
        1,
        "adult-previously-on-briumvi",
        "NOT_MET",
        "The criterion describes participants who have NOT received a BRIUMVI infusion "
        "before the study. This profile lists BRIUMVI among past treatments, so the "
        "sentence does not describe them. No clinical judgement: the drug is named in "
        "the criterion and named in the profile.",
        False,
    ),
    (
        "NCT06433752",
        1,
        "adult-on-ocrelizumab",
        "MET",
        "The profile lists ocrelizumab and interferon beta-1a and no BRIUMVI, so as far "
        "as we were told they have not had one, and the sentence describes them.",
        False,
    ),
    (
        "NCT06441617",
        9,
        "adult-on-ocrelizumab",
        "UNKNOWN",
        "The profile says they are on a disease-modifying therapy but not when it was "
        "started, and the criterion is about the last four weeks. A treatment list "
        "narrows this and does not settle it.",
        False,
    ),
    (
        "NCT06408259",
        0,
        "adult-on-ocrelizumab",
        "UNKNOWN",
        "Proposed UNKNOWN: the profile states relapsing-remitting MS diagnosed in 2019, "
        "which is closer than a bare condition name, but the criterion requires diagnosis "
        "by the 2017 McDonald criteria and that remains a clinical determination. A "
        "reviewer should settle this the same way as the other self-reported-diagnosis "
        "pairs.",
        True,
    ),
    (
        "NCT06408259",
        5,
        "child-with-rrms",
        "NOT_MET",
        "Proposed NOT_MET: this is an EXCLUSION criterion and MET would mean the person has "
        "progressive MS. They state relapsing-remitting, which is not a progressive form, so the "
        "sentence does not describe them. A reviewer must confirm both the clinical claim and that "
        "the polarity convention in docs/decisions/0004 was applied correctly — this is the pair "
        "most likely to be scored backwards.",
        True,
    ),
]


def criteria_for(nct_id: str) -> list:
    for path in sorted(REGISTRY_FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text())
        for raw in payload.get("studies") or [payload]:
            study = parse_study(raw)
            if study.nct_id == nct_id:
                return list(split_criteria(study.eligibility.criteria_text))
    raise SystemExit(f"{nct_id} is not in the recorded fixtures")


def main() -> None:
    cache: dict[str, list] = {}
    pairs = []
    for index, (nct_id, criterion_index, profile, expected, basis, review) in enumerate(PAIRS, 1):
        criteria = cache.setdefault(nct_id, criteria_for(nct_id))
        criterion = criteria[criterion_index]
        pairs.append(
            {
                "id": f"p{index:02d}",
                "nct_id": nct_id,
                "criterion": criterion.source_text,
                "kind": criterion.kind.value,
                "profile": PROFILES[profile],
                "profile_name": profile,
                "expected": expected,
                "basis": basis,
                "needs_human_review": review,
                "reviewed_by": "",
            }
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "version": "criteria_v1",
                "description": (
                    "Real ClinicalTrials.gov eligibility criteria paired with hand-written "
                    "profiles. MET means the criterion, as written, describes the person — "
                    "including for exclusion criteria, where that is what rules them out "
                    "(docs/decisions/0004). Labels marked needs_human_review are proposals "
                    "and are not scored until a person signs them off."
                ),
                "pairs": pairs,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    counts: dict[str, int] = {}
    for pair in pairs:
        counts[pair["expected"]] = counts.get(pair["expected"], 0) + 1
    flagged = sum(1 for p in pairs if p["needs_human_review"])
    print(f"wrote {len(pairs)} pairs to {OUT}")
    print(f"  verdicts: {counts}")
    print(f"  awaiting human review: {flagged}")


if __name__ == "__main__":
    main()
