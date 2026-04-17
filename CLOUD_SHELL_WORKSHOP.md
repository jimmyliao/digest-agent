# CLOUD_SHELL_WORKSHOP.md
# AI 新聞小幫手工作坊 — Google Cloud Shell 版

打開 Google Cloud Shell，輸入 `gemini` 進入 interactive mode，依序貼上 Magic Prompt。

---

## ✨ Phase 1 Magic Prompt
> 安裝環境 + Clone + 啟動 Streamlit + Web Preview

```
請幫我依序執行（每步確認成功再繼續，用繁體中文回覆）：
1. curl -Ls https://astral.sh/uv/install.sh | sh && source ~/.bashrc
2. git clone https://github.com/jimmyliao/digest-agent.git && cd digest-agent
3. uv sync --all-extras
4. 問我要 GEMINI_API_KEY（從 https://aistudio.google.com/app/apikey 取得，沒有可跳過進 Mock 模式）
5. cp .env.example .env，然後用 sed 把 .env 裡的 GEMINI_API_KEY=your-gemini-api-key-here 替換成我提供的 key。同時把 GOOGLE_API_KEY=your-gemini-api-key-here 也替換成同樣的 key（ADK 需要）
6. cat .env | grep API_KEY 確認寫入成功
7. 驗證 API Key 可用：source .env && uv run python -c "from google.genai import Client; c=Client(api_key='$GEMINI_API_KEY'); r=c.models.generate_content(model='gemini-2.5-flash',contents='說 OK'); print('API Key 驗證成功：', r.text[:20])"。如果失敗，告訴我 key 可能無效，但可以繼續（Mock 模式）
8. nohup make dev-shell > /tmp/streamlit.log 2>&1 &
9. sleep 5 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
10. 看到 200 後，告訴我點 Cloud Shell 右上角 Web Preview → port 8080
```

**預期結果：**
- Gemini 會依序執行安裝、Clone、啟動
- 中途詢問你的 `GEMINI_API_KEY`（沒有也可以跳過進 Mock 模式）
- 最後看到 `200` 回應，Gemini 提示你點 **Web Preview → port 8080**
- 瀏覽器新分頁出現 Digest Agent Dashboard
- 可以 Fetch 新聞、Summarize 看 Gemini 摘要

---

## ✨ Phase 2 Magic Prompt（選做）
> 設定 Telegram Bot，讓部署後可以直接推送新聞

```
@CLOUD_SHELL_WORKSHOP.md Phase 1 完成了，請帶我設定 Telegram Bot：
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
@CLOUD_SHELL_WORKSHOP.md Phase 1-3 完成了，請帶我體驗 Phase 4：
ADK Multi-Agent 個股分析。先 Fetch 財經新聞，再到個股分析頁面分析台積電。
```

**預期結果：**

**Step 1 — 先 Fetch 財經新聞（餵資料給 agent）：**
- 到 publish 頁面 → Fetch，抓取最新財經新聞（Yahoo 台股、TWSE 證交所、TechNews）
- 左側選單已有「📈 個股分析」新頁面（同一個 Streamlit app）

**Step 2 — 個股分析（Multi-Agent 協作）：**
- 點左側「📈 個股分析」
- 輸入「台積電AI晶片供應鏈」→ 看到完整分析報告（新聞 × 產業 × 市場 × 綜合評估）
- 「注意看新聞面 — 來源是剛才 Fetch 的 Yahoo、證交所，同一批資料被 agent 重新利用」

**Step 3 — 展開 Agent 協作細節（內建 DevTools）：**
- 報告下方點「🔍 Agent 協作細節（DevTools）」
- 看到每個 agent 的 tool 呼叫（`search_db_articles` 從 DB 讀取 Phase 1 的新聞）
- 「這就像 Chrome F12 — 不用另開工具，直接在同一個頁面看 agent 怎麼協作」

### 學習重點

**從 digest-agent 到 multi-agent 的升級路徑（3 min）：**
```
Phase 1-3 你做的事                    Phase 4 升級後
─────────────────                    ─────────────────
1 個 AI（Gemini）                    4 個 AI agent 各司其職
改 prompt 調整輸出                   每個 agent 有專屬 instruction + tools
src/llm/ 直接呼叫                    ADK SequentialAgent 管理執行順序
Streamlit page 1-3                   Streamlit page 4（同一個 app）
Phase 1 Fetch 的新聞                 → Phase 4 news_collector 從 DB 讀取
```

**ADK 核心概念（3 min）：**
- Agent = LLM + instruction + tools（像一位有專長的分析師）
- SequentialAgent = 保證每個 agent 都執行（框架層保證，不靠 prompt）
- output_key = agent 之間的便利貼（session state 共享分析結果）
- Runner = 執行環境（Streamlit 透過 Runner 呼叫整個 pipeline）

**ADK Session State — agent 之間的溝通（3 min）：**
```
SequentialAgent 依序執行：
1. news_collector    → output_key: "news_analysis"     → 寫入 session state
2. industry_analyst  → output_key: "industry_analysis"  → 寫入 session state
3. market_analyst    → output_key: "market_analysis"    → 寫入 session state
4. stock_orchestrator → 讀取三個 output_key             → 整合成最終報告
```

