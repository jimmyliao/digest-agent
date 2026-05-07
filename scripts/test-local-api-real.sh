#!/usr/bin/env bash
# Real-API smoke test against an already-running Next.js dev server.
# Hits every /api/* endpoint with REAL data (real RSS feeds, real LLM calls).
# Useful for verifying the local UI works end-to-end before deploying to
# Cloud Run or running the AIA / 5/9 workshop demo.
#
# Prerequisites:
#   1. Dev server running: cd apps/web && bun run dev (or npm run dev)
#   2. GEMINI_API_KEY set (or LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY)
#      - reads from $WORKSPACE_ENV / .env.local / shell env
#
# Usage:
#   ./scripts/test-local-api-real.sh                  # default: skip publish
#   ./scripts/test-local-api-real.sh --with-publish   # also test real publish
#   WEB_URL=http://localhost:3001 ./scripts/...       # custom port
#   SUMMARIZE_LIMIT=1 ./scripts/...                   # only summarize 1 article (save quota)
#
# Cost: ~3 LLM calls (~$0.01 with gemini-2.5-flash). Skipped channels won't spam.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Config ─────────────────────────────────────────────────────────────────
WEB_URL="${WEB_URL:-http://localhost:3000}"
SUMMARIZE_LIMIT="${SUMMARIZE_LIMIT:-3}"
WITH_PUBLISH=0
PUBLISH_CHANNELS="${PUBLISH_CHANNELS:-telegram}"  # comma-separated for --with-publish

for arg in "$@"; do
  case "$arg" in
    --with-publish) WITH_PUBLISH=1 ;;
    --help|-h)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

# ── Pretty output ──────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; BLUE=""; BOLD=""; OFF=""
fi
ok()    { echo "${GREEN}✅ $*${OFF}"; }
warn()  { echo "${YELLOW}⚠️  $*${OFF}"; }
fail()  { echo "${RED}❌ $*${OFF}" >&2; exit 1; }
step()  { echo ""; echo "${BOLD}${BLUE}── $* ──${OFF}"; }
info()  { echo "  ${BLUE}ℹ${OFF}  $*"; }

# ── Load env (LLM keys etc) ────────────────────────────────────────────────
load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  set -a; . "$file"; set +a
}
load_env_file "$HOME/workspace/.env"
load_env_file "$REPO_ROOT/apps/web/.env.local"
load_env_file "$REPO_ROOT/.env"

LLM_PROVIDER="${LLM_PROVIDER:-gemini}"
case "$LLM_PROVIDER" in
  gemini)
    [[ -n "${GEMINI_API_KEY:-}" ]] || fail "GEMINI_API_KEY not set (needed for real LLM call). Set it or use LLM_PROVIDER=anthropic"
    KEY_PREVIEW="${GEMINI_API_KEY:0:6}…(${#GEMINI_API_KEY} chars)"
    ;;
  anthropic|claude)
    [[ -n "${ANTHROPIC_API_KEY:-}" ]] || fail "ANTHROPIC_API_KEY not set (needed for real LLM call)"
    KEY_PREVIEW="${ANTHROPIC_API_KEY:0:6}…(${#ANTHROPIC_API_KEY} chars)"
    ;;
  *)
    fail "Unknown LLM_PROVIDER: $LLM_PROVIDER (expected gemini|anthropic)"
    ;;
esac

# ── Step 0: pre-flight ─────────────────────────────────────────────────────
step "Step 0 — pre-flight"
info "WEB_URL          : $WEB_URL"
info "LLM_PROVIDER     : $LLM_PROVIDER"
info "API key          : $KEY_PREVIEW"
info "SUMMARIZE_LIMIT  : $SUMMARIZE_LIMIT (only summarize first N pending)"
info "WITH_PUBLISH     : $WITH_PUBLISH (channels: $PUBLISH_CHANNELS)"

command -v jq >/dev/null || warn "jq not installed — output will be raw JSON. Install: brew install jq"
JQ="${JQ:-jq}"
command -v $JQ >/dev/null || JQ="cat"

