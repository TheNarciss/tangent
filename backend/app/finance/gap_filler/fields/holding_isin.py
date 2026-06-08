"""GappableField: resolve ISIN from a ticker + label.

ISINs are deterministic public identifiers (12 chars, [A-Z]{2}[A-Z0-9]{10}).
The LLM should know the ISIN for most ETFs given the ticker + label, or
look it up via web_search.
"""

from __future__ import annotations

import re
from typing import Any

from ..registry import GappableField, register_field

ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


PROMPT_TEMPLATE = """\
On a une position dans un compte titres avec ISIN manquant:

- Ticker: {ticker}
- Label: {label}
- Currency: {currency}

Trouve l'ISIN officiel de ce produit (12 caractères, format
[A-Z]{{2}}[A-Z0-9]{{9}}[0-9]). Tu peux utiliser web_search.

Si tu n'es pas SÛR à 100%, appelle resolve_isin avec isin=null.
"""


def build_prompt_isin(row: Any) -> str:
    return PROMPT_TEMPLATE.format(
        ticker=row.ticker,
        label=row.label,
        currency=row.currency,
    )


RESPONSE_SCHEMA_ISIN: dict[str, Any] = {
    "type": "object",
    "description": "Resolve the ISIN of a security from ticker+label.",
    "properties": {
        "isin": {
            "type": ["string", "null"],
            "pattern": "^[A-Z]{2}[A-Z0-9]{9}[0-9]$",
            "description": "12-char ISIN, or null if unsure.",
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": ["isin", "confidence"],
}


def validate_isin(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and bool(ISIN_PATTERN.match(value))


FIELD_ISIN = register_field(
    GappableField(
        name="isin",
        table="account_holdings",
        value_column="isin",
        source_column="isin_source",
        resolved_at_column="isin_resolved_at",
        build_prompt=build_prompt_isin,
        response_schema=RESPONSE_SCHEMA_ISIN,
        tool_name="resolve_isin",
        validate_value=validate_isin,
    )
)
