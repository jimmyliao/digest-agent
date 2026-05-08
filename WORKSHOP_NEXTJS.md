# Next.js Workshop — Magic Prompts for Gemini CLI on Google Cloud Shell

The **5/9 BwAI 台中 default path**: Cloud Run UI + Litestream + GEAP showcase.
Pair with `CLOUD_SHELL_WORKSHOP.md` (the Streamlit path), which is the
**fallback / backup plan** if a student gets stuck on the Next.js
toolchain (bun install, etc.) or on workshop day if Cloud Run / GEAP
goes sideways.

> Quick start: `make workshop-verify` (one-shot install + smoke).
> See Magic Prompt 0 below.

## Pre-requisite

Open Google Cloud Shell, then:

```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
gemini --version                   # confirm Gemini CLI available (Cloud Shell has it pre-installed)
# Cloud Shell auto-authenticates the `gemini` CLI via your logged-in Google
# account on first use — no manual `auth login` needed.
```

### Auth — default: Vertex AI (recommended for workshop)

如果你領了 GCP **onramp credit**（5/9 BwAI 學員會發），直接走 Vertex AI — 跟
production 同 stack、跟 GEAP / Cloud Run 同一套 IAM、不用 API key。

```bash
# 1. 確認 onramp 帶的 project 已選
gcloud config get-value project

# 2. 啟用 Vertex AI API（onramp 通常已預啟用，跑一下保險）
gcloud services enable aiplatform.googleapis.com

# 3. 持久化（gemini-cli + apps/web 都會自動讀）
PROJECT=$(gcloud config get-value project)
echo "export GOOGLE_CLOUD_PROJECT=$PROJECT
export GOOGLE_CLOUD_LOCATION=us-central1" >> ~/.bashrc && source ~/.bashrc
```

**Cloud Shell 內 ADC 自動帶 metadata server token**，免 `gcloud auth application-default login`。

跑 `gemini` 進入互動模式時選 **`3. Vertex AI`**（不是 [1. Sign in with Google] 也不是 [2. Use Gemini API Key]）。

### Auth — fallback: GEMINI_API_KEY

少數沒拿到 onramp credit 的學員可以走 aistudio free tier：

```bash
# 拿免費 key: https://aistudio.google.com/app/apikey
export GEMINI_API_KEY=AIza...
echo 'export GEMINI_API_KEY=AIza...' >> ~/.bashrc
```

`gemini` 互動模式選 **`2. Use Gemini API Key`**。

---

## Magic Prompt 0 — Idempotent clone + verify ⭐ 推薦第一次跑這個

這把 clone + Magic Prompts 1 + 2 包成 `make workshop-verify` 一個指令。如果只想知道
「這台 Cloud Shell 環境跑得起來嗎？」就跑這個。**會 idempotent 處理舊的 digest-agent 目錄**（搬到 `~/_old/` 保留），重跑安全。

> ⚠️ 第一次跑時 cwd 在 `~`、還沒 clone，**不能用 `@filename` 指 repo 內檔案**——這個 prompt 自包含所有指令。

