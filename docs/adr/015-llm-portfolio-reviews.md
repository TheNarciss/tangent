# ADR-015 — LLM-powered portfolio reviews

Status: Accepted
Date: 2026-06-02
Supersedes: —

## Context

Tangent offers analytical views (Optimizer, Projection, Risk) but no narrative,
personalized summary that ties everything together. Users want a "financial
advisor" view: opportunities, risks, fiscal optimizations, and current market
context — generated on demand, grounded in their actual patrimony.

The existing analytical views are precise but cognitively fragmented: the user
has to mentally stitch together their allocation, optimizer suggestions, and
risk metrics to draw conclusions. An LLM-generated review collapses that
stitching into a single human-readable narrative.

## Decision

- **Model**: Claude Sonnet 4.6 (`claude-sonnet-4-6`) via the Anthropic Python
  SDK. Chosen over Opus 4.7 (5× more expensive, marginal quality gain for this
  task) and Haiku 4.5 (loses nuance on French fiscal advice).
- **Web grounding**: Anthropic's native `web_search_20250305` tool, capped at
  5 searches per review, used to fetch current market context and verify
  fiscal rules.
- **Trigger**: manual button only (no auto-trigger). The user clicks "Générer
  ma review" on the IA tab.
- **Frequency cap**: 1 generated review per (user, calendar day in
  Europe/Paris). Enforced by a UNIQUE constraint on
  `(user_id, review_date)` in `portfolio_reviews`.
- **Cost cap**: hard daily kill-switch at **€5/day** total spend across all
  users. When hit → endpoint returns HTTP 503 with a "réessayer demain"
  message. Atomic increment on a `llm_daily_cost` row keyed by date
  (UPSERT in a single SQL statement to dodge races).
- **Transport**: Server-Sent Events from FastAPI → React. The LLM stream
  chunks reach the user as they are generated; the full markdown is
  persisted once the stream completes.
- **Persistence**: full markdown + token counts + cited source URLs in
  `portfolio_reviews`. Retention = forever (history is the value — users
  can compare reviews across months to spot evolution).
- **Privacy**: Anthropic data-retention disabled per request (zero-log header).
  No user PII in URLs sent to Anthropic; the snapshot we send is anonymized
  (tickers + amounts, no names, no account IDs).

## Alternatives considered

| Option | Why rejected |
|---|---|
| **GPT-5 (OpenAI)** | Equivalent quality, but splits provider count for no upside. One vendor = one set of credentials, retention policies, rate limits. |
| **DeepSeek V3.1** | 5× cheaper, but no native web search + weaker on French fiscal nuance (PEA ceilings, PFU vs IR option, abattements). |
| **Background job (Celery/RQ)** | Overkill for ~45 reviews/day. SSE in-process suffices until ~10× this volume; migration to a queue stays straightforward later. |
| **Auto-trigger after sync** | Rejected — users want intent. An unsolicited review feels intrusive and burns budget on idle accounts. |
| **TER ETF in projections** (related but separate) | Skipped after research showed no reliable free API for European UCITS TER. The LLM review can mention the issue qualitatively. |

## Consequences

- **New folder** `backend/app/llm/` with 4 modules:
  - `anthropic_client.py` — singleton wrapper around `AsyncAnthropic`
  - `cost_tracker.py` — atomic daily-cost increment + kill-switch check
  - `prompt_builder.py` — extract Wealth + Profile + analytics → structured prompt
  - `review_generator.py` — orchestration: SDK call with `web_search`,
    parse stream, count tokens, persist
- **New migrations**: `portfolio_reviews`, `llm_daily_cost` tables (see PR1)
- **New env var**: `ANTHROPIC_API_KEY`, loaded via `os.getenv` to match the
  existing pattern (`JWT_SECRET`, `GOOGLE_OAUTH_CLIENT_ID`, etc.). Stored in
  `backend/.env` (gitignored), required for prod but the LLM features
  degrade gracefully if absent (HTTP 503 with a clear message).
- **New dependency**: `anthropic >= 0.40` in `pyproject.toml`
- **Frontend**: new "IA" tab in 1st position of `App.tsx`, set as the
  default landing tab once the user has at least one synced account.
- **Cost monitoring**: the `llm_daily_cost` table doubles as an observability
  surface — `GET /admin/llm-cost` (future PR) returns a 30-day history.

## Out of scope (future ADRs)

- Multi-language reviews (today: French only)
- Per-user spending caps (today: global kill-switch only)
- Fine-tuned models or custom system prompts per user
- Backtesting / scoring of past recommendations (e.g. did the user follow
  the rebalancing tip and how did it perform?)
- Caching identical prompts (low value: every patrimony snapshot differs
  day-to-day)

## References

- Anthropic SDK reference: https://docs.claude.com/en/api/client-sdks
- `web_search` tool: https://docs.claude.com/en/docs/build-with-claude/tool-use/web-search-tool
- Pricing: https://www.anthropic.com/pricing
- Related: ADR-002 (multi-tenancy), ADR-004 (secrets management)
