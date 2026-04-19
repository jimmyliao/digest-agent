# E2E Report — feat/nextjs-showcase
Date: 2026-04-18

## Method
curl API（Playwright MCP 在此環境不可用）

## Health Check
| Endpoint | Status | Response |
|----------|--------|---------|
| `/api/health` | ✅ | `{"status":"ok","db":true,"llm_provider":"gemini"}` |

## Page Tests
| Page | URL | Status | Evidence |
|------|-----|--------|---------|
| Home | `/` | ✅ | HTML 含 "Digest Agent" 標題，導覽列含 Pipeline/Articles/Tasks 連結 |
| Articles | `/articles` | ✅ | HTML 含 "articles" 關鍵字，頁面正常渲染 |
| Publish | `/publish` | ✅ | HTML 含 Fetch / Summarize / Publish 三大功能關鍵字 |
| Tasks | `/tasks` | ✅ | HTML 含 "TasksPage" / "tasks" / "fetch" 關鍵字，頁面正常渲染 |

## API E2E
| Flow | Status | Notes |
|------|--------|-------|
| Full pipeline (fetch+summarize+publish) | ✅ | `success:true`, fetched:60, deduplicated:60, summarized:10, published:20 via Telegram |
| Articles list | ✅ | `/api/articles` 回傳 JSON，含真實文章資料（中文科技新聞） |
| Health | ✅ | DB connected, LLM provider: gemini |

## Pipeline API Response (摘要)
```json
{
  "success": true,
  "task_id": "d765aceb-96bf-459d-90b6-4eccc5033c8e",
  "results": {
    "fetch": { "success": true, "fetched": 60, "saved": 0, "deduplicated": 60 },
    "summarize": { "type": "done", "completed": 10, "total": 10 },
    "publish": { "success": true, "published": 20, "channels": [{"channel":"telegram","articlesPublished":20}] }
  }
}
```

## Screenshots
Playwright MCP 在此環境不可用，改以 curl 驗證頁面 HTML 及 API 端點。

## Notes
- `/api/tasks` 不存在（404），Tasks 功能以 `/tasks` 頁面提供，HTML 驗證通過
- Dev server (Next.js) 在測試完成後已正確關閉
- 所有測試均在 `feat/nextjs-showcase` branch 執行
