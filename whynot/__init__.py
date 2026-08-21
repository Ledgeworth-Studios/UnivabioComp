"""Why Not This Trial — clinical-trial eligibility explained in three values.

The package is deliberately small and flat. Each module does one thing:

    registry.py    talks to the ClinicalTrials.gov v2 API (deterministic)
    hardfilter.py  age / sex / healthy-volunteer decisions (deterministic)
    criteria.py    splits the free-text eligibility blob into criteria
    judge.py       the only place a model is allowed to reason
"""

__version__ = "0.1.0"
