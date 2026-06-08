# ADR-021: Universal Gap-Filler for nullable provider fields

- **Status**: Accepted
- **Date**: 2026-06-08
- **Supersedes / Relates to**: ADR-013 (Powens hot+JSONB storage), ADR-015 (LLM portfolio reviews), ADR-018 (nightly batched reviews)

## Context

Tangent depends on third-party data providers (Powens for banking, yfinance + FMP for market data) whose responses are **incomplete by design**:

- **TER (Total Expense Ratio)** of an ETF — Powens never returns it; yfinance returns it for ~30% of European ETFs and is sometimes wrong (e.g. `WPEA.PA` returns `0.20%` while the official KID says `0.25%`).
- **Transaction category** — Powens leaves it NULL in 100% of cases we observe (117/117 transactions in prod).
- **ISIN** on holdings — missing in ~30% of Powens responses for less-known securities.

These NULLs propagate downstream:

- Projection cannot apply a realistic monthly TER cost → understated fees, overstated returns.
- Budgeting dashboard cannot group transactions without categories.
- Optimizer cannot match holdings to factsheets when ISIN is missing.

Prior workarounds were point solutions: a `KNOWN_PEA_ETFS_TER` constant hardcoded in `scanner.py`, manual UI to rename transactions one by one. Neither scales beyond Clem's own portfolio.

## Decision

Introduce a **Universal Gap-Filler**: a registry-based architecture where any nullable DB column can be declared "gappable", and a nightly LLM batch fills it. User overrides remain authoritative.

### Architecture

```
backend/app/finance/gap_filler/
├── registry.py    — GappableField dataclass + register_field()
├── engine.py      — collect_gaps, build_requests, apply_response
└── fields/
    ├── holding_ter.py
    ├── transaction_category.py
    └── holding_isin.py
```

Each field declares:

- target DB column (table + column name)
- a `*_source` tracking column (`'api'` / `'llm'` / `'user'` / `NULL`)
- a `build_prompt(row)` callable that produces the LLM context
- a `response_schema` (Anthropic tool_use input_schema, **structured output forced via `tool_choice`**)
- a `validate_value(v)` predicate
- an optional `coerce_value(v)` transformer

### Source precedence

```
'user' > 'llm' > 'api' > NULL
```

The engine's `collect_gaps()` filters with `source IS DISTINCT FROM 'user'`, so user overrides are immutable across re-runs. LLM fills overwrite NULL or stale `api` values; `api` values from providers overwrite `llm` only when the provider catches up (e.g. Powens later returns a category that's accepted as ground truth).

### Custom_id encoding for Anthropic batch

Format: `gap_<field_name>_<row_uuid>`

- Field names constrained to `^[a-z][a-z0-9]*$` (no underscores).
- UUID is the standard 8-4-4-4-12 hex form.
- Regex-decoded in `decode_custom_id()` for unambiguous dispatch in the poller.

### Integration with the nightly batch (ADR-018)

The existing `submit_nightly_batch()` in `batch_submitter.py` was extended:

1. Build review requests (existing path, opt-in users only).
2. Call `gap_filler_engine.collect_gaps(session)` and `build_gap_fill_requests()`.
3. Concatenate both lists; submit a single Anthropic batch (one 50% discount, one cost cap).
4. Persist `n_requests` and `estimated_cost_usd` reflecting both review and gap-fill counts.

In `batch_poller.py`, the result loop dispatches by `custom_id` prefix:

- `gap_*` → `apply_gap_fill_response()` (write to DB with `source='llm'`)
- else → existing review handling

Gap-fill failures **never** poison the review path — collection is wrapped in try/except, and per-result errors only increment counters.

### Cost model

- Per gap-fill: ~250 input tokens + 100 output tokens + 1 web_search.
- At Sonnet 4.6 batch pricing: **~$0.005 per gap** (web_search is not batch-discounted).
- First-night cost on Tangent's prod state (123 gaps: 117 categories + 6 TERs): **~$0.60**, well under the existing $5/day cap.
- Steady-state: only newly-synced rows have gaps → cost drops to **near-zero**.

### User-facing surface

