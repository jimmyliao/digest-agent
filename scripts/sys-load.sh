#!/bin/bash
# BeforeModel Hook: 系統資訊注入
# 把即時 CPU 負載注入到 Gemini CLI 的 context metadata 中

echo "🔍 Hook 正在讀取系統負載資訊到 Context..." >&2

# 跨平台：Linux (Cloud Shell) 用 pcpu，macOS 用 %cpu
if [[ "$(uname)" == "Darwin" ]]; then
  STATS=$(ps -Ao %cpu,comm | sort -nr | head -n 5)
else
  STATS=$(ps -Ao pcpu,comm --sort=-pcpu | head -n 6 | tail -n 5)
fi

echo "{\"metadata\": {\"system_realtime_load\": \"$STATS\"}}"
exit 0