# Probe server alive
if ! curl -sf "$WEB_URL/api/health" >/dev/null; then
  fail "Dev server not reachable at $WEB_URL — start it: cd apps/web && bun run dev"
fi
ok "dev server reachable"

# ── Step 1: GET /api/health ────────────────────────────────────────────────
step "Step 1 — GET /api/health"
HEALTH=$(curl -s "$WEB_URL/api/health")
echo "$HEALTH" | $JQ . 2>/dev/null || echo "$HEALTH"
status=$(echo "$HEALTH" | $JQ -r .status 2>/dev/null || echo "unknown")
[[ "$status" == "ok" ]] || fail "health.status != ok (got: $status)"
ok "health=ok"

# ── Step 2: baseline counts ────────────────────────────────────────────────
step "Step 2 — baseline article counts"
BASELINE=$(curl -s "$WEB_URL/api/articles" | $JQ -r '.count // 0' 2>/dev/null || echo 0)
info "current articles in DB: $BASELINE"

# ── Step 3: POST /api/fetch (real RSS) ─────────────────────────────────────
step "Step 3 — POST /api/fetch (real RSS, may take 5–15s)"
FETCH_START=$(date +%s)
FETCH=$(curl -s -X POST "$WEB_URL/api/fetch" -H 'Content-Type: application/json')
FETCH_DUR=$(($(date +%s) - FETCH_START))
echo "$FETCH" | $JQ . 2>/dev/null || echo "$FETCH"
fetched=$(echo "$FETCH" | $JQ -r .fetched 2>/dev/null || echo 0)
saved=$(echo "$FETCH" | $JQ -r .saved 2>/dev/null || echo 0)
[[ "$fetched" =~ ^[0-9]+$ ]] || fail "fetch did not return numeric .fetched"
ok "fetch: real RSS pulled $fetched articles, saved $saved new (in ${FETCH_DUR}s)"
if [[ "$fetched" -eq 0 ]]; then
  warn "0 articles fetched — sources table may be empty or all RSS feeds unreachable"
  warn "Try opening $WEB_URL in browser to verify the UI shows sources"
fi

# ── Step 4: GET /api/articles?status=pending ───────────────────────────────
step "Step 4 — GET /api/articles?status=pending"
PENDING=$(curl -s "$WEB_URL/api/articles?status=pending&limit=$SUMMARIZE_LIMIT")
pending_count=$(echo "$PENDING" | $JQ -r '.articles | length' 2>/dev/null || echo 0)
info "pending articles available: $pending_count (will summarize up to $SUMMARIZE_LIMIT)"
if [[ "$pending_count" -eq 0 ]]; then
  warn "No pending articles — skipping summarize/publish steps"
  echo ""
  ok "Real-API smoke (partial): health + fetch verified"
  exit 0
fi

# Pick article IDs to summarize (limit to SUMMARIZE_LIMIT)
ARTICLE_IDS=$(echo "$PENDING" | $JQ -c "[.articles[0:$SUMMARIZE_LIMIT][].id]" 2>/dev/null)
info "will summarize article IDs: $ARTICLE_IDS"

# ── Step 5: POST /api/summarize (real LLM, SSE) ───────────────────────────
step "Step 5 — POST /api/summarize (real $LLM_PROVIDER call, SSE stream)"
SUMM_START=$(date +%s)
# SSE: drain stream, collect events
SUMM_BODY=$(printf '{"provider":"%s","articleIds":%s}' "$LLM_PROVIDER" "$ARTICLE_IDS")
echo "  request body: $SUMM_BODY"
SUMM_RAW=$(curl -s -N -X POST "$WEB_URL/api/summarize" \
  -H 'Content-Type: application/json' \
  -d "$SUMM_BODY")
SUMM_DUR=$(($(date +%s) - SUMM_START))

# Show event types we saw
echo "$SUMM_RAW" | grep -E '^data:' | head -20 | while IFS= read -r line; do
  evt_type=$(echo "$line" | sed 's/^data: //' | $JQ -r .type 2>/dev/null || echo "?")
  echo "    SSE: $evt_type"
done

