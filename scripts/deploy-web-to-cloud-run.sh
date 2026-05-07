#!/usr/bin/env bash
# Deploy apps/web/ (Next.js + Litestream) to Cloud Run with GCS-backed
# SQLite persistence.
#
# Usage:
#   ./scripts/deploy-web-to-cloud-run.sh
#
# Required env vars (resolution order):
#   1. Shell env (highest priority)
#   2. .env.deploy at repo root (gitignored)
#   3. .env at repo root
#
#   GCP_PROJECT             e.g. bwai2026-jimmyliao-ws
#   LITESTREAM_GCS_BUCKET   e.g. bwai2026-jimmyliao-ws-data  (no gs:// prefix)
#   GCP_LOCATION            optional (default: us-central1)
#
# Prerequisites (one-time):
#   ./scripts/setup-data-bucket.sh
#   gcloud auth application-default login
#   gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
#                          storage.googleapis.com artifactregistry.googleapis.com
#
# After successful deploy: print Cloud Run URL + tip to add DIGEST_API_URL
# to .env.deploy so the GEAP redeploy reaches this endpoint.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Load env from .env.deploy + .env ───────────────────────────────────────
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
      [[ "$val" =~ ^\"(.*)\"$ ]] && val="${BASH_REMATCH[1]}"
      [[ "$val" =~ ^\'(.*)\'$ ]] && val="${BASH_REMATCH[1]}"
      [[ -z "$val" ]] && continue
      [[ -n "${!key:-}" ]] && continue
      export "$key=$val"
      loaded=$((loaded+1))
    fi
  done < "$file"
  echo "📂 Loaded $loaded var(s) from: $file"
}

load_env_file .env.deploy
load_env_file .env

GCP_LOCATION="${GCP_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-digest-agent-web}"

# ── Validate ────────────────────────────────────────────────────────────────
missing=()
[[ -z "${GCP_PROJECT:-}"           ]] && missing+=("GCP_PROJECT")
[[ -z "${LITESTREAM_GCS_BUCKET:-}" ]] && missing+=("LITESTREAM_GCS_BUCKET")

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "❌ Missing env vars: ${missing[*]}" >&2
  echo "" >&2
  echo "Set them in shell, or in .env.deploy / .env at repo root:" >&2
  echo "  GCP_PROJECT=your-project-id" >&2
  echo "  LITESTREAM_GCS_BUCKET=your-project-id-data" >&2
  echo "  GCP_LOCATION=us-central1   # optional" >&2
  echo "" >&2
  echo "Tip: run ./scripts/setup-data-bucket.sh first to provision the GCS bucket." >&2
  exit 1
fi

# Strip accidental gs:// prefix if present
LITESTREAM_GCS_BUCKET="${LITESTREAM_GCS_BUCKET#gs://}"
LITESTREAM_GCS_BUCKET="${LITESTREAM_GCS_BUCKET%/}"
BUCKET_URI="gs://${LITESTREAM_GCS_BUCKET}"

# ── Pre-flight check (8 items, mirrors deploy-to-agent-engine.sh) ──────────
echo "🔍 Pre-flight check..."
echo "  Project : $GCP_PROJECT"
echo "  Region  : $GCP_LOCATION"
echo "  Service : $SERVICE_NAME"
echo "  Bucket  : $BUCKET_URI"
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

# 2. Billing enabled
if billing_state=$(gcloud beta billing projects describe "$GCP_PROJECT" --format='value(billingEnabled)' 2>/dev/null); then
  if [[ "$billing_state" == "True" ]]; then
    echo "  ✅ Billing enabled"
  else
    echo "  ❌ Billing NOT enabled on $GCP_PROJECT" >&2
    errors=$((errors+1))
  fi
else
  echo "  ⚠️  Could not check billing — skipping"
  warns=$((warns+1))
fi

# 3. Required APIs
required_apis=(
  "run.googleapis.com"
  "cloudbuild.googleapis.com"
  "storage.googleapis.com"
  "artifactregistry.googleapis.com"
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

# 4. Data bucket exists
if gsutil ls -b "$BUCKET_URI" >/dev/null 2>&1; then
  echo "  ✅ Data bucket exists: $BUCKET_URI"
else
  echo "  ❌ Data bucket $BUCKET_URI not found" >&2
  echo "     → Run: ./scripts/setup-data-bucket.sh" >&2
  errors=$((errors+1))
fi

# 5. Runtime SA has objectAdmin on bucket
PROJECT_NUMBER=$(gcloud projects describe "$GCP_PROJECT" --format='value(projectNumber)' 2>/dev/null || true)
if [[ -n "$PROJECT_NUMBER" ]]; then
  RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
  sa_member="serviceAccount:${RUNTIME_SA}"
  bucket_iam=$(gsutil iam get "$BUCKET_URI" 2>/dev/null || echo "")
  if printf '%s' "$bucket_iam" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)
member = '$sa_member'
for b in data.get('bindings', []):
    if b.get('role') == 'roles/storage.objectAdmin' and member in b.get('members', []):
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    echo "  ✅ Runtime SA has objectAdmin on bucket"
  else
    echo "  ⚠️  Runtime SA ($RUNTIME_SA) may lack objectAdmin on $BUCKET_URI" >&2
    echo "     → Run: ./scripts/setup-data-bucket.sh" >&2
    warns=$((warns+1))
  fi
fi

# 6. ADC
if gcloud auth application-default print-access-token >/dev/null 2>&1; then
  echo "  ✅ ADC valid"
else
  echo "  ❌ ADC missing — run: gcloud auth application-default login" >&2
  errors=$((errors+1))
fi

# 7. ADC quota project matches
adc_qp=$(python3 -c "import json,sys,os; p=os.path.expanduser('~/.config/gcloud/application_default_credentials.json'); print(json.load(open(p)).get('quota_project_id','')) if os.path.exists(p) else print('')" 2>/dev/null)
if [[ -z "$adc_qp" ]]; then
  echo "  ⚠️  ADC quota project not set"
  echo "     → gcloud auth application-default set-quota-project $GCP_PROJECT"
  warns=$((warns+1))
elif [[ "$adc_qp" != "$GCP_PROJECT" ]]; then
  echo "  ⚠️  ADC quota project ($adc_qp) ≠ deploy project ($GCP_PROJECT)"
  warns=$((warns+1))
else
  echo "  ✅ ADC quota project matches: $adc_qp"
fi

# 8. IAM (caller can deploy Cloud Run + trigger Cloud Build)
caller=$(gcloud config get account 2>/dev/null || echo "")
if [[ -n "$caller" ]]; then
  roles=$(gcloud projects get-iam-policy "$GCP_PROJECT" \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:$caller" \
    --format='value(bindings.role)' 2>/dev/null || true)
  if grep -qE "^roles/(owner|editor)$" <<<"$roles"; then
    echo "  ✅ IAM: $caller has owner/editor"
  elif grep -q "^roles/run.admin$" <<<"$roles" && grep -q "^roles/cloudbuild.builds.editor$" <<<"$roles"; then
    echo "  ✅ IAM: $caller has run.admin + cloudbuild.builds.editor"
  else
    echo "  ⚠️  IAM: $caller may lack required roles (need owner/editor or run.admin+cloudbuild.builds.editor)"
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
echo "   1. Cloud Build via cloudbuild.web.yaml (repo-root context, ~3-5 min)"
echo "      → builds apps/web/Dockerfile which needs infra/ + packages/ from root"
echo "   2. gcloud run deploy --image to $SERVICE_NAME in $GCP_LOCATION"
echo "   3. Inject env: LITESTREAM_GCS_BUCKET=$LITESTREAM_GCS_BUCKET"
echo "                  DATABASE_URL=file:/data/digest.db"
echo ""
# Auto-proceed in three cases (workshop / CI / scripted runs):
#   1. Non-interactive stdin (`make deploy-web > log.txt 2>&1 &`, CI runners,
#      `gcloud cloud-shell ssh --command="..."` — read -r would EOF and `set -e`
#      would kill the script with exit 1, which is misleading)
#   2. CONFIRM_DEPLOY=y env var (explicit opt-in for scripted unattended runs)
#   3. User answers y/yes at the interactive prompt
if [[ ! -t 0 ]]; then
  echo "ℹ️  stdin not a terminal — auto-proceeding (set CONFIRM_DEPLOY=n to abort)"
  [[ "${CONFIRM_DEPLOY:-y}" == "n" ]] && { echo "Aborted (CONFIRM_DEPLOY=n)."; exit 0; }
elif [[ -n "${CONFIRM_DEPLOY:-}" ]]; then
  echo "ℹ️  CONFIRM_DEPLOY=${CONFIRM_DEPLOY} — skipping prompt"
  case "$CONFIRM_DEPLOY" in [yY]|[yY][eE][sS]) ;; *) echo "Aborted."; exit 0 ;; esac
else
  read -r -p "Continue? [y/N] " ans
  case "$ans" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

# ── Ensure Artifact Registry repo exists ──────────────────────────────────
AR_REPO="${AR_REPO:-cloud-run-source-deploy}"
if ! gcloud artifacts repositories describe "$AR_REPO" \
      --location="$GCP_LOCATION" --project="$GCP_PROJECT" >/dev/null 2>&1; then
  echo "📦 Creating Artifact Registry repo: $AR_REPO ($GCP_LOCATION)..."
  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$GCP_LOCATION" \
    --project="$GCP_PROJECT" \
    --quiet
fi

IMAGE="${GCP_LOCATION}-docker.pkg.dev/${GCP_PROJECT}/${AR_REPO}/${SERVICE_NAME}:$(date +%Y%m%d-%H%M%S)"
echo "🏷  Image: $IMAGE"
echo ""

# ── Build via Cloud Build (repo root context, custom Dockerfile path) ─────
echo "🏗  Building image via Cloud Build (cloudbuild.web.yaml)..."
gcloud builds submit \
  --config cloudbuild.web.yaml \
  --substitutions "_IMAGE=$IMAGE" \
  --project "$GCP_PROJECT" \
  --quiet \
  .

# ── Deploy to Cloud Run ────────────────────────────────────────────────────
echo ""
echo "🚀 Deploying $SERVICE_NAME..."
echo ""

# Build the env-vars list. Two design choices worth knowing:
#   1. `^|^` custom delimiter — values may contain commas freely (default `,`
#      splits e.g. an LLM key or comma-separated config silently). See
#      https://cloud.google.com/sdk/gcloud/reference/topic/escaping
#   2. `--update-env-vars` (NOT `--set-env-vars`) — `--set-env-vars` REPLACES
#      the entire env on the service every deploy, which means any var not
#      listed here gets DROPPED. That bites students who set vars from
#      Console / manual gcloud previously, or have an evolving .env.deploy.
#      `--update-env-vars` merges, so listed keys are upserted and the rest
#      are preserved. Use `gcloud run services update --remove-env-vars` if
#      you genuinely need to remove a key.
ENV_VARS="^|^LITESTREAM_GCS_BUCKET=$LITESTREAM_GCS_BUCKET|DATABASE_URL=file:/data/digest.db"
[[ -n "${GEAP_RESOURCE_NAME:-}" ]]   && ENV_VARS="$ENV_VARS|GEAP_RESOURCE_NAME=$GEAP_RESOURCE_NAME"
[[ -n "${BASIC_AUTH_USER:-}" ]]      && ENV_VARS="$ENV_VARS|BASIC_AUTH_USER=$BASIC_AUTH_USER"
[[ -n "${BASIC_AUTH_PASSWORD:-}" ]]  && ENV_VARS="$ENV_VARS|BASIC_AUTH_PASSWORD=$BASIC_AUTH_PASSWORD"
[[ -n "${LLM_PROVIDER:-}" ]]         && ENV_VARS="$ENV_VARS|LLM_PROVIDER=$LLM_PROVIDER"
[[ -n "${GEMINI_API_KEY:-}" ]]       && ENV_VARS="$ENV_VARS|GEMINI_API_KEY=$GEMINI_API_KEY"

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$GCP_LOCATION" \
  --project "$GCP_PROJECT" \
  --allow-unauthenticated \
  --update-env-vars "$ENV_VARS" \
  --memory 1Gi \
  --cpu 1 \
  --quiet

# ── Fetch URL & print ──────────────────────────────────────────────────────
WEB_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$GCP_LOCATION" \
  --project "$GCP_PROJECT" \
  --format='value(status.url)' 2>/dev/null || true)

echo ""
if [[ -n "$WEB_URL" ]]; then
  echo "✅ Deployed: $WEB_URL"
  echo ""
  echo "💡 Add to .env.deploy so GEAP redeploy picks it up:"
  echo ""
  echo "    DIGEST_API_URL=$WEB_URL"
  echo ""
  echo "🔗 Verify:"
  echo "    curl $WEB_URL/api/articles | jq ."
else
  echo "⚠️  Deploy completed but could not fetch service URL." >&2
  echo "    Run: gcloud run services describe $SERVICE_NAME --region $GCP_LOCATION --format='value(status.url)'" >&2
fi
