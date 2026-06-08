"""GappableField: TER (Total Expense Ratio) of an ETF holding.

Resolves the annual TER as a ratio (0.0025 = 0.25%/an). The LLM is asked to
search the KID/factsheet of the issuer (Amundi, iShares, Lyxor, BNP, etc.).

The schema strictly bounds the response to [0, 0.02] (anything above 2%/an
isn't a classic ETF and should be a human-checked case).
"""

from __future__ import annotations

from typing import Any

from ..registry import GappableField, register_field

PROMPT_TEMPLATE = """\
On a une position ETF dans un compte titres français avec ces infos:

- Ticker: {ticker}
- ISIN: {isin}
- Label: {label}
- Currency: {currency}

Trouve le TER (Total Expense Ratio) ANNUEL de ce produit. Utilise
**impérativement** web_search pour vérifier la valeur sur le KID
(Document d'Information Clé) ou la factsheet officielle de l'émetteur
(Amundi, iShares, Lyxor, BNP, Xtrackers, Invesco, etc.).

Ne te fie pas à ta mémoire — les TER changent dans le temps et la
source officielle prime. Cite l'URL dans source_url.

IMPORTANT — Format de la réponse:
- Le TER doit être retourné comme un RATIO, pas un pourcentage:
    * 0.25% → 0.0025
    * 0.50% → 0.005
    * 1.20% → 0.012
- Si tu trouves une valeur fiable: appelle resolve_ter avec ter=<valeur>
  et confidence='high' ou 'medium' selon la qualité de la source.
- Si tu n'as PAS de donnée fiable: appelle resolve_ter avec ter=null
  et confidence='low'. Mieux vaut admettre l'inconnu qu'inventer.
"""


def build_prompt_ter(row: Any) -> str:
    return PROMPT_TEMPLATE.format(
        ticker=row.ticker,
        isin=row.isin or "(non renseigné)",
        label=row.label,
        currency=row.currency,
    )


RESPONSE_SCHEMA_TER: dict[str, Any] = {
    "type": "object",
    "description": "Resolve the annual TER (Total Expense Ratio) of an ETF.",
    "properties": {
        "ter": {
            "type": ["number", "null"],
            "description": (
                "TER as a ratio (0.0025 = 0.25%/an). Use null if unknown. "
                "Must be in [0, 0.02] when non-null."
            ),
            "minimum": 0,
            "maximum": 0.02,
        },
        "source_url": {
            "type": ["string", "null"],
            "description": "URL of the KID or factsheet used.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": ["ter", "confidence"],
}


def validate_ter(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, (int, float)):
        return False
    return 0 <= float(value) <= 0.02


def coerce_ter(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


FIELD_TER = register_field(
    GappableField(
        name="ter",
        table="account_holdings",
        value_column="ter",
        source_column="ter_source",
        resolved_at_column="ter_resolved_at",
        build_prompt=build_prompt_ter,
        response_schema=RESPONSE_SCHEMA_TER,
        tool_name="resolve_ter",
        validate_value=validate_ter,
        coerce_value=coerce_ter,
        requires_web_search=True,
    )
)
