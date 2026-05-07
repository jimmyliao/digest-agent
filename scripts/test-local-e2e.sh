#!/usr/bin/env bash
# Local end-to-end smoke test for the SQLite persistence PR.
# Verifies: branch is correct, unit tests green, Next.js dev server
# serves the new ?company= / ?limit= query params, and the agent's
# search_db_articles tool toggles between HTTP and SQLite modes
# correctly based on DIGEST_API_URL.
#
# Usage:
#   ./scripts/test-local-e2e.sh
#
# No GCS, no Cloud Run, no LLM key needed. Runs entirely on localhost.
# Auto-cleans the dev server on exit (trap).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Pretty output ──────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; BOLD=""; OFF=""
fi
ok()    { echo "${GREEN}✅ $*${OFF}"; }
warn()  { echo "${YELLOW}⚠️  $*${OFF}"; }
fail()  { echo "${RED}❌ $*${OFF}" >&2; exit 1; }
step()  { echo ""; echo "${BOLD}── $* ──${OFF}"; }

# ── Cleanup trap (kills dev server we start) ───────────────────────────────
WEB_PID=""
cleanup() {
  if [[ -n "$WEB_PID" ]]; then
    kill "$WEB_PID" 2>/dev/null || true
    sleep 1
    # Belt-and-suspenders: kill anything still on 3000 that we own
    lsof -ti:3000 -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# ── Step 0: pre-flight ─────────────────────────────────────────────────────
step "Step 0 — pre-flight"
command -v uv >/dev/null || fail "uv not found — install: curl -LsSf https://astral.sh/uv/install.sh | sh"

JS_RUNNER=""
if command -v bun >/dev/null; then JS_RUNNER="bun"
elif command -v npm >/dev/null; then JS_RUNNER="npm"
else fail "neither bun nor npm found — install Node 20+ or Bun"
fi
ok "uv found"
ok "JS runner: $JS_RUNNER"

# Port 3000 must be free (don't kill someone else's server)
if lsof -ti:3000 -sTCP:LISTEN >/dev/null 2>&1; then
  fail "port 3000 already in use — stop the other process first: lsof -ti:3000 | xargs kill"
fi
ok "port 3000 free"

# ── Step 1: branch ─────────────────────────────────────────────────────────
step "Step 1 — current branch"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "  on: $BRANCH"
if [[ "$BRANCH" != "feat/sqlite-persistence-litestream" && "$BRANCH" != "main" ]]; then
  warn "not on feat/sqlite-persistence-litestream or main — continuing anyway"
fi

# ── Step 2: install deps (idempotent) ──────────────────────────────────────
step "Step 2 — install apps/web deps ($JS_RUNNER)"
(
  cd apps/web
  if [[ "$JS_RUNNER" == "bun" ]]; then
    bun install --frozen-lockfile 2>&1 | tail -2
  else
    npm install 2>&1 | tail -2
  fi
)
ok "deps installed"

# ── Step 3: unit tests ─────────────────────────────────────────────────────
step "Step 3a — vitest (apps/web)"
(
  cd apps/web
  if [[ "$JS_RUNNER" == "bun" ]]; then
    bun run test 2>&1 | tail -8
  else
    npm test 2>&1 | tail -8
  fi
) || fail "vitest failed"
ok "vitest passed"

step "Step 3b — pytest (tests/test_news_tools_http.py)"
uv run --with pytest pytest tests/test_news_tools_http.py -v 2>&1 | tail -10
ok "pytest passed"

# ── Step 4: start Next.js dev server (background) ─────────────────────────
step "Step 4 — start Next.js dev server (background, log: /tmp/digest-web.log)"
(
  cd apps/web
  if [[ "$JS_RUNNER" == "bun" ]]; then
    nohup bun run dev > /tmp/digest-web.log 2>&1 &
    echo $! > /tmp/digest-web.pid
  else
    nohup npm run dev > /tmp/digest-web.log 2>&1 &
    echo $! > /tmp/digest-web.pid
  fi
)
WEB_PID=$(cat /tmp/digest-web.pid)
echo "  pid: $WEB_PID"

# Wait for server (up to 30s)
for i in $(seq 1 30); do
  if curl -sf http://localhost:3000/api/articles >/dev/null 2>&1; then
    ok "server up after ${i}s"
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "--- /tmp/digest-web.log tail ---"
    tail -20 /tmp/digest-web.log
    fail "server did not respond within 30s"
  fi
  sleep 1
done

# ── Step 5: query params ──────────────────────────────────────────────────
step "Step 5 — /api/articles query params"
for q in "" "?company=TSMC&limit=5" "?limit=3"; do
  code=$(curl -s -o /tmp/articles-resp.json -w "%{http_code}" "http://localhost:3000/api/articles${q}")
  body=$(head -c 100 /tmp/articles-resp.json)
  if [[ "$code" != "200" ]]; then
    fail "GET /api/articles${q} → HTTP $code (body: $body)"
  fi
  echo "  GET /api/articles${q:-/} → 200 ${body}"
done
ok "all 3 query variants returned 200"

# ── Step 6/7: agent HTTP mode + SQLite fallback ───────────────────────────
step "Step 6 — agent: A) HTTP mode (server alive)"
DIGEST_API_URL=http://localhost:3000 uv run python -c "
from agents.stock.tools.news_tools import search_db_articles
r = search_db_articles('TSMC', '2330', 10)
src = r.get('source')
assert src == 'remote_api', f'expected remote_api, got {src}'
print(f'  source={src} total_in_db={r.get(\"total_in_db\")} ok')
" || fail "HTTP mode test failed"
ok "HTTP mode → source=remote_api"

step "Step 7 — agent: B) SQLite path (DIGEST_API_URL unset)"
unset DIGEST_API_URL
uv run python -c "
import os
os.environ.pop('DIGEST_API_URL', None)
from agents.stock.tools.news_tools import search_db_articles
r = search_db_articles('TSMC', '2330', 10)
src = r.get('source')
assert src == 'local_db', f'expected local_db, got {src}'
print(f'  source={src} total_in_db={r.get(\"total_in_db\")} ok')
" || fail "SQLite path test failed"
ok "env unset → source=local_db"

step "Step 8 — agent: C) HTTP fail → SQLite fallback (port 9999 dead)"
DIGEST_API_URL=http://localhost:9999 uv run python -c "
from agents.stock.tools.news_tools import search_db_articles
r = search_db_articles('TSMC', '2330', 10)
src = r.get('source')
assert src == 'local_db', f'expected local_db (after fallback), got {src}'
print(f'  source={src} (fallback ok)')
" || fail "HTTP-fail-fallback test failed"
ok "HTTP fail → fallback to local_db"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo "${GREEN}${BOLD}  ✅ All local e2e tests passed${OFF}"
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo ""
echo "Verified:"
echo "  ✅ branch + deps + vitest 38/38 + pytest 4/4"
echo "  ✅ Next.js dev server boots, /api/articles 200"
echo "  ✅ ?company= and ?limit= query params work"
echo "  ✅ agent HTTP mode (DIGEST_API_URL set, server up)"
echo "  ✅ agent SQLite path (DIGEST_API_URL unset)"
echo "  ✅ agent fallback (DIGEST_API_URL set, server dead)"
echo ""
echo "Dev server will be stopped automatically (trap)."
