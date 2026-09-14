"""Category of a transaction from what the bank already says about it.

Card networks attach a merchant category code (MCC, ISO 18245) to every
payment; banks attach an ISO 20022 operation code to every entry. Both are
normalised, come with the transaction, and cost nothing: a rule table turns
them into our categories at sync time. What no rule covers stays empty and
goes to the nightly LLM, as before.

The table is `config/transaction_categories.yaml`; nothing here is a value.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from ..errors import ConfigurationError
from .gap_filler.fields.transaction_category import CATEGORIES

_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "transaction_categories.yaml"

SOURCE = "bank_code"  # what category_source says when a rule decided


class MccRule(BaseModel):
    mcc: int | None = Field(default=None, ge=0, le=9999)
    from_: int | None = Field(default=None, alias="from", ge=0, le=9999)
    to: int | None = Field(default=None, ge=0, le=9999)
    category: str

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _one_shape(self) -> MccRule:
        single = self.mcc is not None
        span = self.from_ is not None and self.to is not None
        if single == span:
            raise ValueError("une règle MCC porte soit `mcc`, soit `from` et `to`")
        if span and self.from_ > self.to:  # type: ignore[operator]
            raise ValueError("`from` doit précéder `to`")
        if self.category not in CATEGORIES:
            raise ValueError(f"catégorie inconnue: {self.category}")
        return self

    def covers(self, code: int) -> bool:
        if self.mcc is not None:
            return code == self.mcc
        return self.from_ <= code <= self.to  # type: ignore[operator]


class CodeRule(BaseModel):
    code: str  # DOMAIN/FAMILY or DOMAIN/FAMILY/SUBFAMILY
    category: str

    @model_validator(mode="after")
    def _known(self) -> CodeRule:
        if self.category not in CATEGORIES:
            raise ValueError(f"catégorie inconnue: {self.category}")
        return self


class Rules(BaseModel):
    mcc: list[MccRule] = Field(default_factory=list)
    bank_transaction_code: list[CodeRule] = Field(default_factory=list)


@lru_cache(maxsize=1)
def rules() -> Rules:
    if not _PATH.exists():
        raise ConfigurationError("transaction_categories.yaml introuvable.")
    try:
        return Rules.model_validate(yaml.safe_load(_PATH.read_text()) or {})
    except (yaml.YAMLError, ValueError) as exc:
        raise ConfigurationError(f"transaction_categories.yaml malformé: {exc}") from exc


def from_mcc(mcc: str | int | None) -> str | None:
    """The category the merchant code decides, first matching rule wins."""
    if mcc in (None, ""):
        return None
    try:
        code = int(str(mcc).strip())
    except ValueError:
        return None
    for rule in rules().mcc:
        if rule.covers(code):
            return rule.category
    return None


def from_bank_code(code: dict | str | None) -> str | None:
    """The category the ISO operation code decides, most specific rule first."""
    if not code:
        return None
    if isinstance(code, dict):
        parts = [str(code.get(k) or "").strip().upper() for k in ("domain", "family", "sub_family")]
        # Enable Banking's shape: {code, sub_code} = family, sub-family, under PMNT.
        if not any(parts) and code.get("code"):
            parts = [
                "PMNT",
                str(code["code"]).strip().upper(),
                str(code.get("sub_code") or "").strip().upper(),
            ]
        path = "/".join(p for p in parts if p)
    else:
        path = str(code).strip().upper()
    known = {r.code.upper(): r.category for r in rules().bank_transaction_code}
    while path:
        if path in known:
            return known[path]
        path = path.rpartition("/")[0]
    return None


def decide(*, mcc: str | int | None = None, bank_code: dict | str | None = None) -> str | None:
    """Merchant code first (it names the shop), then the operation code."""
    return from_mcc(mcc) or from_bank_code(bank_code)
