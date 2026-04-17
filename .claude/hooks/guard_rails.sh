#!/bin/bash
# Claude Code PreToolUse hook — protects data/ and src/app.py
# Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}

input=$(cat)
command=$(echo "$input" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except:
    print('')
" 2>/dev/null || echo "")

if echo "$command" | grep -qE "(rm|mv|del|unlink).*(data/|src/app\.py)|data/.*\.(db|sqlite)"; then
  echo '{"decision": "block", "reason": "Protected: data/ directory and src/app.py are guarded by SRE policy"}'
  exit 2
fi

echo '{"decision": "allow"}'
exit 0
