"""LLM-powered portfolio reviews.

See ADR-015 (docs/adr/015-llm-portfolio-reviews.md) for the full rationale.

Public surface for the rest of the app:

- `anthropic_client.get_client()` — singleton `AsyncAnthropic` instance
- `anthropic_client.MODEL` — currently `"claude-sonnet-4-6"`
- `anthropic_client.MAX_TOKENS` — output cap per review (4096)

Future PRs in this series will add:

- `cost_tracker.py` (PR2) — daily kill-switch at €5/day
- `prompt_builder.py` (PR3) — Wealth + Profile + analytics → structured prompt
- `review_generator.py` (PR4) — orchestration with `web_search` tool + SSE
"""
