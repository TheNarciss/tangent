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
# Single source of truth for model + token budget. Changing these here
# propagates to every caller (review_generator, future agents, etc.).

MODEL: str = "claude-sonnet-4-6"
"""The Claude model used for portfolio reviews (cf ADR-015)."""

MAX_TOKENS: int = 4096
"""Hard cap on output tokens per LLM call. A full review fits in ~2-3k tokens;
4096 leaves headroom for verbose generations without runaway cost."""

WEB_SEARCH_MAX_USES: int = 5
"""Maximum number of `web_search_20250305` tool invocations per review.
Caps cost: 5 × $0.01 = $0.05 worst case for the search component."""


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
        logger.info("Initializing AsyncAnthropic client (model=%s)", MODEL)
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
