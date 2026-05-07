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

# Pre-check ADC quota project (else invoke fails with RESOURCE_PROJECT_INVALID at SessionService)
if [[ -n "${GCP_PROJECT:-}" ]]; then
  adc_qp=$(python3 -c "import json,sys,os; p=os.path.expanduser('~/.config/gcloud/application_default_credentials.json'); print(json.load(open(p)).get('quota_project_id','')) if os.path.exists(p) else print('')" 2>/dev/null)
  if [[ -n "$adc_qp" ]] && [[ "$adc_qp" != "$GCP_PROJECT" ]]; then
    echo "❌ ADC quota project ($adc_qp) ≠ GCP_PROJECT ($GCP_PROJECT)" >&2
    echo "   → invoke will fail with RESOURCE_PROJECT_INVALID at SessionService" >&2
    echo "   → Fix: gcloud auth application-default set-quota-project $GCP_PROJECT" >&2
    exit 1
  fi
fi

exec uv run python -m agents.stock.invoke_agent_engine "$@"