| Endpoint | Auth | Action |
|----------|------|--------|
| `PUT /api/accounts/holdings/{id}/ter` | active user | sets `source='user'`, beats LLM forever |
| `PUT /api/accounts/transactions/{id}/category` | active user | idem, validates against closed taxonomy |
| `GET /api/admin/data-sources` | superuser | audit: counts per `(table.field, source)` |

### Downstream consumer: Projection

`projection.build()` now accepts an optional `weighted_ter` parameter (computed in the route via `account_holdings.get_weighted_ter()`). The broker `fee_fn` closure is wrapped by `fees.apply_ter_to_fee_fn(fee_fn, weighted_ter)`, which adds `value * weighted_ter / 12` per month on top. With `weighted_ter=0`, the wrap is an identity no-op → bit-for-bit backward compatibility.

## Alternatives considered

### A. Hardcoded mapping (`KNOWN_PEA_ETFS_TER`)

- ✅ Zero LLM cost, deterministic.
- ❌ Doesn't scale beyond a handful of well-known PEA ETFs.
- ❌ Requires manual update for every new holding the user buys.
- ❌ Single field only — no equivalent for categories or ISINs.
- **Verdict**: rejected as a long-term strategy; kept only as an in-process fallback if needed.

### B. Synchronous LLM call at request time

- ✅ Immediate feedback in UI.
- ❌ Adds 1-3 s latency per Projection load.
- ❌ Pays full Anthropic price (no batch discount).
- ❌ Repeats the same lookup on every page load.
- **Verdict**: rejected — gap-fills are persistent, batching wins.

### C. Polymorphic `gap_fills` table

```sql
CREATE TABLE gap_fills (
  id UUID PK,
  table_name TEXT,
  row_id UUID,
  field_name TEXT,
  source TEXT,
  resolved_at TIMESTAMPTZ,
  ...
);
```

- ✅ One schema for everything.
- ❌ Forces a JOIN every time we read TER/category.
- ❌ No native NULL handling — every read needs to LEFT JOIN and COALESCE.
- ❌ Foreign keys can't be enforced (polymorphic `row_id`).
- **Verdict**: rejected at Tangent's scale. The 3-column-per-field overhead (`*`, `*_source`, `*_resolved_at`) is cheap on PostgreSQL and reads stay direct.

### D. Wait for Powens to fix their API

- ❌ Powens hasn't categorized our transactions in 18 months of production.
- **Verdict**: not happening.

## Consequences

### Positive

- **Scales to any nullable field** — adding a new gappable field is one Python module in `fields/` (no engine changes, no migration if the columns already exist).
- **User stays in control** — `source='user'` is immutable, the UI can show provenance ("Estimation IA, à vérifier" badge).
- **Auditable** — `GET /api/admin/data-sources` shows exactly how many rows came from where.
- **Cost-bounded** — reuses the existing `$5/day` daily cost cap and the batch discount.
- **No degradation if gap-fill is disabled** — `weighted_ter=0` is a no-op identity wrap; existing routes still work.

### Negative

- **+7 nullable columns across 2 tables** (migration `c8d1f5e9b6a4`). Tolerable PostgreSQL overhead at our scale.
- **LLM hallucination risk** — mitigated by (1) forced tool_use with strict JSON schemas, (2) `validate_value()` predicates, (3) source tagging so user can spot and override, (4) explicit "return null if unsure" instructions in the prompts.
- **No retry per-gap on transient LLM errors** — only the whole batch retries (via tenacity on the submit call). Gap-fill failures within a successful batch are logged and skipped; the next nightly run picks them up.

### Neutral / future work

- ADR-021 establishes the pattern, but only 3 fields are registered today (TER, category, ISIN). Future candidates:
  - `loans.rate` (rarely returned by Powens; LLM could infer from monthly_payment + duration).
  - `bank_accounts.iban`, `bank_accounts.bic` — usually NULL, sometimes resolvable.
  - `account_holdings.label` cleanup (e.g. " - PEA" suffix stripping).
- Frontend UI is **not** in this PR. PR2 (separate) will add an `<DataField>` component showing the source badge and inline editing.