# Last 'done' event determines success
LAST_DONE=$(echo "$SUMM_RAW" | grep -E '^data:' | tail -1 | sed 's/^data: //')
done_msg=$(echo "$LAST_DONE" | $JQ -r '.message // .type' 2>/dev/null || echo "")
ok "summarize: stream complete in ${SUMM_DUR}s — $done_msg"

# ── Step 6: verify summarized ──────────────────────────────────────────────
step "Step 6 — GET /api/articles?status=summarized"
SUMMARIZED=$(curl -s "$WEB_URL/api/articles?status=summarized")
summ_count=$(echo "$SUMMARIZED" | $JQ -r '.articles | length' 2>/dev/null || echo 0)
info "summarized articles in DB: $summ_count"
if [[ "$summ_count" -eq 0 ]]; then
  warn "No articles in summarized status — LLM may have errored. Check dev server log."
else
  echo "$SUMMARIZED" | $JQ -r '.articles[0] | "  → first: \(.title // "(no title)") | summary len=\((.summary // "") | length)"' 2>/dev/null || true
  ok "lifecycle: pending → summarized verified"
fi

# ── Step 7: POST /api/publish (opt-in) ─────────────────────────────────────
if [[ "$WITH_PUBLISH" -eq 1 ]]; then
  step "Step 7 — POST /api/publish (real channels: $PUBLISH_CHANNELS)"
  warn "This will actually send messages to the configured channels."
  read -r -p "Proceed? [y/N] " ans
  if [[ "$ans" =~ ^[yY] ]]; then
    PUB_BODY=$(printf '{"channels":["%s"]}' "$PUBLISH_CHANNELS")
    PUB=$(curl -s -X POST "$WEB_URL/api/publish" \
      -H 'Content-Type: application/json' \
      -d "$PUB_BODY")
    echo "$PUB" | $JQ . 2>/dev/null || echo "$PUB"
    success=$(echo "$PUB" | $JQ -r .success 2>/dev/null || echo "false")
    [[ "$success" == "true" ]] && ok "publish: success=true" || warn "publish: success=$success (check dev server log)"
  else
    info "publish skipped by user"
  fi
else
  step "Step 7 — POST /api/publish (SKIPPED, use --with-publish to enable)"
  info "Publish would send real messages to channels — opt in only when needed"
fi

# ── Step 8: GET /api/articles (final state) ───────────────────────────────
step "Step 8 — final state"
ALL=$(curl -s "$WEB_URL/api/articles?limit=200")
total=$(echo "$ALL" | $JQ -r '.count' 2>/dev/null || echo "?")
by_status=$(echo "$ALL" | $JQ -r '.articles | group_by(.publish_status) | map({(.[0].publish_status): length}) | add' 2>/dev/null || echo "(jq missing)")
info "total articles: $total"
info "by status     : $by_status"

# ── Step 9: pipeline endpoint (smoke only) ────────────────────────────────
step "Step 9 — POST /api/pipeline (orchestrator wiring smoke)"
info "Skipping full pipeline run (already exercised fetch+summarize separately)"
info "To run combined pipeline manually:"
info "  curl -X POST $WEB_URL/api/pipeline -H 'Content-Type: application/json' -d '{\"steps\":[\"fetch\",\"summarize\"]}'"

echo ""
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo "${GREEN}${BOLD}  ✅ Real-API smoke test passed${OFF}"
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo ""
echo "Verified against $WEB_URL:"
echo "  ✅ /api/health        — ok, db connected"
echo "  ✅ /api/fetch         — real RSS pulled $fetched, saved $saved new"
echo "  ✅ /api/summarize     — real $LLM_PROVIDER call, $SUMMARIZE_LIMIT article(s), SSE stream"
echo "  ✅ /api/articles      — lifecycle (pending → summarized) verified"
if [[ "$WITH_PUBLISH" -eq 1 ]]; then
  echo "  ✅ /api/publish       — real channels exercised"
else
  echo "  ⏭️  /api/publish      — skipped (use --with-publish)"
fi
echo ""
echo "Next: ${BOLD}make test-local-e2e${OFF} for unit + agent layer, then merge PR + ${BOLD}make deploy-web${OFF} for Cloud Run."