**資料流串接（Phase 1 → Phase 4）：**
```
Phase 1: Fetch → RSS (Yahoo台股/TWSE/TechNews) → 存入 DB (174篇)
                                                       ↓ 共用
Phase 4: news_collector → search_db_articles (從 DB 搜尋) → 找到台積電 5 篇
         → industry_analyst (LLM 產業知識)
         → market_analyst (LLM 市場分析)
         → stock_orchestrator (整合報告)
```

**動手改（5 min，選做）：**
- 打開 `agents/stock/industry_agent.py`
- 修改 instruction 加入「特別關注 AI 晶片需求」
- 重啟後再分析台積電，看報告差異

**進階：打開 ADK DevTools（講師選做）：**
> adk web 是 ADK 內建的開發者工具，可以看到更詳細的 event trace、LLM span。
> Workshop 不需要帶，但講師想展示幕後可以用。
```bash
nohup make adk-web > /tmp/adk.log 2>&1 &
# Web Preview → 改 port 8000
```

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

**步驟 3 — 設定 API Key（寫入 .env）**

詢問學員：「請提供你的 GEMINI_API_KEY，可從 https://aistudio.google.com/app/apikey 免費取得。沒有也可以，會進 Mock 模式。」

```bash
cp .env.example .env
sed -i 's/GEMINI_API_KEY=your-gemini-api-key-here/GEMINI_API_KEY=學員的key/' .env
sed -i 's/GOOGLE_API_KEY=your-gemini-api-key-here/GOOGLE_API_KEY=學員的key/' .env
cat .env | grep API_KEY   # 確認寫入成功
```

**步驟 3.5 — 驗證 API Key（快速測試）**
```bash
source .env && uv run python -c "
from google.genai import Client
c = Client(api_key='$GEMINI_API_KEY')
r = c.models.generate_content(model='gemini-2.5-flash', contents='說 OK')
print('API Key 驗證成功：', r.text[:20])
"
```
- ✅ 看到「API Key 驗證成功」→ 繼續
- ❌ 失敗 → 告訴學員 key 可能無效，可繼續（Mock 模式）

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

**步驟 1 — 確認頁面**

告訴學員：「刷新 Web Preview port 8080，左側選單已有📈 個股分析」
（Phase 1 寫入 .env 時已設定 GOOGLE_API_KEY，Phase 4 直接可用）

**步驟 2 — 先 Fetch 財經新聞（銜接 Phase 1）**

告訴學員：
1. 點左側「publish」→ Pipeline 操作
2. 點「▶ 開始 Fetch」→ 等待抓取（約 10 秒）
3. 看到「✅ 抓取完成！新增 XXX 篇文章」
4. 「這些新聞等下會被 Phase 4 的 agent 直接從 DB 讀取來分析」

**步驟 3 — 個股分析**

告訴學員：
1. 點左側「📈 個股分析」
2. 輸入「台積電AI晶片供應鏈」→ 點「🔍 開始分析」
3. 等待 30-60 秒（4 個 agent 依序執行）
4. 看到完整報告：新聞面 + 產業面 + 市場面 + 綜合評估
5. 「注意新聞面的來源 — yahoo-tw-stock、twse-news — 就是剛才 Fetch 的那批」

**步驟 4 — 展開 Agent 協作細節**

告訴學員：
1. 往下滾，點「🔍 Agent 協作細節（DevTools）」
2. 看到每個 agent 的 tool 呼叫紀錄：
   - `search_db_articles` → 從 DB 搜到台積電相關文章
   - news_collector、industry_analyst、market_analyst、stock_orchestrator 各自的回應
3. 「這就像 Chrome F12 — 不用另開工具，看 agent 怎麼分工」

**步驟 5 — 解說架構（口頭，搭配 sidebar 架構圖）**

```
SequentialAgent（框架保證依序執行）
├── 1. news_collector     → search_db_articles (讀 Phase 1 的 DB)
├── 2. industry_analyst   → LLM 產業知識分析
├── 3. market_analyst     → LLM 市場趨勢分析
└── 4. stock_orchestrator → 讀取 3 個 output_key → 整合報告
```

重點說明：
- 「news_collector 用的 `search_db_articles`，就是去讀你們 Phase 1 Fetch 存進去的新聞」
- 「output_key 是 agent 之間的便利貼 — news_analysis、industry_analysis、market_analysis」
- 「最後 stock_orchestrator 把三張便利貼讀出來，整合成你們看到的報告」

**步驟 6 — 動手修改 agent（選做）**

告訴學員：
```bash
# 用 Gemini CLI 修改 agent
gemini -p "打開 agents/stock/industry_agent.py，在 instruction 裡加上『特別關注 AI 晶片供應鏈和 CoWoS 先進封裝產能』"
```
回到 Streamlit 再次分析台積電，看報告差異。

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
| 個股分析 400 API key expired | 確認 `export GOOGLE_API_KEY=$GEMINI_API_KEY` |
| 個股分析 Built-in tools 衝突 | 已修復（最新版本） |
| Agent 回應很慢 | 正常，4 個 agent 串聯約 30-60 秒 |
| 只看到新聞面沒有產業/市場面 | 確認用最新版本（SequentialAgent 架構） |
| `ModuleNotFoundError: agents` | 確認在 `digest-agent/` 目錄下執行 |
| news_collector 搜不到新聞 | 先回 publish 頁面 Fetch，確保 DB 有資料 |
