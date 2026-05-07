#!/usr/bin/env bash
# Invoke a deployed Agent Engine reasoning engine.
#
# Usage:
#   ./scripts/invoke-agent-engine.sh                                 # latest deploy + default msg
#   ./scripts/invoke-agent-engine.sh "鴻海營運分析"                   # latest deploy + custom msg
#   ./scripts/invoke-agent-engine.sh projects/.../reasoningEngines/N "msg"  # specific deploy
#
# Reads:
#   - deployed-agent-engines.txt  (gitignored, written by deploy script)
#   - .env.deploy / .env          (for GCP_PROJECT, GCP_LOCATION)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Inline env loader (matches scripts/deploy-to-agent-engine.sh logic)
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

exec uv run python -m agents.stock.invoke_agent_engine "$@"
