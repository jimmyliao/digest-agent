#!/usr/bin/env bash
# Set up a monthly GCP billing budget alert for the deploy project.
# Defaults to $5 USD with notifications at 50% / 90% / 100% — covers
# casual digest-agent usage with healthy margin.
#
# Usage:
#   ./scripts/setup-billing-alert.sh                       # $5 USD default
#   ./scripts/setup-billing-alert.sh 10                    # $10 USD
#   ./scripts/setup-billing-alert.sh 10 "my-custom-name"   # custom display name
#
# Reads GCP_PROJECT from .env.deploy / .env (same loader as deploy.sh).
# Notifications go to billing admins (you, since you set up billing).
# Idempotent: if a budget with same display_name exists, skip creation.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      local val="${BASH_REMATCH[2]}"
      [[ "$val" =~ ^\"(.*)\"$ ]] && val="${BASH_REMATCH[1]}"
      [[ "$val" =~ ^\'(.*)\'$ ]] && val="${BASH_REMATCH[1]}"
      [[ -z "$val" ]] && continue
      [[ -n "${!key:-}" ]] && continue
      export "$key=$val"
    fi
  done < "$file"
}

load_env_file .env.deploy
load_env_file .env

if [[ -z "${GCP_PROJECT:-}" ]]; then
  echo "❌ GCP_PROJECT not set in .env.deploy / .env" >&2
  exit 1
fi

AMOUNT="${1:-5}"
DISPLAY_NAME="${2:-${GCP_PROJECT}-monthly-budget-${AMOUNT}usd}"

echo "🔍 Pre-check..."
echo "  Project        : $GCP_PROJECT"
echo "  Budget amount  : \$${AMOUNT} USD/month"
echo "  Display name   : $DISPLAY_NAME"

# 1. Resolve billing account
BILLING=$(gcloud beta billing projects describe "$GCP_PROJECT" --format='value(billingAccountName)' 2>/dev/null || true)
if [[ -z "$BILLING" ]]; then
  echo "❌ No billing account linked to $GCP_PROJECT — link one in Console first" >&2
  exit 1
fi
BILLING_ID="${BILLING#billingAccounts/}"
echo "  Billing account: $BILLING_ID"

# 2. Get project number for filter
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)' 2>/dev/null || true)
if [[ -z "$PROJECT_NUMBER" ]]; then
  echo "❌ Cannot resolve project number for $GCP_PROJECT" >&2
  exit 1
fi
echo "  Project number : $PROJECT_NUMBER"

# 3a. Ensure billingbudgets API is enabled (one-time per project)
if ! gcloud services list --enabled --project="$GCP_PROJECT" --format="value(config.name)" 2>/dev/null | grep -qx "billingbudgets.googleapis.com"; then
  echo "  → Enabling billingbudgets.googleapis.com..."
  gcloud services enable billingbudgets.googleapis.com --project="$GCP_PROJECT"
  echo "    (waiting 10s for API to propagate)"
  sleep 10
fi

# 3b. Idempotency: check if same-named budget exists
EXISTING=$(gcloud billing budgets list \
  --billing-account="$BILLING_ID" \
  --format="value(displayName)" 2>/dev/null \
  | grep -Fx "$DISPLAY_NAME" || true)

if [[ -n "$EXISTING" ]]; then
  echo ""
  echo "⚠️  Budget '$DISPLAY_NAME' already exists. Skipping create."
  echo ""
  echo "Manage at:"
  echo "  https://console.cloud.google.com/billing/$BILLING_ID/budgets?project=$GCP_PROJECT"
  echo ""
  echo "To delete: gcloud billing budgets list --billing-account=$BILLING_ID"
  echo "           gcloud billing budgets delete <BUDGET_ID> --billing-account=$BILLING_ID"
  exit 0
fi

# 4. Create budget with 50% / 90% / 100% thresholds
echo ""
echo "💰 Creating budget..."
gcloud billing budgets create \
  --billing-account="$BILLING_ID" \
  --display-name="$DISPLAY_NAME" \
  --budget-amount="${AMOUNT}USD" \
  --threshold-rule=percent=0.50 \
  --threshold-rule=percent=0.90 \
  --threshold-rule=percent=1.00 \
  --filter-projects="projects/${PROJECT_NUMBER}" \
  --quiet

echo ""
echo "✅ Budget created. Email alerts at 50%, 90%, 100% will be sent to billing admins."
echo ""
echo "🔗 Manage:"
echo "  https://console.cloud.google.com/billing/$BILLING_ID/budgets?project=$GCP_PROJECT"
echo ""
echo "💡 Tip: For digest-agent typical usage (idle + occasional invokes),"
echo "       you'll likely never trigger \$${AMOUNT} unless something runaway happens."
