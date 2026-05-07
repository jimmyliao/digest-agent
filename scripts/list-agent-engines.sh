#!/usr/bin/env bash
# List Agent Engines (Reasoning Engines) deployed to your GCP project.
#
# Usage:
#   ./scripts/list-agent-engines.sh                          # all
#   ./scripts/list-agent-engines.sh --filter digest-agent    # filter by display_name prefix
#   ./scripts/list-agent-engines.sh --filter digest-agent --require-unique  # exit 1 if !=1
#   ./scripts/list-agent-engines.sh --filter digest-agent --sync   # append matched into registry
#   ./scripts/list-agent-engines.sh --json                   # JSON output
#
# Reads GCP_PROJECT / GCP_LOCATION from .env.deploy / .env (same loader as deploy.sh).

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

exec uv run python -m agents.stock.list_agent_engines "$@"
