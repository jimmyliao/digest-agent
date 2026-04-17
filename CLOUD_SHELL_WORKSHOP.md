# CLOUD_SHELL_WORKSHOP.md
# AI 新聞小幫手工作坊 — Google Cloud Shell 版

打開 Google Cloud Shell，輸入 `gemini` 進入 interactive mode，依序貼上 Magic Prompt。

---

## ✨ Phase 1 Magic Prompt
> 安裝環境 + 啟動 Streamlit + Web Preview

```
@CLOUD_SHELL_WORKSHOP.md 我剛開啟 Google Cloud Shell，請帶我完成 Phase 1：
安裝 uv、clone https://github.com/jimmyliao/digest-agent、設定 GEMINI_API_KEY、啟動 Streamlit、開 Web Preview 看到 Dashboard。
```

**預期結果：**
- Gemini 會詢問你的 `GEMINI_API_KEY`（沒有也可以跳過進 Mock 模式）
- 最後看到 `200` 回應，Gemini 提示你點 **Web Preview → port 8080**
- 瀏覽器新分頁出現 Digest Agent Dashboard
- 可以 Fetch 新聞、Summarize 看 Gemini 摘要

---

## ✨ Phase 2 Magic Prompt（選做）
> 設定 Telegram Bot，讓部署後可以直接推送新聞

```
@CLOUD_SHELL_WORKSHOP.md Phase 1 完成，請帶我設定 Telegram Bot：
取得 BotFather token、取得 Chat ID、在 Dashboard 填入設定。
```

**預期結果：**
- Gemini 引導你開 Telegram → @BotFather 取得 token
- 再開 @userinfobot 取得 Chat ID
- 填入 Dashboard ⚙️ 渠道設定後，Publish 一篇文章，Telegram 收到推送訊息

---

## ✨ Phase 3 Magic Prompt
> 部署到 Cloud Run，拿到公開 URL

```
@CLOUD_SHELL_WORKSHOP.md 請帶我把 digest-agent 部署到 Cloud Run。
我的 GCP Project ID 是：（填入你的 Project ID）
```

**預期結果：**
- Gemini 啟用必要 GCP API、執行 `make deploy-workshop`
- Cloud Build 打包約 3-5 分鐘
- 拿到一個 `https://digest-agent-workshop-xxxx.asia-east1.run.app` 公開 URL
- 任何人用瀏覽器打開都能看到 Dashboard，不需要 Cloud Shell

---

## ✨ Phase 4 Magic Prompt（進階加碼）
> 從「改一個 prompt」到「讓多個 AI 各司其職」— ADK Multi-Agent 個股分析

**銜接語（講師口頭）：**
> 「剛才你們用 Gemini CLI 改了摘要的 prompt，讓一個 AI 做得更好。
> 但如果分析需要多種專業呢？新聞、產業、市場各需要不同專家。
> 這就是 Multi-Agent 的場景 — 同一個 repo，我們來看看怎麼升級。」

```
@CLOUD_SHELL_WORKSHOP.md Phase 1-3 完成了。請帶我體驗 Phase 4：
從同一個 digest-agent 升級到 ADK Multi-Agent 個股分析。
先在 Streamlit 看結果，再用 ADK DevTools 看 agent 怎麼協作。
```

**預期結果：**

**Step 1 — 同一個 Streamlit，新增一頁（熟悉的 UI）：**
- 切換到 `feature/adk-stock-analysis` branch
- 重啟 Streamlit（`make dev-shell`）
- 左側選單出現「📈 個股分析」新頁面
- 輸入「2330 台積電」→ 看到完整分析報告（新聞 × 產業 × 市場 × 綜合評估）

**Step 2 — 打開 ADK DevTools 看幕後（開發者視角）：**
- `make adk-web` 啟動 ADK Web UI（port 8000）
- Web Preview port 8000 看到 agent 協作的完整過程
- 同樣輸入「分析台積電」→ 看到 4 個 agent 的 thinking + tool 呼叫
- 「剛才 Streamlit 看到的報告，背後就是這 4 個 agent 協作出來的」

### 學習重點

**從 digest-agent 到 multi-agent 的升級路徑（3 min）：**
```
Phase 1-3 你做的事                    Phase 4 升級後
─────────────────                    ─────────────────
1 個 AI（Gemini）                    4 個 AI agent 各司其職
改 prompt 調整輸出                   每個 agent 有專屬 instruction + tools
src/llm/ 直接呼叫                    ADK 管理 agent 溝通和狀態
Streamlit page 1-3                   Streamlit page 4（同一個 app）
```

