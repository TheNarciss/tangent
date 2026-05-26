# Powens API reference (local cache)

Files in this directory are mirrored from `docs.powens.com`. Re-run
`bash scripts/fetch_powens_docs.sh` to refresh.

## Files by topic

| Topic | File |
|---|---|
| **Data model** — every field for every resource | `20-bank-accounts.md`, `22-bank-transactions.md`, `30-investments.md` |
| **Account types** — full list of types Powens supports | `21-bank-account-types.md` |
| **Wealth** — investments, loans, pockets, orders | `30-*.md` to `33-*.md` |
| **Connections** — connection state machine, expand fields | `11-connections.md`, `12-connectors.md` |
| **Webview** — flows for connect/manage/reset | `50-webview.md` |
| **Webhooks** — events emitted during sync | `51-webhooks.md` |
| **Errors** — error codes catalog | `02-errors.md` |

## How to find a field

Run: `grep -i "<field_name>" *.md` from this directory.

Example:
```
grep -i "next_payment_amount" *.md
```

Tells you which resource declares this field and what it means.
