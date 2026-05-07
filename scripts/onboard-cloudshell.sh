#!/usr/bin/env bash
# One-shot onboarding for Google Cloud Shell (and other fresh dev machines).
# Idempotent: re-runnable, skips anything already installed.
#
# Installs / verifies:
#   - bun                (Next.js apps/web/ uses bun.lock + workspace:* protocol)
#   - uv                 (Python parts: agents/, src/, tests/)
#   - Node 20+           (warns if older — Cloud Shell currently ships 22+)
#   - gcloud             (Cloud Shell has it; warn if missing on other machines)
#
# Usage:
#   bash scripts/onboard-cloudshell.sh
#   make onboard-cloudshell        # equivalent
#
# After this, run:
#   bun install              # install Next.js workspace deps from root
#   uv sync --all-extras     # install Python deps (Streamlit + agents)
#   cp apps/web/.env.example apps/web/.env.local  # then edit

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Pretty output ──────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  GREEN=$'\033[32m'; YELLOW=$'\033[33m'; BLUE=$'\033[34m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
else
  GREEN=""; YELLOW=""; BLUE=""; BOLD=""; OFF=""
fi
ok()    { echo "${GREEN}✅ $*${OFF}"; }
warn()  { echo "${YELLOW}⚠️  $*${OFF}"; }
step()  { echo ""; echo "${BOLD}${BLUE}── $* ──${OFF}"; }

step "Detect environment"
if [[ -n "${CLOUD_SHELL:-}" ]] || [[ "${USER:-}" == "cloudshell-user" ]] || [[ -d /google/devshell ]]; then
  ENV_LABEL="Google Cloud Shell"
elif [[ "$(uname)" == "Darwin" ]]; then
  ENV_LABEL="macOS"
elif grep -qi microsoft /proc/version 2>/dev/null; then
  ENV_LABEL="WSL"
else
  ENV_LABEL="Linux"
fi
echo "  Detected: $ENV_LABEL"
echo "  Shell:    $SHELL"
echo "  PWD:      $REPO_ROOT"

