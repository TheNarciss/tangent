"""LLM-powered portfolio reviews.

See ADR-015 (docs/adr/015-llm-portfolio-reviews.md) for the full rationale.

Public surface for the rest of the app:

- `anthropic_client.get_client()` — singleton `AsyncAnthropic` instance
- `anthropic_client.BRIEFING_MODEL` — Opus 5 with adaptive thinking, for the briefing
- `anthropic_client.CATEGORY_MODEL` — Haiku 4.5, for the transaction categories
- `anthropic_client.SOURCING_MODEL` — Sonnet 5, for what is read on the web (TER, ISIN)
- `cost_tracker.DAILY_CAP_USD` — the daily kill-switch, all users together

Future PRs in this series will add:

- `cost_tracker.py` (PR2) — daily kill-switch at €5/day
- `prompt_builder.py` (PR3) — Wealth + Profile + analytics → structured prompt
- `review_generator.py` (PR4) — orchestration with `web_search` tool + SSE
"""
