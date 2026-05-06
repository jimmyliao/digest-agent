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

# ── Load env from .env.deploy or .env if vars not already set ──────────────
load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  # shellcheck disable=SC1090
  set -a; . "$file"; set +a
  echo "📂 Loaded env from: $file"
}

[[ -z "${GCP_PROJECT:-}" ]] && load_env_file .env.deploy
[[ -z "${GCP_PROJECT:-}" ]] && load_env_file .env

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

if ! gcloud projects describe "$GCP_PROJECT" >/dev/null 2>&1; then
  echo "❌ Project $GCP_PROJECT not accessible — run: gcloud auth login" >&2
  exit 1
fi

if ! gsutil ls "$STAGING_BUCKET" >/dev/null 2>&1; then
  echo "❌ Bucket $STAGING_BUCKET not found — create with:" >&2
  echo "   gsutil mb -p $GCP_PROJECT -l $GCP_LOCATION $STAGING_BUCKET" >&2
  exit 1
fi

if ! gcloud services list --enabled --project="$GCP_PROJECT" 2>/dev/null | grep -q aiplatform.googleapis.com; then
  echo "❌ aiplatform.googleapis.com not enabled — enable with:" >&2
  echo "   gcloud services enable aiplatform.googleapis.com --project=$GCP_PROJECT" >&2
  exit 1
fi

echo "✅ Pre-flight passed"
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
