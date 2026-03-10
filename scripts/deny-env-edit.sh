#!/bin/bash
# P9 Hooks Demo: 安全攔截 (BeforeTool)

# 獲取工具呼叫的參數
args="$*"

# 如果參數中包含 .env 且是寫入操作
if [[ "$args" == *".env"* ]]; then
  echo "{\"decision\": \"deny\", \"reason\": \"⚠️ 為了現場展示安全，Hook 攔截了對 .env 的修改指令！\"}"
  exit 1
fi

echo "{\"decision\": \"allow\"}"
exit 0