**ADK 核心概念（3 min）：**
- Agent = LLM + instruction + tools（像一位有專長的分析師）
- Sub-agents = 專業分工（新聞、產業、市場各有專家）
- Runner = 執行環境（管理 agent 之間的溝通）
- `adk web` = Agent 的 DevTools（不是產品 UI，是開發者偵錯工具）

**ADK Memory 三層架構（3 min）：**
```
1. temp: state     → 工具呼叫間暫存（agent 內部用）
2. session state   → 本次對話的便利貼（agent 間共享 output_key）
3. MemoryService   → 跨對話的知識庫（長期學習）
```

**Demo 體驗（5 min）：**
- Streamlit: 輸入「台積電」看到報告 → 「這背後怎麼運作的？」
- adk web: 同樣的查詢 → 看到 orchestrator 如何委派 3 個 sub-agent
- 同 session 再問「跟聯發科比呢？」→ session state 延續上下文

**動手改（5 min，選做）：**
- 打開 `agents/stock/industry_agent.py`
- 修改 instruction 加入「特別關注 AI 晶片需求」
- 重啟後再分析台積電，看報告差異

---

---

## Appendix：給 Gemini CLI 的執行腳本

> 你是「AI 新聞小幫手」工作坊的 AI 助教。
> 請用繁體中文，親切但精準地引導學員。
> **每個步驟執行後確認成功再繼續，不要一次丟出所有指令。**

### Phase 1 執行細節

**步驟 0 — 確認 Gemini CLI**
```bash
gemini --version
```
- ✅ 有版本號 → 繼續
- ❌ `node: No such file or directory` → 告訴學員點右上角 ⋮ → **重新啟動**

**步驟 1 — 安裝 uv**
```bash
curl -Ls https://astral.sh/uv/install.sh | sh && source ~/.bashrc
uv --version
```

**步驟 2 — Clone + 安裝**
```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
uv sync --all-extras
```

**步驟 3 — 設定 API Key**

詢問學員：「請提供你的 GEMINI_API_KEY，可從 https://aistudio.google.com/app/apikey 免費取得。沒有也可以，會進 Mock 模式。」

```bash
export GEMINI_API_KEY=學員的key
echo 'export GEMINI_API_KEY=學員的key' >> ~/.bashrc
```

**步驟 4 — 啟動 Streamlit**
```bash
nohup make dev-shell > /tmp/streamlit.log 2>&1 &
sleep 5 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
```
看到 `200` 才繼續。有錯：`tail -20 /tmp/streamlit.log`。

**步驟 5 — Web Preview**

告訴學員：「點 Cloud Shell 右上角 **Web Preview（眼睛圖示）** → **Preview on port 8080**，新分頁出現 Dashboard 就成功！
試試：🚀 發佈控制 → Fetch → 勾選文章 → Summarize。」

完成後告訴學員：「✅ Phase 1 完成！請貼 Phase 2 或 Phase 3 Magic Prompt 繼續。」

---

### Phase 2 執行細節（Telegram）

告訴學員：

**取得 Bot Token（30 秒）：**
1. Telegram 搜尋 `@BotFather` → `/newbot` → 取得 API Token

**取得 Chat ID（10 秒）：**
1. Telegram 搜尋 `@userinfobot` → 傳任意訊息 → 取得 `Id`

**重要：** 搜尋你的 Bot → 點 **開始（Start）**，否則推送會出現 `chat not found`。

```bash
export TELEGRAM_BOT_TOKEN=你的token
export TELEGRAM_CHAT_ID=你的chat-id
```

或引導學員在 Dashboard 設定：**⚙️ 渠道設定 → Telegram → 填入 → 💾 儲存到 DB**。

完成後告訴學員：「✅ Telegram 設定完成！請貼 Phase 3 Magic Prompt 部署到雲端。」

---

### Phase 3 執行細節（Cloud Run）

詢問學員的 GCP Project ID（Cloud Shell 左上角可以看到）。

```bash
gcloud config set project 學員的project-id
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
GEMINI_API_KEY=$GEMINI_API_KEY make deploy-workshop
```

部署約 3-5 分鐘。完成後：
```bash
gcloud run services describe digest-agent-workshop --region asia-east1 --format 'value(status.url)'
```

