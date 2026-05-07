#!/usr/bin/env bash
# Set up the GCS bucket used by Litestream to back the Next.js apps/web/
# SQLite database (/data/digest.db). Idempotent — safe to re-run.
#
# Usage:
#   ./scripts/setup-data-bucket.sh                  # uses ${GCP_PROJECT}-data
#   ./scripts/setup-data-bucket.sh my-bucket-name   # custom bucket name
#
# Reads GCP_PROJECT from .env.deploy / .env (same loader as
# setup-billing-alert.sh / deploy-to-agent-engine.sh).
#
# What it does:
#   1. Create gs://${BUCKET_NAME} (us-central1) if missing
#   2. Enable object versioning (recover from accidental delete)
#   3. Set 30-day lifecycle GC on noncurrent generations
#   4. Grant the Cloud Run runtime SA roles/storage.objectAdmin on the bucket
#   5. Print LITESTREAM_GCS_BUCKET=... for copy into .env.deploy
#
# Bash 3.2 compatible (works on macOS default bash).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Load env from .env.deploy + .env ───────────────────────────────────────
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

BUCKET_NAME="${1:-${GCP_PROJECT}-data}"
BUCKET_URI="gs://${BUCKET_NAME}"
LOCATION="${GCP_LOCATION:-us-central1}"

echo "🔍 Pre-check..."
echo "  Project        : $GCP_PROJECT"
echo "  Bucket         : $BUCKET_URI"
echo "  Location       : $LOCATION"
echo ""

# Track whether anything actually changed (for "Already configured" exit)
changed=0

# 1. Create bucket if missing
if gsutil ls -b "$BUCKET_URI" >/dev/null 2>&1; then
  echo "  ✅ Bucket exists: $BUCKET_URI"
else
  echo "  → Creating bucket $BUCKET_URI in $LOCATION..."
  gsutil mb -p "$GCP_PROJECT" -l "$LOCATION" "$BUCKET_URI"
  echo "  ✅ Bucket created"
  changed=1
fi

# 2. Versioning
versioning_state=$(gsutil versioning get "$BUCKET_URI" 2>/dev/null | awk '{print $NF}' | tr '[:upper:]' '[:lower:]')
if [[ "$versioning_state" == "enabled" ]]; then
  echo "  ✅ Versioning already enabled"
else
  echo "  → Enabling versioning..."
  gsutil versioning set on "$BUCKET_URI"
  echo "  ✅ Versioning enabled"
  changed=1
fi

# 3. Lifecycle: delete noncurrent generations >30d old
# Use a tmp file (bash 3.2 process substitution works but be explicit for portability)
LIFECYCLE_TMP=$(mktemp -t digest-lifecycle.XXXXXX)
# shellcheck disable=SC2064
trap "rm -f '$LIFECYCLE_TMP'" EXIT
cat >"$LIFECYCLE_TMP" <<'JSON'
{"rule":[{"action":{"type":"Delete"},"condition":{"daysSinceNoncurrentTime":30}}]}
JSON

# Compare against existing config to detect change. Strip whitespace for comparison.
existing_lifecycle=$(gsutil lifecycle get "$BUCKET_URI" 2>/dev/null || true)
desired_lifecycle=$(cat "$LIFECYCLE_TMP")
existing_compact=$(printf '%s' "$existing_lifecycle" | tr -d ' \t\n\r')
desired_compact=$(printf '%s' "$desired_lifecycle" | tr -d ' \t\n\r')

if [[ "$existing_compact" == "$desired_compact" ]]; then
  echo "  ✅ Lifecycle policy already in sync (30d noncurrent GC)"
else
  echo "  → Setting lifecycle policy (delete noncurrent >30d)..."
  gsutil lifecycle set "$LIFECYCLE_TMP" "$BUCKET_URI"
  echo "  ✅ Lifecycle policy set"
  changed=1
fi

# 4. Resolve project number → Cloud Run runtime SA
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)' 2>/dev/null || true)
if [[ -z "$PROJECT_NUMBER" ]]; then
  echo "  ❌ Cannot resolve project number for $GCP_PROJECT" >&2
  exit 1
fi
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "  Runtime SA     : $RUNTIME_SA"

# Check if SA already has objectAdmin on this bucket
sa_member="serviceAccount:${RUNTIME_SA}"
existing_iam=$(gsutil iam get "$BUCKET_URI" 2>/dev/null || echo "")
if printf '%s' "$existing_iam" | grep -q "\"$sa_member\"" \
   && printf '%s' "$existing_iam" | grep -q "roles/storage.objectAdmin"; then
  # Coarse check; refine with python if available
  if printf '%s' "$existing_iam" | python3 -c "
import json, sys
data = json.load(sys.stdin)
member = '$sa_member'
role = 'roles/storage.objectAdmin'
for b in data.get('bindings', []):
    if b.get('role') == role and member in b.get('members', []):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    echo "  ✅ Runtime SA already has roles/storage.objectAdmin on bucket"
  else
    echo "  → Granting roles/storage.objectAdmin to $RUNTIME_SA..."
    gsutil iam ch "${sa_member}:objectAdmin" "$BUCKET_URI"
    echo "  ✅ IAM granted"
    changed=1
  fi
else
  echo "  → Granting roles/storage.objectAdmin to $RUNTIME_SA..."
  gsutil iam ch "${sa_member}:objectAdmin" "$BUCKET_URI"
  echo "  ✅ IAM granted"
  changed=1
fi

echo ""
if [[ $changed -eq 0 ]]; then
  echo "✅ Already configured — no changes needed."
else
  echo "✅ Setup complete."
fi
echo ""
echo "💡 Add this to .env.deploy so make deploy-web picks it up:"
echo ""
echo "    LITESTREAM_GCS_BUCKET=${BUCKET_NAME}"
echo ""
echo "🔗 Bucket console:"
echo "    https://console.cloud.google.com/storage/browser/${BUCKET_NAME}?project=${GCP_PROJECT}"
