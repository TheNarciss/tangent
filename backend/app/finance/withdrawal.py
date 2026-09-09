"""The app's sustainable withdrawal rate, in one place.

Bengen's 4 % comes from the United States 1926-1992; on French history it
fails in more than half of the cohorts (Pfau 2010), so the rate lives in
`config/verdicts.yaml` and every screen reads it from there. What used to be
a whole planning module — a « capital for an income » route nothing called,
built on the American rule — went with the rest of §8.3.
"""

from __future__ import annotations

from . import verdicts as _verdicts


def default_withdrawal_rate() -> float:
    """The sustainable initial withdrawal rate, versioned in verdicts.yaml."""
    return _verdicts.config().retirement.withdrawal_rate