驗證並告訴學員：「🎉 恭喜！Cloud Run URL 可以分享給任何人！」

---

### Phase 4 執行細節（ADK Multi-Agent）

銜接語：「剛才你改了一個 AI 的 prompt。接下來我們在同一個 app 裡，
讓多個 AI 各司其職，協作分析一支股票。」

**步驟 1 — 切換 branch + 重啟 Streamlit（熟悉的 UI）**
```bash
# 先停掉原本的 Streamlit
kill $(lsof -ti:8080) 2>/dev/null

# 切換到 multi-agent branch
git fetch origin
git checkout feature/adk-stock-analysis
uv sync

# 重啟 Streamlit
nohup make dev-shell > /tmp/streamlit.log 2>&1 &
sleep 5 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
```
看到 `200` → 告訴學員：「刷新 Web Preview port 8080，左側選單多了📈 個股分析」

**步驟 2 — 在 Streamlit 體驗個股分析**

告訴學員：
1. 點左側「📈 個股分析」
2. 輸入「2330 台積電」→ 點「🔍 開始分析」
3. 等待 15-30 秒 → 看到完整報告（新聞面 + 產業面 + 市場面 + 綜合評估）
4. 「這份報告背後是 4 個 AI agent 協作的結果。想看看怎麼運作的嗎？」

**步驟 3 — 打開 ADK DevTools 看幕後**
```bash
nohup make adk-web > /tmp/adk.log 2>&1 &
sleep 3 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8000
```
告訴學員：「點 Web Preview → **改 port 8000**（不是 8080）」

1. 左上角選 `stock`
2. 輸入「分析 2330 台積電」
3. 觀察左側面板：每個 agent 的 Event、thinking、tool 呼叫過程
4. 「剛才 Streamlit 看到的報告，就是這 4 個 agent 協作出來的」

**步驟 4 — 解說 Memory（口頭 + 螢幕展示）**

講師在 adk web 展示：
- 第一次查詢 → agent 完整分析（~30 秒）
- 同 session 再問「跟聯發科比呢？」→ session state 延續上下文
- 說明：output_key 讓 orchestrator 能看到每個 sub-agent 的分析結果

**步驟 5 — 動手修改 agent（選做）**

告訴學員：
```bash
# 用 Gemini CLI 修改 agent
gemini -p "打開 agents/stock/industry_agent.py，在 instruction 裡加上『特別關注 AI 晶片供應鏈和 CoWoS 先進封裝產能』"
```
回到 Streamlit 或 adk web，再次分析台積電，看報告差異。

完成後：「🎉 恭喜完成所有 Phase！你從一個 RSS 摘要 app 出發，
一路做到了多個 AI agent 協作的個股分析系統。
同一個 repo、同一個 Streamlit、從單一 pipeline 進化到 multi-agent。」

---

### 常見狀況

| 狀況 | 處理方式 |
|------|---------|
| `gemini --version` 噴 `node: No such file or directory` | 點 ⋮ → 重新啟動 |
| `uv` 裝完找不到 | `source ~/.bashrc` |
| Web Preview 空白 / WebSocket 錯誤 | 確認用 `make dev-shell`（已內含修復旗標） |
| `OperationalError: unable to open database` | `mkdir -p data`（已內含在 `make dev-shell`） |
| port 8080 沒回應 | `tail -20 /tmp/streamlit.log` |
| Telegram `chat not found` | 先在 Telegram 對 Bot 按 **Start** |
| Cloud Run deploy 失敗 | 確認 billing：`gcloud beta billing projects describe <project-id>` |
| Cloud Run 第一次開很慢 | Cold start，等 10 秒重整 |
| Gemini API 429 | 摘要數量調低（UI slider） |
| 沒有 API Key | Mock 模式，摘要是假的但流程完整 |
| 環境完全壞掉（最後手段） | `sudo rm -rf $HOME` → 點 ⋮ → 重新啟動（**$HOME 全刪**） |
| ADK Web UI port 8000 不通 | `tail -20 /tmp/adk.log`，確認 `adk web` 啟動成功 |
| `google_search` tool 失敗 | 確認有 `GEMINI_API_KEY`，Google Search grounding 需要有效 key |
| Agent 回應很慢 | 正常，4 個 agent 串聯約 15-30 秒 |
| `ModuleNotFoundError: agents` | 確認在 `digest-agent/` 目錄下執行 |
