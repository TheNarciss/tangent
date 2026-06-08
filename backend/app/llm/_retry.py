"""Retry decorator for transient Anthropic overload errors (529/503).

Strictly bounded:
- Only retries 529 (overloaded_error) and 503 (service_unavailable). Excludes:
  - 429 (rate limit) — needs Retry-After header respect, different strategy
  - 4xx (deterministic) — retry would just re-fail
  - 500 (generic internal) — may be deterministic, risk of infinite loop
- Max 3 attempts total (initial + 2 retries). Wait exponential 4s, 8s, 16s
  (capped at 60s). Total worst case ~28s.
- ONLY safe on calls that fail BEFORE token consumption — e.g.
  `batches.create()` which is rejected at the gate when overloaded.
- NOT applied to `messages.stream()` which may have already streamed (and
  thus billed) some tokens when the error occurs. The SSE caller catches
  APIStatusError and surfaces it to the user instead.
"""

from __future__ import annotations

import logging

from anthropic import APIStatusError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def is_anthropic_overloaded(exc: BaseException) -> bool:
    """True iff exc is an Anthropic APIStatusError with status 503 or 529."""
    return isinstance(exc, APIStatusError) and exc.status_code in (503, 529)


retry_on_overload = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception(is_anthropic_overloaded),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
"""Retry on Anthropic 529/503. See module docstring for safety bounds."""