# ── 1. Node ────────────────────────────────────────────────────────────────
step "Node.js"
if command -v node >/dev/null 2>&1; then
  NODE_VER=$(node --version)
  NODE_MAJOR=${NODE_VER#v}
  NODE_MAJOR=${NODE_MAJOR%%.*}
  echo "  Found: $NODE_VER"
  if [[ "$NODE_MAJOR" -lt 20 ]]; then
    warn "Node ${NODE_VER} is older than the Next.js 15 minimum (v20)."
    warn "Cloud Shell typically ships v22+. On older machines: nvm install 20"
  else
    ok "Node $NODE_VER (>=20)"
  fi
else
  warn "Node not found."
  if [[ "$ENV_LABEL" == "Google Cloud Shell" ]]; then
    warn "Cloud Shell normally pre-installs Node — try restarting the VM (⋮ → Restart)."
  else
    warn "Install Node 20+: https://nodejs.org/  (or use nvm)"
  fi
fi

# ── 2. Bun ─────────────────────────────────────────────────────────────────
step "Bun (Next.js workspace package manager)"
# Re-source ~/.bashrc style PATH if bun is in $HOME/.bun but not yet on PATH
[[ -d "$HOME/.bun/bin" && ":$PATH:" != *":$HOME/.bun/bin:"* ]] && export PATH="$HOME/.bun/bin:$PATH"

if command -v bun >/dev/null 2>&1; then
  ok "Bun $(bun --version) already installed"
else
  echo "  Installing bun via official installer..."
  if ! command -v curl >/dev/null 2>&1; then
    warn "curl missing — install with: sudo apt-get install -y curl"
    exit 1
  fi
  curl -fsSL https://bun.sh/install | bash
  export PATH="$HOME/.bun/bin:$PATH"
  if command -v bun >/dev/null 2>&1; then
    ok "Bun $(bun --version) installed at $HOME/.bun/bin/bun"
    echo "  → New shells will pick up bun from ~/.bashrc automatically."
    echo "  → For THIS shell, export already done in-script."
  else
    warn "bun install completed but binary not on PATH. Run:"
    echo "    export PATH=\"\$HOME/.bun/bin:\$PATH\""
    echo "    source ~/.bashrc"
    exit 1
  fi
fi

# ── 3. uv (Python) ─────────────────────────────────────────────────────────
step "uv (Python package manager)"
if command -v uv >/dev/null 2>&1; then
  ok "uv $(uv --version | awk '{print $2}') already installed"
else
  echo "  Installing uv via official installer..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # uv installer writes to ~/.local/bin; source the env file it provides
  [[ -f "$HOME/.local/bin/env" ]] && . "$HOME/.local/bin/env"
  [[ -d "$HOME/.local/bin" && ":$PATH:" != *":$HOME/.local/bin:"* ]] && export PATH="$HOME/.local/bin:$PATH"
  if command -v uv >/dev/null 2>&1; then
    ok "uv $(uv --version | awk '{print $2}') installed"
  else
    warn "uv installed but not on PATH. Run: source ~/.bashrc"
  fi
fi

# ── 4. gcloud ──────────────────────────────────────────────────────────────
step "gcloud SDK"
if command -v gcloud >/dev/null 2>&1; then
  ok "gcloud $(gcloud --version 2>/dev/null | head -1 | awk '{print $4}')"
  if [[ "$ENV_LABEL" != "Google Cloud Shell" ]]; then
    if gcloud auth print-access-token >/dev/null 2>&1; then
      ok "Logged in: $(gcloud config get account 2>/dev/null)"
    else
      warn "Not logged in. Run: gcloud auth login && gcloud auth application-default login"
    fi
  fi
else
  warn "gcloud not installed."
  if [[ "$ENV_LABEL" == "Google Cloud Shell" ]]; then
    warn "(Unexpected for Cloud Shell — try restarting the VM)"
  else
    warn "Install: https://cloud.google.com/sdk/docs/install"
  fi
fi

# ── 5. Repo deps install ───────────────────────────────────────────────────
step "Install workspace deps (bun install)"
if [[ -f bun.lock ]]; then
  bun install --frozen-lockfile 2>&1 | tail -3
  ok "Next.js workspace deps installed"
else
  warn "bun.lock missing at repo root — skipping bun install"
fi

step "Install Python deps (uv sync --all-extras)"
if command -v uv >/dev/null 2>&1 && [[ -f pyproject.toml ]]; then
  uv sync --all-extras 2>&1 | tail -3
  ok "Python deps installed"
else
  warn "uv or pyproject.toml missing — skipping uv sync"
fi

# ── 6. Env scaffolding ─────────────────────────────────────────────────────
step "Env file scaffolding"
if [[ ! -f apps/web/.env.local ]] && [[ -f apps/web/.env.example ]]; then
  cp apps/web/.env.example apps/web/.env.local
  echo "BASIC_AUTH_DISABLED=1" >> apps/web/.env.local
  ok "Created apps/web/.env.local from template (BASIC_AUTH disabled for dev)"
  warn "→ Edit apps/web/.env.local: set GEMINI_API_KEY (and optionally GEAP_RESOURCE_NAME)"
else
  ok "apps/web/.env.local already exists (not overwriting)"
fi

if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp .env.example .env
  ok "Created .env from template (Streamlit / agents path)"
fi

# ── 7. Summary ─────────────────────────────────────────────────────────────
echo ""
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo "${GREEN}${BOLD}  ✅ Onboarding complete on $ENV_LABEL${OFF}"
echo "${GREEN}${BOLD}════════════════════════════════════════${OFF}"
echo ""
echo "Quick start:"
echo ""
echo "  ${BOLD}Next.js path (Cloud Run target)${OFF}:"
echo "    cd apps/web && bun run dev"
echo "    open http://localhost:3000"
echo ""
echo "  ${BOLD}Streamlit path (5/9 workshop)${OFF}:"
echo "    make dev-shell      # Cloud Shell (port 8080 + Web Preview)"
echo "    make dev            # Local (loads .env)"
echo ""
echo "  ${BOLD}Test all (no GCS / no LLM key needed)${OFF}:"
echo "    make test-local-e2e"
echo ""
echo "Env files to edit:"
echo "  - apps/web/.env.local        # GEMINI_API_KEY, GEAP_RESOURCE_NAME, etc."
echo "  - .env                       # Streamlit / agents (GEMINI_API_KEY)"
echo "  - .env.deploy (gitignored)   # Cloud Run / GEAP deploy"
echo ""
echo "Need a GEMINI_API_KEY? https://aistudio.google.com/app/apikey"
