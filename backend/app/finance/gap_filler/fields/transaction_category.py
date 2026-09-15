"""GappableField: category of a bank transaction.

The LLM picks ONE category from a fixed taxonomy. Free-form categorization
is rejected (the schema enum bounds the choice). The fixed list is borrowed
from Powens' default category nomenclature and condensed to the most
useful buckets for a French personal-finance dashboard.
"""

from __future__ import annotations

from collections.abc import Sequence
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


BATCH_PROMPT_TEMPLATE = """\
Catégorise chacune de ces transactions bancaires françaises. Chaque ligne \
porte un identifiant, une description, un montant et une date :
{lines}

Choisis UNE catégorie par transaction parmi :
{categories}

Réponds en appelant resolve_category une seule fois, avec un élément par \
transaction, en recopiant son identifiant tel quel. Une description trop \
vague pour raisonner avec certitude reçoit category='autre'.

Conseils :
- Montant positif sur "Carte X CB 1234" → 'remboursement' ou 'salaire' selon le montant
- Chaînes de magasins (Carrefour, Monoprix…) → 'alimentation'
- Restaurants, McDonald's, Uber Eats → 'restaurant'
- SNCF, RATP, BlaBlaCar → 'transport'
- Netflix, Spotify, Apple → 'abonnements'
"""

# Rows per request. Twenty-five short lines fit comfortably in one answer and
# divide the cost of the instructions and the schema by as much.
BATCH_SIZE = 25


def build_batch_prompt_category(rows: Sequence[Any]) -> str:
    lines = "\n".join(
        f"- id={row.id} | {row.description} | {row.amount:.2f} {row.currency} | {row.transaction_date}"
        for row in rows
    )
    cats = "\n".join(f"  - {c}" for c in CATEGORIES)
    return BATCH_PROMPT_TEMPLATE.format(lines=lines, categories=cats)


RESPONSE_SCHEMA_CATEGORY: dict[str, Any] = {
    "type": "object",
    "description": "One category per transaction, from the closed taxonomy, keyed by the id given.",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["id", "category"],
            },
        }
    },
    "required": ["items"],
}


RESPONSE_SCHEMA_CATEGORY_SINGLE: dict[str, Any] = {
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
        batch_size=BATCH_SIZE,
        build_batch_prompt=build_batch_prompt_category,
    )
)
