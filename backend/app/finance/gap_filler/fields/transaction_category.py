"""GappableField: category of a bank transaction.

The LLM picks ONE category from a fixed taxonomy. Free-form categorization
is rejected (the schema enum bounds the choice). The fixed list is borrowed
from Powens' default category nomenclature and condensed to the most
useful buckets for a French personal-finance dashboard.
"""

from __future__ import annotations

from typing import Any

from ..registry import GappableField, register_field

# Fixed category taxonomy. Adding/removing items here is fine but be aware
# that historical "llm"-categorized rows keep their old labels until the
# next gap-fill pass.
CATEGORIES: list[str] = [
    "alimentation",
    "restaurant",
    "transport",
    "carburant",
    "loyer",
    "charges_logement",
    "telecom_internet",
    "assurance",
    "sante",
    "loisirs",
    "abonnements",
    "shopping",
    "voyages",
    "education",
    "impots_taxes",
    "salaire",
    "remboursement",
    "virement_interne",
    "epargne_investissement",
    "frais_bancaires",
    "cadeaux_dons",
    "autre",
]


PROMPT_TEMPLATE = """\
Catégorise cette transaction bancaire française:

- Description: {description}
- Montant: {amount:.2f} {currency}
- Date: {transaction_date}

Choisis UNE catégorie parmi:
{categories}

Si la description est trop vague et que tu ne peux pas raisonner avec
certitude, appelle resolve_category avec category='autre'.

Conseils:
- "Carte X CB 1234" + montant positif → likely 'remboursement' ou 'salaire' selon montant
- Marques de chaînes (Carrefour, Monoprix, etc.) → 'alimentation'
- Restaurants, McDonald's, Uber Eats → 'restaurant'
- SNCF, RATP, BlaBlaCar → 'transport'
- Netflix, Spotify, Apple → 'abonnements'
"""


def build_prompt_category(row: Any) -> str:
    cats = "\n".join(f"  - {c}" for c in CATEGORIES)
    return PROMPT_TEMPLATE.format(
        description=row.description,
        amount=row.amount,
        currency=row.currency,
        transaction_date=row.transaction_date,
        categories=cats,
    )


RESPONSE_SCHEMA_CATEGORY: dict[str, Any] = {
    "type": "object",
    "description": "Pick the single best-fitting category from the closed taxonomy.",
    "properties": {
        "category": {
            "type": "string",
            "enum": CATEGORIES,
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": ["category", "confidence"],
}


def validate_category(value: Any) -> bool:
    return isinstance(value, str) and value in CATEGORIES


FIELD_CATEGORY = register_field(
    GappableField(
        name="category",
        table="bank_transactions",
        value_column="category",
        source_column="category_source",
        resolved_at_column="category_resolved_at",
        build_prompt=build_prompt_category,
        response_schema=RESPONSE_SCHEMA_CATEGORY,
        tool_name="resolve_category",
        validate_value=validate_category,
    )
)