```bash
gemini -p "我在 Cloud Shell（第一次或重複跑 workshop）。請：
1. command -v rg >/dev/null || sudo apt-get install -y ripgrep（gemini-cli 需要，缺了會 fallback warn）
2. mkdir -p ~/_old
3. 如果 ~/digest-agent 已存在 → mv ~/digest-agent ~/_old/digest-agent-\$(date +%Y%m%d-%H%M%S)（保留舊版備查）
4. cd ~ && git clone https://github.com/jimmyliao/digest-agent.git
5. cd digest-agent && make workshop-verify
   過程會：bun + uv 裝好、bun install + uv sync、scaffold apps/web/.env.local（BASIC_AUTH_DISABLED=1）、bg 起 dev server、curl /api/health、自動關 dev、印 PASS/FAIL

跑完告訴我：rg 版本、bun 版本、uv 版本、health endpoint 回傳、是否全部 ✅"
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
gemini -p "@GEMINI.md 我在 Google Cloud Shell（onramp credit 走 Vertex AI 路徑）。請幫我：
1. 跑 make onboard-cloudshell
2. 確認 bun --version 和 uv --version 都有版號（沒有就提醒重 source ~/.bashrc）
3. 確認 apps/web/.env.local 已建立、且預設帶有 BASIC_AUTH_DISABLED=1
4. 把 GOOGLE_CLOUD_PROJECT=\$(gcloud config get-value project) 跟 GOOGLE_CLOUD_LOCATION=us-central1 寫進 apps/web/.env.local
   （fallback 學員：改寫 GEMINI_API_KEY=AIza... 到 .env.local）
5. 跑 gcloud services enable aiplatform.googleapis.com 確認 Vertex AI API 已啟用
6. 印出後續可以跑的兩個下一步指令（dev server + Cloud Run deploy）
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

> **要先有 GCP project + billing 啟用**。Workshop 學員可用 onramp credit。
>
> **註**：Cloud Run service 端目前 default 走 `GEMINI_API_KEY` env，原因是 default Cloud Run service account 沒設 Vertex User role；本機 dev 走 Vertex AI，部署到 Cloud Run 時 .env.deploy 仍寫 `GEMINI_API_KEY` 即可。要走純 Vertex AI 部署，需要 grant SA `roles/aiplatform.user`，超出 90min workshop 範圍。

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

## Magic Prompt 5 — GEAP agent runtime 部署（5/9 Phase 1.5b 用）

> 5/9 workshop default：在 Phase 1.5 認證後背景跑這個，~3-5 min 完成，Phase 4 接 dev server 用。
> 5/18 AIA showcase 進階路徑同樣使用這個 prompt（再加上 Cloud Run UI 串接）。

```bash
gemini -p "@GEMINI.md Phase 1.5 Vertex AI 認證已設好。請幫我背景部署 ADK SequentialAgent 到 GEAP（Vertex AI Agent Engine），Phase 4 stock analysis 會用：
1. gcloud services enable storage.googleapis.com cloudbuild.googleapis.com（aiplatform 已啟）
2. PROJECT=\$(gcloud config get-value project)，gsutil mb -l us-central1 gs://\$PROJECT-agents（已存在跳過）
3. uv sync --extra geap
4. 用 placeholder GEMINI_API_KEY=not-used-engine-runs-on-vertex 跑 nohup make deploy-agent-engine 到 /tmp/geap-deploy.log（runtime 走 Vertex AI，不需要真 key）
5. 印背景 PID + log path
完成後（5/18 AIA path）：跑 make invoke-agent-engine 確認 4 個 agent 串流，印 https://console.cloud.google.com/vertex-ai/agents/agent-engines Console URL
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
| 教學用途 | 5/9 **fallback / backup** path | 5/9 **default** + 5/18 AIA showcase |

---

## Troubleshooting

| 症狀 | 解法 |
|------|------|
| `bun: command not found` 即使跑完 onboarding | `source ~/.bashrc` 或開新 terminal tab |
| `Server misconfigured: BASIC_AUTH_USER not set` | `.env.local` 加 `BASIC_AUTH_DISABLED=1` 或設 `BASIC_AUTH_USER` + `BASIC_AUTH_PASSWORD` |
| `/api/stock-chat 500 GEAP_RESOURCE_NAME not set` | 跑 Magic Prompt 5（Phase 1.5b）背景部署後，跑 Magic Prompt 4-pre 把 resource name 寫進 .env.local 並重啟 dev server |
| `Vertex AI permission denied` / 401-403 from `aiplatform.googleapis.com` | `gcloud services enable aiplatform.googleapis.com`；確認 onramp project 有 Vertex User role；Cloud Shell 重開 tab 讓 ADC 重新拿 token |
| Cloud Build `Unsupported URL Type "workspace:"` | 你 fork 的版本太舊，pull main 拿 PR #10/#11/#12 後的 Dockerfile |
| Cold start `Cannot find module './361.js'` (dev mode only) | `rm -rf apps/web/.next && bun run dev --turbopack` |

---

## See also

- [`CLOUD_SHELL_WORKSHOP.md`](./CLOUD_SHELL_WORKSHOP.md) — Streamlit path (5/9 **fallback / backup**)
- [`PERSISTENCE.md`](./PERSISTENCE.md) — Litestream + GCS architecture
- [`GEAP_DEPLOY.md`](./GEAP_DEPLOY.md) — GEAP agent runtime deployment
- [`scripts/README.md`](./scripts/README.md) — catalog of every script + its `make` wrapper
- [`Makefile`](./Makefile) — run `make` (no args) for the curated entry-points table
