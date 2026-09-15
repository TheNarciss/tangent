"""Lazy singleton wrapper around `anthropic.AsyncAnthropic`.

Why a wrapper and not the SDK direct?

- **Lazy init**: avoids crashing app boot if `ANTHROPIC_API_KEY` is missing in
  dev. The error surfaces only when an LLM feature is actually used.
- **Single source of truth for env loading**: matches the existing pattern
  (`os.getenv` direct in the module that needs it, cf `auth/backend.py`,
  `auth/oauth_router.py`). No pydantic-settings refactor.
- **Single hook** for adding retry, telemetry, or per-request data-retention
  flags in later PRs (ADR-015 §Privacy).

See ADR-015 for context.
"""

from __future__ import annotations

import logging
import os

from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# ── Public constants ────────────────────────────────────────────────────────
# Single source of truth for models, thinking and token budgets: one model per
# job, because the jobs are not alike. Changing these here propagates to
# every caller (review_generator, batch_submitter, gap-filler).

BRIEFING_MODEL: str = "claude-opus-5"
"""The morning briefing: the one text that judges and sorts (ADR-015, amended
2026-09-15). One a day per administrator, so the strongest model with real
reasoning costs a few cents."""

BRIEFING_THINKING: dict[str, str] = {"type": "adaptive"}
BRIEFING_EFFORT: str = "high"

BRIEFING_MAX_TOKENS: int = 16_000
"""Output cap per briefing call, thinking tokens included: a briefing is
~2-3k tokens of text, the reasoning before it a few thousand more."""

CATEGORY_MODEL: str = "claude-haiku-4-5"
"""Transaction categories: a closed list of 22, twenty-five rows per call. A
classification, no reasoning needed, and the volume is here."""

SOURCING_MODEL: str = "claude-sonnet-5"
"""Fields read from a document on the web (TER, ISIN): a web search, then a
figure copied from a KID or a factsheet."""

SOURCING_EFFORT: str = "medium"

WEB_SEARCH_MAX_USES: int = 5
"""Maximum number of web_search invocations per briefing.
Caps cost: 5 × $0.01 = $0.05 worst case for the search component."""


def web_search_tool(max_uses: int = WEB_SEARCH_MAX_USES) -> dict[str, object]:
    """Anthropic's server-side web search, the variant current models take."""
    return {"type": "web_search_20260209", "name": "web_search", "max_uses": max_uses}


# ── Singleton instance ──────────────────────────────────────────────────────

_client: AsyncAnthropic | None = None


def get_client() -> AsyncAnthropic:
    """Return a process-wide singleton `AsyncAnthropic`.

    Reads `ANTHROPIC_API_KEY` from the environment on first call. Subsequent
    calls return the cached instance without re-reading env vars (intentional:
    avoids surprises if the env mutates at runtime).

    Raises:
        RuntimeError: if `ANTHROPIC_API_KEY` is unset or empty. Callers should
            catch this and return HTTP 503 to the user with a clear message
            ("LLM features unavailable — contact support").
    """
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY env var is required for LLM features. "
                "Set it in backend/.env (or export it) before starting the server. "
                "See ADR-015 for context."
            )
        logger.info("Initializing AsyncAnthropic client (briefing model=%s)", BRIEFING_MODEL)
        _client = AsyncAnthropic(api_key=api_key)
    return _client


def reset_client_for_testing() -> None:
    """Reset the singleton. **Tests only** — see `tests/unit/test_llm_mock.py`.

    Why: `get_client()` caches the SDK instance after the first call. Tests
    that monkeypatch the API key after import would otherwise hit the cached
    instance and bypass the env change.
    """
    global _client
    _client = None
