"""One merchant, many labels: fold what the bank appends to a shop's name.

« CB CARREFOUR 12/09 » and « CB CARREFOUR 03/09 » are one merchant. Dates,
card numbers, amounts and reference numbers are noise; the prefixes banks
put in front of a payment are too. The same folding serves the spending
screen and the categories learned from past decisions.
"""

from __future__ import annotations

import re

_NOISE = re.compile(r"[\d/*.,:-]+")
_PREFIXES = ("cb ", "carte ", "paiement cb ", "prlv sepa ", "prlv ", "vir sepa ", "vir ")


def fold(label: str | None) -> str:
    """The merchant behind a bank label, lowercased, noise stripped."""
    name = _NOISE.sub(" ", (label or "").lower())
    for prefix in _PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix) :]
    name = " ".join(name.split()).strip()
    return name or "sans libellé"
