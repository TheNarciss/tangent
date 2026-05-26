#!/usr/bin/env bash
# fetch_powens_docs.sh
# Télécharge la documentation Powens API en local sous forme de .md
# Chaque page de docs.powens.com a une version .md accessible via l'URL + ".md"
#
# Usage:  bash fetch_powens_docs.sh
# Output: backend/docs/powens_reference/*.md
#
# Re-run quand tu veux refresh la doc (Powens la met à jour de temps en temps).

set -euo pipefail

# Cible
TARGET_DIR="${PROJECT_ROOT:-$(pwd)}/backend/docs/powens_reference"
mkdir -p "$TARGET_DIR"

# Toutes les pages de la doc API qui nous intéressent.
# Tu peux en rajouter — il suffit de copier l'URL depuis docs.powens.com et ajouter .md
PAGES=(
  # ── Overview ─────────────────────────────────────────────────────────────
  "https://docs.powens.com/api-reference/overview/api-design.md|00-api-design.md"
  "https://docs.powens.com/api-reference/overview/authentication.md|01-authentication.md"
  "https://docs.powens.com/api-reference/overview/errors.md|02-errors.md"
  "https://docs.powens.com/api-reference/overview/fair-usage-policy.md|03-fair-usage-policy.md"

  # ── User & connections ───────────────────────────────────────────────────
  "https://docs.powens.com/api-reference/users/users.md|10-users.md"
  "https://docs.powens.com/api-reference/user-connections/connections.md|11-connections.md"
  "https://docs.powens.com/api-reference/user-connections/connectors.md|12-connectors.md"
  "https://docs.powens.com/api-reference/user-connections/banks.md|13-banks.md"

  # ── Data aggregation (bank) ──────────────────────────────────────────────
  "https://docs.powens.com/api-reference/products/data-aggregation/bank-accounts.md|20-bank-accounts.md"
  "https://docs.powens.com/api-reference/products/data-aggregation/bank-account-types.md|21-bank-account-types.md"
  "https://docs.powens.com/api-reference/products/data-aggregation/bank-transactions.md|22-bank-transactions.md"
  "https://docs.powens.com/api-reference/products/data-aggregation/categories.md|23-categories.md"
  "https://docs.powens.com/api-reference/products/data-aggregation/balances.md|24-balances.md"

  # ── Wealth aggregation (investments, loans, pockets, market orders) ─────
  "https://docs.powens.com/api-reference/products/wealth-aggregation/investments.md|30-investments.md"
  "https://docs.powens.com/api-reference/products/wealth-aggregation/market-orders.md|31-market-orders.md"
  "https://docs.powens.com/api-reference/products/wealth-aggregation/pockets.md|32-pockets.md"
  "https://docs.powens.com/api-reference/products/wealth-aggregation/loan-amortizations.md|33-loan-amortizations.md"

  # ── Documents aggregation ────────────────────────────────────────────────
  "https://docs.powens.com/api-reference/products/documents-aggregation/subscriptions.md|40-subscriptions.md"
  "https://docs.powens.com/api-reference/products/documents-aggregation/documents.md|41-documents.md"
  "https://docs.powens.com/api-reference/products/documents-aggregation/document-types.md|42-document-types.md"
  "https://docs.powens.com/api-reference/products/documents-aggregation/connection-identity.md|43-connection-identity.md"

  # ── Webview & webhooks ───────────────────────────────────────────────────
  "https://docs.powens.com/api-reference/overview/webview.md|50-webview.md"
  "https://docs.powens.com/api-reference/overview/webhooks.md|51-webhooks.md"

  # ── Common objects ───────────────────────────────────────────────────────
  "https://docs.powens.com/api-reference/overview/currencies.md|60-currencies.md"
  "https://docs.powens.com/api-reference/overview/countries.md|61-countries.md"
)

echo "Downloading Powens docs to: $TARGET_DIR"
echo ""

COUNT_OK=0
COUNT_FAIL=0
FAILED=()

for entry in "${PAGES[@]}"; do
  url="${entry%|*}"
  filename="${entry##*|}"
  target="$TARGET_DIR/$filename"

  printf "  %-45s" "$filename"

  if response=$(curl -sS -w "\n%{http_code}" "$url" 2>&1); then
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    if [[ "$http_code" == "200" ]]; then
      echo "$body" > "$target"
      lines=$(wc -l < "$target" | tr -d ' ')
      echo "OK ($lines lines)"
      COUNT_OK=$((COUNT_OK + 1))
    else
      echo "HTTP $http_code"
      COUNT_FAIL=$((COUNT_FAIL + 1))
      FAILED+=("$filename ($http_code)")
    fi
  else
    echo "ERR"
    COUNT_FAIL=$((COUNT_FAIL + 1))
    FAILED+=("$filename (network)")
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Downloaded:  $COUNT_OK"
echo "✗ Failed:      $COUNT_FAIL"
if [[ ${#FAILED[@]} -gt 0 ]]; then
  echo ""
  echo "Failed pages (URL may have changed in Powens doc):"
  for f in "${FAILED[@]}"; do echo "    $f"; done
fi

# Create a README pointing to the relevant files
cat > "$TARGET_DIR/README.md" << 'EOF'
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
EOF

echo ""
echo "Done. See $TARGET_DIR/README.md for navigation."
