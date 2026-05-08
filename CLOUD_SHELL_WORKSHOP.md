# CLOUD_SHELL_WORKSHOP.md
# AI 新聞小幫手工作坊（5/9 BwAI 台中 / 90 min）

Cloud Shell 開好後，照下面 Phase 1 → 4 順序貼指令。Phase 1 用 `gemini` interactive，其餘直接 bash copy-paste。

---

## 你會做到的

| Phase | 做什麼 | 預估 |
|------|------|------|
| 1 | Clone repo + 環境驗證（Magic Prompt） | 5 min |
| 1.5 | Vertex AI auth 寫進 `.env.local` | 1 min |
| 1.5b | 部署 ADK Agent 到 Vertex Agent Engine（背景跑） | 5–10 min |
| 2 | 起 Next.js dev server（port 3000） | 30 sec |
| 3 | Pipeline：Fetch 新聞 → Summarize | 5 min |
| 4 | Stock：4-agent 個股分析 stream | 10 min |
| M4 | （進階）部署自家 Cloud Run UI | 10 min |

---

## 開場準備（2 min）

打開 [console.cloud.google.com](https://console.cloud.google.com)，右上角 `>_` 開 Cloud Shell。

```bash
# 確認 onramp credit project 已選
gcloud config get-value project

# 啟用 Vertex AI（onramp 通常已預啟用，跑一下保險）
gcloud services enable aiplatform.googleapis.com

# 持久化 project + region 到 shell（gemini-cli + apps/web 都會讀）
PROJECT=$(gcloud config get-value project)
echo "export GOOGLE_CLOUD_PROJECT=$PROJECT" >> ~/.bashrc
echo "export GOOGLE_CLOUD_LOCATION=us-central1" >> ~/.bashrc
source ~/.bashrc
```

---

## Phase 1 — Clone + Verify（Magic Prompt）

進 gemini interactive：

```bash
gemini
```

進 auth 選單時選 **`3. Vertex AI`**（onramp 學員）或 **`2. Use Gemini API Key`**（fallback）。

等出現 `> Type your message` 後，貼下面：

```
我在 Cloud Shell（第一次或重複跑 workshop）。請：
1. command -v rg >/dev/null || sudo apt-get install -y ripgrep
2. mkdir -p ~/_old
3. 如果 ~/digest-agent 已存在 → mv ~/digest-agent ~/_old/digest-agent-$(date +%Y%m%d-%H%M%S)
4. cd ~ && git clone https://github.com/jimmyliao/digest-agent.git
5. cd digest-agent && make workshop-verify

跑完告訴我：rg / bun / uv 版本、health endpoint 回傳、是否全部 ✅
```

**預期**：終端最後印
```
✅ Cloud Shell smoke test PASSED
🎉 Workshop environment verified end-to-end.
```

完成後 Ctrl+C 兩下退出 gemini，回到一般 shell。

---

## Phase 1.5 — Vertex AI auth 寫進 dev env

```bash
cd ~/digest-agent
echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT" >> apps/web/.env.local
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> apps/web/.env.local
tail -3 apps/web/.env.local
```

---

## Phase 1.5b — 部署 ADK Agent 到 Vertex Agent Engine（背景）

```bash
cd ~/digest-agent
nohup make workshop-deploy-agent > /tmp/geap-deploy.log 2>&1 &
echo "Deploy PID: $!"
```

觀察進度（每 30 秒會 print elapsed）：

```bash
tail -f /tmp/geap-deploy.log
```

等到看到 `✅ Deployed: projects/.../reasoningEngines/<NEW_ID>` 後 Ctrl+C 退 tail。

> **約 5–10 min**。可以平行做 Phase 2 + 3。

---

## Phase 2 — 起 Next.js dev server

```bash
cd ~/digest-agent/apps/web
nohup bun run dev > /tmp/dev.log 2>&1 &
sleep 6
curl -s http://localhost:3000/api/health && echo
```

看到 `{"status":"ok","db":true,...}` → 點 Cloud Shell 右上角 **Web Preview** → 改 port 3000，新分頁開 Pipeline 頁面。

---

## Phase 3 — Pipeline（RSS → Summarize）

在 Web Preview 頁面：

1. 點 **🚀 Pipeline**
2. **Fetch** → 等 ~10 秒，看到 `Fetched: 100+ articles`
3. 切到 **📰 Articles** → 勾選 3 篇
4. 回 Pipeline → **Summarize** → 看 Gemini 串流摘要進來

---

## Phase 4 — Stock 4-agent 分析

確認 Phase 1.5b 已完成後，把新 engine resource name 寫進 dev env 並 restart：

```bash
cd ~/digest-agent
echo "GEAP_RESOURCE_NAME=$(tail -1 deployed-agent-engines.txt | cut -f2)" >> apps/web/.env.local
tail -3 apps/web/.env.local

# restart dev server
kill $(lsof -ti:3000) 2>/dev/null
sleep 2
cd apps/web && nohup bun run dev > /tmp/dev.log 2>&1 &
sleep 6
curl -s http://localhost:3000/api/health && echo
```

回 Web Preview → **📈 Stock** → 輸入：

```
近期台積電 vs 聯發科 vs 鴻海
```

預期看到 4 個 agent 依序串流：

```
news_collector → industry_analyst → market_analyst → stock_orchestrator
```

每個 `search_db_articles` tool return 應該標 `"source":"remote_api"`，代表你自家的 GEAP engine 透過 HTTP 從 Cloud Run API 拿到真實近期新聞（不是空的本地 SQLite）。

---

## Phase M4 — （進階）部署自家 Cloud Run UI

如果想完整 close-loop（自家 GEAP engine 連自家 Cloud Run UI），跑：

```bash
cd ~/digest-agent
nohup make workshop-deploy-web > /tmp/web-deploy.log 2>&1 &
tail -f /tmp/web-deploy.log
```

完成後拿到自己的 `https://digest-agent-web-XXXXX-uc.a.run.app`，用 `admin` / `workshop2026` 登入。

要讓 GEAP engine 改打自家 Cloud Run（取代 prod）：

```bash
URL=$(gcloud run services describe digest-agent-web --region=us-central1 --format='value(status.url)')
DIGEST_API_URL="$URL" make workshop-deploy-agent
```

再回 Phase 4 重跑 Stock 分析，新 source 就是你自家 Cloud Run。

---

## Auth fallback（沒 onramp credit）

跑 `gemini` 時改選 `2. Use Gemini API Key`：

```bash
# 拿免費 key: https://aistudio.google.com/app/apikey
export GEMINI_API_KEY=AIza...
echo 'export GEMINI_API_KEY=AIza...' >> ~/.bashrc
```

跑 `make workshop-deploy-agent` 時也會自動把這個 key 帶進 GEAP engine。

---

## 常見問題

| 症狀 | 解法 |
|------|------|
| `bun: command not found` 即使 onboarding 跑完 | `source ~/.bashrc` 或開新 Cloud Shell tab |
| Web Preview 空白 / 卡住 | 看 `tail -30 /tmp/dev.log`，常見是 port 被佔 |
| `/api/stock-chat` 500 `GEAP_RESOURCE_NAME not set` | Phase 4 第一段 `echo + restart` 漏跑 |
| Cold start `Cannot find module './361.js'` | `rm -rf apps/web/.next && bun run dev` |
| Phase 1.5b 卡很久 | tail log 看是否 `Still deploying...` 還在動，typical 4–6 min |
| Phase 4 分析慢 | 4 agent 串聯 + 真實 LLM call，30–90 秒正常 |
| Cloud Run deploy `Permission denied` | onramp project billing 沒啟用，到 console 看 |
| `gemini --version` 報 `node: No such file or directory` | Cloud Shell ⋮ → 重新啟動 VM |

---

## 講師補充

**為什麼 Magic Prompt 只用在 Phase 1？**
Clone + verify 是一次性自動化，學員不知道該打啥指令最好交給 LLM。其他步驟（auth / deploy / start dev / wire env）用 deterministic Make target 或 bash copy-paste 比 prompt 自癒可靠 10 倍——`gemini-cli` safety policy 會擋 `$()` command substitution，跑 5 次有 4 次要 fallback。

**架構**
- Next.js 15 App Router（apps/web）
- SQLite + Litestream → GCS（Cloud Run 重啟保留 articles）
- ADK SequentialAgent → ParallelAgent：`news_collector` → `industry_analyst` → `market_analyst` → `stock_orchestrator`
- Vertex Agent Engine Runtime（managed ADK，免自己跑 server）

**Phase 4 的 `source: "remote_api"` 是關鍵**
證明學員自家 GEAP engine 走 HTTP fallback 抓真實新聞，不是空的本地 SQLite，整條 close-loop 通了。

---

## 進階閱讀

- [`Makefile`](./Makefile) — `make`（無參數）看所有 entry-points
- [`PERSISTENCE.md`](./PERSISTENCE.md) — Litestream + GCS 架構
- [`GEAP_DEPLOY.md`](./GEAP_DEPLOY.md) — Agent Engine 部署細節
- [`scripts/README.md`](./scripts/README.md) — script catalog
