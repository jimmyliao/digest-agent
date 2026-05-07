# Next.js Workshop — Magic Prompts for Gemini CLI on Google Cloud Shell

Companion to `CLOUD_SHELL_WORKSHOP.md` (which targets the **Streamlit** path).
This file is the **Next.js (TypeScript)** path students follow when the
workshop track is the Cloud Run UI + Litestream + GEAP showcase.

> 5/9 workshop default = Streamlit. This Next.js track is **stretch / advanced**
> for students who finished early or want the production-style demo.

## Pre-requisite

Open Google Cloud Shell, then:

```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
gemini --version                   # confirm Gemini CLI available (Cloud Shell has it pre-installed)
# Cloud Shell auto-authenticates the `gemini` CLI via your logged-in Google
# account on first use — no manual `auth login` needed. If a prompt appears,
# follow it; otherwise just continue.

# Get a free Gemini API key at: https://aistudio.google.com/app/apikey
# (separate from the CLI auth — the *app* needs this for Gemini API calls)
export GEMINI_API_KEY=AIza...
echo 'export GEMINI_API_KEY=AIza...' >> ~/.bashrc
```

---

## Magic Prompt 0 — One-command verify ⭐ 推薦第一次跑這個

這把 Magic Prompts 1 + 2 包成 `make workshop-verify` 一個指令。如果只想知道
「這台 Cloud Shell 環境跑得起來嗎？」就跑這個。

```bash
gemini -p "@GEMINI.md 我在 Google Cloud Shell。請幫我跑 make workshop-verify，
過程會：
1. 安裝 bun + uv（已裝會跳過）
2. bun install + uv sync 把所有依賴裝好
3. scaffold apps/web/.env.local（含 BASIC_AUTH_DISABLED=1）
4. 在 background 起 apps/web dev server
5. 等 port 3000 起來後 curl /api/health 確認 200
6. 自動關掉 dev server，印 PASS/FAIL

跑完告訴我：bun 版本、uv 版本、health endpoint 回傳、是否全部 ✅"
```

**預期結果**：終端最後印
```
✅ Cloud Shell smoke test PASSED
🎉 Workshop environment verified end-to-end.
   onboard ✅   smoke ✅
```

失敗時就跑下面 Magic Prompts 1–3 拆步驟 debug。

---

## Magic Prompt 1 — Onboarding only (install bun + uv + deps)

只想裝環境、不要跑 smoke 用這個（例如要先手動填 GEMINI_API_KEY）。

```bash
gemini -p "@GEMINI.md 我在 Google Cloud Shell。請幫我：
1. 跑 make onboard-cloudshell
2. 確認 bun --version 和 uv --version 都有版號（沒有就提醒重 source ~/.bashrc）
3. 確認 apps/web/.env.local 已建立、且預設帶有 BASIC_AUTH_DISABLED=1
4. 把 GEMINI_API_KEY 寫進 apps/web/.env.local 的 GEMINI_API_KEY= 欄位
5. 印出後續可以跑的兩個下一步指令（dev server + Cloud Run deploy）
"
```

**預期結果**：
- bun 和 uv 都安裝完，可直接呼叫
- `bun install` 跑完（Next.js workspace 依賴 ~880 packages）
- `uv sync --all-extras` 跑完（Streamlit + agents Python 依賴）
- `apps/web/.env.local` 已 scaffold，`GEMINI_API_KEY` 寫入

---

## Magic Prompt 2 — Local dev (Next.js Web Preview port 3000)

```bash
gemini -p "@GEMINI.md 我已經跑完 onboarding，apps/web/.env.local 也設好 GEMINI_API_KEY。
請幫我：
1. 確認 port 3000 沒被佔（lsof -ti:3000 | xargs kill 2>/dev/null）
2. 在背景跑：cd apps/web && nohup bun run dev > /tmp/digest-web.log 2>&1 &
3. sleep 5 後 curl http://localhost:3000/api/health 確認 200
4. 失敗的話 tail -30 /tmp/digest-web.log 找原因
5. 成功就告訴我點 Cloud Shell 右上角 Web Preview → 改 port 3000 → 看 Pipeline 頁
"
```

**預期結果**：
- Next.js dev server 跑在 port 3000
- `/api/health` 回 `{"status":"ok","db":true,...}`
- Web Preview 開啟 → 看到 Digest Agent 首頁（4 個 nav: Pipeline / Articles / Tasks / Stock）

---

## Magic Prompt 3 — Run the pipeline real-API smoke

```bash
gemini -p "@GEMINI.md Next.js dev 已在 port 3000 跑。
請幫我跑 make test-local-api-real（這會打真實 RSS + 真實 Gemini summarize ~3 篇）：
1. 先驗 dev server 還在（curl /api/health）
2. 跑 make test-local-api-real
3. 印出最後的 ✅ 統計（fetched / saved / summarized）
4. 任何失敗都把 stderr 跟 dev server log /tmp/digest-web.log 一起印
"
```

**預期**：~30-60 秒跑完，看到：
```
✅ /api/health        — ok, db connected
✅ /api/fetch         — real RSS pulled N, saved M new
✅ /api/summarize     — real gemini call, 3 article(s), SSE stream
✅ /api/articles      — lifecycle (pending → summarized) verified
```

