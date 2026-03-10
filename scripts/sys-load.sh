#!/bin/bash
# P10 Hooks Demo: 系統資訊注入 (BeforeModel)

echo "🔍 Hook 正在讀取系統負載資訊到 Context..." >&2

# 抓取 CPU 負載前 5 名 (Mac 版指令)
STATS=$(ps -Ao %cpu,comm | sort -nr | head -n 5)

# 將資訊注入到 metadata 中
echo "{\"metadata\": {\"system_realtime_load\": \"$STATS\"}}"
exit 0
