"""Universal Gap-Filler (ADR-021).

Importing this package auto-registers the gappable fields (ter, category, isin).

Public API:
    from app.finance.gap_filler import (
        Gap, GappableField,
        get_field, get_all_fields, register_field,
        encode_custom_id, decode_custom_id,
    )

The Anthropic-dependent functions (batch building, response parsing) live
in `gap_filler.engine` and must be imported explicitly:

    from app.finance.gap_filler.engine import (
        collect_gaps, build_gap_fill_requests, apply_gap_fill_response,
    )

Keeping `engine` out of the package top-level lets the rest of the app
import the registry without pulling in the anthropic SDK.
"""

from . import fields
from .registry import (
    Gap,
    GappableField,
    decode_custom_id,
    encode_custom_id,
    get_all_fields,
    get_field,
    register_field,
)

__all__ = [
    "Gap",
    "GappableField",
    "decode_custom_id",
    "encode_custom_id",
    "get_all_fields",
    "get_field",
    "register_field",
]
