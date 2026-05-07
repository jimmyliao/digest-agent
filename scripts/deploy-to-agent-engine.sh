#!/usr/bin/env bash
# Deploy agents/stock SequentialAgent to GEAP / Vertex AI Agent Engine.
#
# Usage:
#   ./scripts/deploy-to-agent-engine.sh
#
# Required env vars (resolution order):
#   1. Shell env (highest priority)
#   2. .env.deploy at repo root (gitignored)
#   3. .env at repo root
#
#   GCP_PROJECT      e.g. bwai2026-jimmyliao-ws
#   STAGING_BUCKET   e.g. gs://bwai2026-jimmyliao-ws-agents
#   GEMINI_API_KEY   from https://aistudio.google.com/app/apikey
#   GCP_LOCATION     optional (default: us-central1)
#
# Prerequisites (one-time):
#   gcloud auth application-default login
#   gcloud services enable aiplatform.googleapis.com storage.googleapis.com cloudbuild.googleapis.com
#   gsutil mb -l us-central1 gs://YOUR_PROJECT-agents
#   IAM: roles/aiplatform.user + roles/storage.admin (owner already covers both)
#
# See GEAP_DEPLOY.md for full details.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Load env from .env.deploy + .env (priority order) ──────────────────────
# Resolution: shell env (highest) > .env.deploy > .env (fallback)
# Skips empty values so a placeholder like GEMINI_API_KEY= doesn't block fallback
load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  local loaded=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      local key="${BASH_REMATCH[1]}"
      local val="${BASH_REMATCH[2]}"
      # strip optional surrounding quotes
      [[ "$val" =~ ^\"(.*)\"$ ]] && val="${BASH_REMATCH[1]}"
      [[ "$val" =~ ^\'(.*)\'$ ]] && val="${BASH_REMATCH[1]}"
      [[ -z "$val" ]] && continue   # skip empty placeholders
      [[ -n "${!key:-}" ]] && continue   # don't overwrite existing
      export "$key=$val"
      loaded=$((loaded+1))
    fi
  done < "$file"
  echo "📂 Loaded $loaded var(s) from: $file"
}

load_env_file .env.deploy
load_env_file .env

GCP_LOCATION="${GCP_LOCATION:-us-central1}"

# ── Validate ────────────────────────────────────────────────────────────────
missing=()
[[ -z "${GCP_PROJECT:-}"    ]] && missing+=("GCP_PROJECT")
[[ -z "${STAGING_BUCKET:-}" ]] && missing+=("STAGING_BUCKET")
[[ -z "${GEMINI_API_KEY:-}" ]] && missing+=("GEMINI_API_KEY")

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "❌ Missing env vars: ${missing[*]}" >&2
  echo "" >&2
  echo "Set them in shell, or in .env.deploy / .env at repo root:" >&2
  echo "  GCP_PROJECT=your-project-id" >&2
  echo "  STAGING_BUCKET=gs://your-project-id-agents" >&2
  echo "  GEMINI_API_KEY=your-api-key" >&2
  echo "  GCP_LOCATION=us-central1   # optional" >&2
  exit 1
fi

# ── Pre-flight check ────────────────────────────────────────────────────────
echo "🔍 Pre-flight check..."
echo "  Project: $GCP_PROJECT"
echo "  Region:  $GCP_LOCATION"
echo "  Bucket:  $STAGING_BUCKET"
echo "  API key: ${GEMINI_API_KEY:0:6}…(${#GEMINI_API_KEY} chars)"
echo ""

errors=0
warns=0

# 1. Project access
if gcloud projects describe "$GCP_PROJECT" >/dev/null 2>&1; then
  echo "  ✅ Project accessible: $GCP_PROJECT"
else
  echo "  ❌ Project $GCP_PROJECT not accessible — run: gcloud auth login" >&2
  errors=$((errors+1))
fi

# 2. Billing enabled (deploy fails partway without billing — fail fast)
if billing_state=$(gcloud beta billing projects describe "$GCP_PROJECT" --format='value(billingEnabled)' 2>/dev/null); then
  if [[ "$billing_state" == "True" ]]; then
    echo "  ✅ Billing enabled"
  else
    echo "  ❌ Billing NOT enabled on $GCP_PROJECT" >&2
    echo "     → Console > Billing > Link a billing account" >&2
    errors=$((errors+1))
  fi
else
  echo "  ⚠️  Could not check billing (gcloud beta not available?) — skipping"
  warns=$((warns+1))
fi

# 3. Required GCP APIs
required_apis=(
  "aiplatform.googleapis.com"
  "storage.googleapis.com"
  "cloudbuild.googleapis.com"
)
enabled_apis=$(gcloud services list --enabled --project="$GCP_PROJECT" --format='value(config.name)' 2>/dev/null || true)
for api in "${required_apis[@]}"; do
  if grep -qx "$api" <<<"$enabled_apis"; then
    echo "  ✅ API: $api"
  else
    echo "  ❌ API missing: $api" >&2
    echo "     → gcloud services enable $api --project=$GCP_PROJECT" >&2
    errors=$((errors+1))
  fi
done

# 4. Staging bucket
if gsutil ls "$STAGING_BUCKET" >/dev/null 2>&1; then
  bucket_loc=$(gsutil ls -L -b "$STAGING_BUCKET" 2>/dev/null | grep "Location constraint:" | awk '{print $NF}')
  bucket_loc_lc=$(printf '%s' "$bucket_loc" | tr '[:upper:]' '[:lower:]')
  region_lc=$(printf '%s' "$GCP_LOCATION" | tr '[:upper:]' '[:lower:]')
  if [[ -n "$bucket_loc" ]] && [[ "$bucket_loc_lc" != "$region_lc" ]] && [[ "$bucket_loc_lc" != "us" ]]; then
    echo "  ⚠️  Bucket region ($bucket_loc) differs from deploy region ($GCP_LOCATION)"
    warns=$((warns+1))
  else
    echo "  ✅ Bucket exists: $STAGING_BUCKET ($bucket_loc)"
  fi
else
  echo "  ❌ Bucket $STAGING_BUCKET not found" >&2
  echo "     → gsutil mb -p $GCP_PROJECT -l $GCP_LOCATION $STAGING_BUCKET" >&2
  errors=$((errors+1))
fi

# 5. ADC (vertexai SDK uses Application Default Credentials)
if gcloud auth application-default print-access-token >/dev/null 2>&1; then
  echo "  ✅ ADC valid"
else
  echo "  ❌ ADC missing — run: gcloud auth application-default login" >&2
  errors=$((errors+1))
fi

# 6. IAM roles (caller needs aiplatform.user + storage.admin, or owner/editor)
caller=$(gcloud config get account 2>/dev/null || echo "")
if [[ -n "$caller" ]]; then
  roles=$(gcloud projects get-iam-policy "$GCP_PROJECT" \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:$caller" \
    --format='value(bindings.role)' 2>/dev/null || true)
  if grep -qE "^roles/(owner|editor)$" <<<"$roles"; then
    echo "  ✅ IAM: $caller has owner/editor (sufficient)"
  elif grep -q "^roles/aiplatform.user$" <<<"$roles" && grep -q "^roles/storage.admin$" <<<"$roles"; then
    echo "  ✅ IAM: $caller has aiplatform.user + storage.admin"
  else
    echo "  ⚠️  IAM: $caller may lack required roles (need aiplatform.user + storage.admin, or owner/editor)"
    echo "     Found: $(tr '\n' ',' <<<"$roles" | sed 's/,$//')"
    warns=$((warns+1))
  fi
fi

echo ""
if [[ $errors -gt 0 ]]; then
  echo "❌ Pre-flight failed: $errors blocker(s) above" >&2
  exit 1
fi
if [[ $warns -gt 0 ]]; then
  echo "✅ Pre-flight passed with $warns warning(s)"
else
  echo "✅ Pre-flight passed"
fi
echo ""

# ── Confirm before spend ───────────────────────────────────────────────────
echo "⚠️  This will:"
echo "   1. uv sync --extra geap  (install vertexai SDK, ~30MB)"
echo "   2. Upload agent tarball to $STAGING_BUCKET"
echo "   3. Trigger Cloud Build (~3-5 min)"
echo "   4. Register Reasoning Engine on Agent Engine Runtime"
echo ""
read -r -p "Continue? [y/N] " ans
case "$ans" in
  [yY]|[yY][eE][sS]) ;;
  *) echo "Aborted."; exit 0 ;;
esac

# ── Execute deploy via Makefile ────────────────────────────────────────────
GCP_PROJECT="$GCP_PROJECT" \
GCP_LOCATION="$GCP_LOCATION" \
STAGING_BUCKET="$STAGING_BUCKET" \
GEMINI_API_KEY="$GEMINI_API_KEY" \
make deploy-agent-engine