---

## Magic Prompt 4 — Deploy to Cloud Run (production-grade UI)

> **要先有 GCP project + billing 啟用**。Workshop 學員可用 trial credit。

```bash
gemini -p "@GEMINI.md 請幫我把 apps/web/ deploy 到 Cloud Run。已知：
- 我的 GCP_PROJECT=YOUR_PROJECT_ID
- 我有 GEMINI_API_KEY 在 shell env

依序執行：
1. echo 'GCP_PROJECT=YOUR_PROJECT_ID' > .env.deploy
   echo \"GEMINI_API_KEY=\$GEMINI_API_KEY\" >> .env.deploy
   echo 'BASIC_AUTH_USER=admin' >> .env.deploy
   echo 'BASIC_AUTH_PASSWORD=workshop2026' >> .env.deploy
2. gcloud config set project YOUR_PROJECT_ID
3. gcloud services enable run.googleapis.com cloudbuild.googleapis.com storage.googleapis.com artifactregistry.googleapis.com
4. make setup-data-bucket   （建 GCS bucket 給 Litestream）
5. echo 'LITESTREAM_GCS_BUCKET=YOUR_PROJECT_ID-data' >> .env.deploy
6. make deploy-web   （Cloud Build ~3-5 min）
7. 印出 Cloud Run URL + 提示用 admin/workshop2026 登入
"
```

**預期**：
- 建好 GCS bucket `gs://YOUR_PROJECT_ID-data`
- Cloud Build 成功（4 步：build / push / deploy / route）
- 拿到 URL `https://digest-agent-web-XXXX-uc.a.run.app`
- 瀏覽器打開 → 跳 Basic Auth 對話框 → 進入 UI

---

## Magic Prompt 5 —（進階）GEAP agent runtime 部署

> 不在 5/9 workshop 範疇，留給 5/18 AIA showcase 路徑。

```bash
gemini -p "@GEMINI.md Cloud Run UI 已部署（URL=https://...）。
現在請幫我把 ADK SequentialAgent 部署到 GEAP（Vertex AI Agent Engine）：
1. 確認 .env.deploy 有 STAGING_BUCKET=gs://YOUR_PROJECT_ID-agents（沒有就建：gsutil mb gs://YOUR_PROJECT_ID-agents）
2. 把 Cloud Run URL 寫進 .env.deploy 的 DIGEST_API_URL=
3. 跑 make deploy-agent-engine（~5-10 min）
4. 跑 make invoke-agent-engine 確認 4 個 agent 串流出來
5. 印出 https://console.cloud.google.com/agent-platform/runtimes Console URL
"
```

---

## 跟 Streamlit 版的差別

| 項目 | Streamlit (`make dev-shell`) | Next.js (`bun run dev`) |
|------|----------------------------|------------------------|
| 預裝 | Cloud Shell 內建 Python + uv | 多一步 `make onboard-cloudshell` 裝 bun |
| Port | 8080 | 3000 |
| 個股分析 | `4_stock_analysis.py` 跑 in-process Python ADK，要 `GEMINI_API_KEY` | `/stock-analysis` 透過 Vertex AI 打 GEAP（要先部署 agent runtime） |
| Auth | 無 | HTTP Basic Auth（local dev 用 `BASIC_AUTH_DISABLED=1` 跳過） |
| 持久化 | 預設 `/tmp/digest.db`（ephemeral，workshop 教學用） | Litestream + GCS（Cloud Run 重啟保留所有狀態） |
| 教學用途 | 5/9 workshop **預設路徑** | 5/9 stretch / 5/18 AIA showcase |

---

## Troubleshooting

| 症狀 | 解法 |
|------|------|
| `bun: command not found` 即使跑完 onboarding | `source ~/.bashrc` 或開新 terminal tab |
| `Server misconfigured: BASIC_AUTH_USER not set` | `.env.local` 加 `BASIC_AUTH_DISABLED=1` 或設 `BASIC_AUTH_USER` + `BASIC_AUTH_PASSWORD` |
| `/api/stock-chat 500 GEAP_RESOURCE_NAME not set` | 還沒跑 prompt 5；本地測試的話可以先忽略此 endpoint |
| Cloud Build `Unsupported URL Type "workspace:"` | 你 fork 的版本太舊，pull main 拿 PR #10/#11/#12 後的 Dockerfile |
| Cold start `Cannot find module './361.js'` (dev mode only) | `rm -rf apps/web/.next && bun run dev --turbopack` |

---

## See also

- [`CLOUD_SHELL_WORKSHOP.md`](./CLOUD_SHELL_WORKSHOP.md) — Streamlit path (5/9 workshop default)
- [`PERSISTENCE.md`](./PERSISTENCE.md) — Litestream + GCS architecture
- [`GEAP_DEPLOY.md`](./GEAP_DEPLOY.md) — GEAP agent runtime deployment
- [`scripts/README.md`](./scripts/README.md) — catalog of every script + its `make` wrapper
- [`Makefile`](./Makefile) — run `make` (no args) for the curated entry-points table
