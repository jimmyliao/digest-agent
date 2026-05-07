#!/usr/bin/env bash
# Cloud Shell smoke test — verifies an environment freshly set up by
# scripts/onboard-cloudshell.sh actually boots a working Next.js dev
# server and serves /api/health.
#
# Designed to be runnable from `gcloud cloud-shell ssh --command="..."`
# or as the second half of `make workshop-verify`.
#
# Usage:
#   bash scripts/smoke-cloudshell.sh
#   make smoke-cloudshell
#
# Exit codes:
#   0 — all green
#   1 — pre-flight failed (bun/uv missing, port busy, etc.)
#   2 — dev server failed to come up within timeout
#   3 — /api/health returned non-200 or malformed body

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Pretty output ──────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; BOLD=""; OFF=""
fi
ok()   { echo "${GREEN}✅ $*${OFF}"; }
warn() { echo "${YELLOW}⚠️  $*${OFF}"; }
fail() { echo "${RED}❌ $*${OFF}" >&2; exit "${2:-1}"; }
step() { echo ""; echo "${BOLD}── $* ──${OFF}"; }

# ── Cleanup trap ───────────────────────────────────────────────────────────
WEB_PID=""
cleanup() {
  if [[ -n "$WEB_PID" ]]; then
    kill "$WEB_PID" 2>/dev/null || true
    sleep 1
    lsof -ti:3000 -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# ── Step 1: pre-flight ─────────────────────────────────────────────────────
step "Pre-flight"

# bun: try PATH then ~/.bun/bin (onboarding installs there but new shell
# may not have re-sourced bashrc yet)
if ! command -v bun >/dev/null 2>&1; then
  if [[ -x "$HOME/.bun/bin/bun" ]]; then
    export PATH="$HOME/.bun/bin:$PATH"
    ok "bun found at ~/.bun/bin/bun (PATH adjusted in-script)"
  else
    fail "bun not found — run 'make onboard-cloudshell' first" 1
  fi
fi
ok "bun $(bun --version)"

# uv: similar pattern
if ! command -v uv >/dev/null 2>&1; then
  if [[ -x "$HOME/.local/bin/uv" ]]; then
    export PATH="$HOME/.local/bin:$PATH"
    ok "uv found at ~/.local/bin/uv (PATH adjusted in-script)"
  else
    fail "uv not found — run 'make onboard-cloudshell' first" 1
  fi
fi
ok "uv $(uv --version | awk '{print $2}')"

# Port 3000 must be free
if lsof -ti:3000 -sTCP:LISTEN >/dev/null 2>&1; then
  fail "port 3000 already in use — stop the other process first" 1
fi
ok "port 3000 free"

# bun.lock present (sanity)
[[ -f bun.lock ]] || fail "bun.lock missing — onboarding incomplete" 1
ok "bun.lock present"

# .env.local present (created by onboarding)
[[ -f apps/web/.env.local ]] || warn "apps/web/.env.local missing — health check may use defaults"

# ── Step 2: boot dev server ────────────────────────────────────────────────
step "Boot apps/web dev server in background"

LOG=/tmp/digest-smoke-dev.log
: > "$LOG"
(cd apps/web && bun run dev) > "$LOG" 2>&1 &
WEB_PID=$!
echo "  PID=$WEB_PID, log=$LOG"

# ── Step 3: wait for port 3000 ─────────────────────────────────────────────
step "Wait for port 3000 (max 60s)"
for i in $(seq 1 60); do
  if curl -fs -m 2 -o /dev/null http://localhost:3000/api/health 2>/dev/null; then
    ok "port 3000 responding after ${i}s"
    break
  fi
  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    echo "--- last 30 lines of $LOG ---"
    tail -30 "$LOG"
    fail "dev server died — see log above" 2
  fi
  sleep 1
done
if ! curl -fs -m 2 -o /dev/null http://localhost:3000/api/health 2>/dev/null; then
  echo "--- last 30 lines of $LOG ---"
  tail -30 "$LOG"
  fail "dev server did not respond on /api/health within 60s" 2
fi

# ── Step 4: validate /api/health body ──────────────────────────────────────
step "Validate /api/health response"
HEALTH=$(curl -fs http://localhost:3000/api/health)
echo "  body: $HEALTH"
echo "$HEALTH" | grep -q '"status"' || fail "/api/health body missing 'status' field — got: $HEALTH" 3
echo "$HEALTH" | grep -q 'ok' || fail "/api/health did not report 'ok'" 3
ok "health endpoint OK"

# ── Step 5: validate /api/articles list endpoint ──────────────────────────
step "Validate /api/articles?limit=1"
ART=$(curl -fs "http://localhost:3000/api/articles?limit=1" || echo "")
if echo "$ART" | grep -q '"articles"'; then
  ok "articles endpoint returns shape with 'articles' key"
else
  warn "/api/articles unexpected shape — got: $(echo "$ART" | head -c 200)"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo "${GREEN}${BOLD}  ✅ Cloud Shell smoke test PASSED${OFF}"
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo ""
echo "Next steps:"
echo "  • Web Preview port 3000 → confirm UI loads in browser"
echo "  • For full real-API smoke: 'make test-local-api-real' (needs GEMINI_API_KEY)"
echo "  • For Cloud Run deploy: see WORKSHOP_NEXTJS.md Magic Prompt 4"
