# 🚀 GDG Workshop - AI 新聞小幫手：實作指南 (WORKSHOP_GUIDE)

這份文件引導你從零開始建立並擴充一個 AI 自動化新聞摘要助手。無論你是學員還是助教，都可以按照此 SOP 完成今天的任務。

**主題**：🚀 AI 新聞小幫手
**Repo**：`https://github.com/jimmyliao/digest-agent.git`
**投影片**：`https://bwai0310.web.app`

---

> [!IMPORTANT]
> **🚀 快速開始：一鍵自動化環境設定 (Antigravity 用戶專屬)**  
> 如果你正在使用 **Antigravity IDE**，你根本不需手動打指令！請直接開啟右側的 Agent 面板，複製並貼上以下這段話：
>
> ```text
> 請幫我把 https://github.com/jimmyliao/digest-agent.git clone 下來，然後進到資料夾裡面用 uv sync --all-extras 安裝依賴。好了之後幫我從 .env.example 複製一份 .env。做完提醒我去補上 API Key。
> ```
>
> 貼完之後，Agent 會自動幫你完成下載、安裝與設定。你只需要最後去補上 API Key 即可。

---

## 🅰️ Lab A：Clone & Run (啟動專案)

**目標**：讓學員成功在本地跑起 Streamlit 網頁應用程式，並能正確總結文章。

### Step 1：環境檢查與擴充套件安裝
- 學員電腦必須要有 **Python 3.11+**。
- 必須安裝過 [`uv`](https://github.com/astral-sh/uv) (Python 的高效能套件管理器)。
- 確認學員有在終端機執行：
  ```bash
  git clone https://github.com/jimmyliao/digest-agent.git
  cd digest-agent/digest-agent
  uv sync --all-extras
  ```

### Step 2：設定環境變數 (.env)
- 複製範例檔：
  ```bash
  cp .env.example .env
  ```
- **取得 API Key (選擇性)**：
  引導學員去 [aistudio.google.com](https://aistudio.google.com/) 申請免費的 Gemini API Key，並貼入 `.env` 中的 `GEMINI_API_KEY=`。
- **設定 GCP Project ID (選擇性)**：
  如果你有 GCP 專案，可以順便填入 `GOOGLE_CLOUD_PROJECT=`。這在本地開發不是必須，但當你需要使用 Vertex AI 或部署到雲端時就會用到。
- 🚨 **TA 救援提示**：如果學員申請 API Key 卡住，請跟他們說**「沒有 API Key 也沒關係」**，專案會自動進入 **Mock Mode**，依然可以點擊看摘要（雖然是假資料），不會報錯。

### Step 3：啟動應用程式
- 請學員執行：
  ```bash
  make dev
  # 或者：uv run streamlit run src/app.py
  ```

### Step 4：驗證 UI
- 帶學員打開瀏覽器：`http://localhost:8080`
- 驗證流程：去左側菜單點 **[2_publish]** -> 按下 **[Fetch]** -> 勾選一兩篇文章 -> 按下 **[Summarize]**。
- 有出現摘要畫面（或 Mock 假資料）即算完成 Lab A！

> [!TIP]
> **想要看真實推播？**
> 你可以到 [Appendix：Telegram 快速設定](#appendixtelegram-快速設定) 取得 Token 並填入瀏覽器的「渠道設定」中測試。但如果你想用 AI 學會怎麼寫一個新的發佈器，請繼續 Lab B。

---

## 🅱️ Lab B：用 Gemini CLI 加功能

**目標**：體驗如何透過 `AGENTS.md` 讓 Gemini CLI 讀懂專案，並直接用自然語言請它加一個新功能（Slack Publisher）。

### Step 1：確認專案脈絡 (GEMINI.md)
- 請學員在 `digest-agent/` 目錄下確認：
  ```bash
  ls -la GEMINI.md
  ```
  （這是一個 symlink，指嚮 `AGENTS.md`，讓 AI 工具明白這個專案的架構）。

### Step 2：開啟安全保護 (Checkpointing)
- 🚨 **強烈建議 TA 提醒學員做這步**，避免被 AI 改爛程式碼。
- 在 `~/.gemini/settings.json` 裡面確認打開 Checkpointing：
  ```json
  { "general": { "checkpointing": { "enabled": true } } }
  ```

### Step 3：呼叫並下指令
- 啟動互動模式：
  ```bash
  gemini
  ```
- **輸入 Prompt**：
  > 「參考 telegram_publisher.py，建立 slack_publisher.py，用 Webhook URL 發佈摘要」
- **預期結果**：Agent 會先去看 `telegram_publisher.py` 當範本，然後生出 `slack_publisher.py`，最後修改 `__init__.py` 註冊新的 Publisher。
- **還原教學**：若生出來壞掉跑不動，教學員在終端機打 `/restore` 就能還原檔案跟對話歷史！

---

## 🅲 Lab C：調整 Prompt 格式

**目標**：學會去源頭修改提示詞 (Prompt)，體驗不同風格的摘要輸出。

### Step 1：修改 Prompt 程式碼
- 請學員打開 `src/llm/prompt_manager.py`。
- 找到原本的格式定義：
  ```python
  "請用以下格式輸出：
  - 標題：
  - 100字摘要：
  ..."
  ```
- 引導學員改成自己想玩的風格，例如：
  > "請變成推特風格，280字內，包含 2-3 個 hashtag，語氣活潑！"
  或者
  > "請幫我把摘要翻譯成英文 (Translate to English)。"

### Step 2：重新驗證
- 網頁（Streamlit）通常會自動 Reload；若沒有，回到瀏覽器重整。
- 重新去 **Publish 頁面** 點一次 **Summarize**，看看是不是變成剛剛設定的新風格。

---

## 📌 TA Debug 常見問題與備忘
1. **指令找不到 `uv`？**
   - Windows/Mac 可能需要重啟 Terminal 讓 PATH 生效。
2. **`make dev` 執行失敗？**
   - 學員可能在 Windows 且沒有安裝 `make`。請他們直接下：`uv run streamlit run src/app.py` 即可。
3. **API Rate Limit 報錯 (HTTP 429)？**
   - 免費版 Gemini API 有頻率限制。
   - **自動降級機制 (NEW)**：專案已實作自動降級 (Fallback)，若 `gemini-2.5-flash` 額度用罄，會自動嘗試 `flash-lite` 或 `3.1-flash-lite-preview`。
   - **建議**：請學員在 UI 上將「摘要數量上限」設為 **1~5 篇**，不要一次全選。
4. **Agent 發瘋或寫出有 Bug 的扣？**
   - 使用 `/restore` 大法。
5. **(進階) 學員想試玩 MCP 連接 GitHub？**
   - 投影片有提到連接 GitHub，若學員想實作，請教他們在 `~/.gemini/settings.json` 加入：
     ```json
     {
       "mcpServers": {
         "github": {
           "command": "docker",
           "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/modelcontextprotocol/servers/github:latest"]
         }
       }
     }
     ```
   - ⚠️ 注意：這需要學員電腦有裝 Docker，也需要在環境變數設定 `GITHUB_PERSONAL_ACCESS_TOKEN`，若時間不夠建議請他們以聽講為主。

---

## ☁️ 常見問答：可以使用 Google Colab 嗎？

**強烈建議學員使用「本機 (Local Machine)」！不推薦使用 Colab。**

如果學員問起，請助教以下列三個理由勸退，並鼓勵他們在自己的筆電跑：

1. **Gemini CLI 互動卡頓**：Gemini CLI 是終端機互動介面 (TUI)，在 Colab 的網頁 cell 中執行互動模式 (`gemini`) 往往會因為缺乏完整 tty 而卡死或無法正常輸入指令。
2. **網頁預覽非常困難**：這是一個 Streamlit 網頁應用。在 Colab 啟動後，它會掛在內部的 `localhost:8080`，學員**無法直接點擊網址看到網頁**。必須透過 `localtunnel` 或 `ngrok` 進行 Port 穿透，很多初學者會卡在憑證和對外網址設定。
3. **體驗不到最好的 AI 編輯器**：這堂課的精髓是體驗「AI 幫忙改 Code」，在本地使用 VS Code / Antigravity 才能舒適地看到 Code Diff、檔案變動甚至使用 Checkpointing，Colab 內建的簡易編輯器無法提供這種流暢感。

*(備用方案：若學員電腦真的完全鎖死無法裝 Python，只能在 Colab 跑時，必須教他們用 `gemini -p "指令"` (Headless 模式) 來互動，並用 `npx localtunnel --port 8080` 來把網頁曝露到外網。)*

---

## 🛠️ 教學：如何從頭使用本專案 (如果從空白開始)

若學員詢問「我拿到了這個專案，接下來該怎麼用 AI 開發？」，可以引導他們依照以下情境操作：

### 情境 1：用 Gemini CLI (終端機模式)
這是最符合 Workshop 展示的純命令列工作流。

1. **進入專案並啟動 Agent**：
   ```bash
   cd digest-agent
   gemini
   ```
2. **與 Agent 溝通**：
   Agent 啟動時會自動讀取 `./AGENTS.md` 了解專案脈絡（知道這是個 Streamlit 應用，用 feedparser 抓新聞）。直接在提示符號後輸入需求：
   > "請幫我在左側選單新增一個『關於作者』頁面，顯示 Jimmy 的簡介"
3. **安全防護 (Checkpointing)**：
   一旦 Agent 改爛了，立刻輸入 `/restore` 叫出時光機恢復。

### 情境 2：用 Antigravity IDE (自動化設定)
這是最符合 Agentic Workflow 的做法。學員只需要把你的專案網址餵給 AI 即可！

1. **開啟空的 Antigravity 視窗**：
   隨便開一個空資料夾，然後進入右方的 Agent 面板。
2. **複製貼上這段「起手式 Prompt」**：
   > "請幫我把 `https://github.com/jimmyliao/digest-agent.git` clone 下來，然後進到資料夾裡面用 `uv sync --all-extras` 安裝依賴。好了之後幫我從 `.env.example` 複製一份 `.env`。做完提醒我去補上 API Key。"
3. **等待 Agent 完成**：
   Agent 會自動開啟終端機，跑完所有 git clone 和 uv 安裝的流程。
4. **填寫 API Key (或直接略過)**：
   自己打開 `.env` 把 `GEMINI_API_KEY` 補上（如果沒有 API Key 就不填，系統會進入 Mock 模式）。
5. **啟動並開始玩**：
   在終端機輸入 `make dev` 就可以看見網頁了！想要加什麼功能，直接再對 Agent 面板許願即可。

---

## 📖 Appendix：Telegram 快速設定

如果學員想要測試真實推播，請照以下步驟取得 Token：

1. **取得 Bot Token**： 
   在 Telegram 搜尋 [@BotFather](https://t.me/botfather)，對它輸入 `/newbot`，按照說明設定名字，最後會得到一段 `HTTP API Token`。
2. **取得您的 Chat ID**：
   在 Telegram 搜尋 [@userinfobot](https://t.me/userinfobot)，對它輸入任何內容，它會回傳你的 `Id` (這就是 Chat ID)。
3. **設定應用程式**：
   回到 `http://localhost:8080` 的 **[2_publish]** 頁面，點選 **[渠道設定]** -> **[Telegram]**，填入 Token 與 ID 後點擊 **[儲存到 DB]**。
   *(或者，你也可以點擊 **[儲存到 .env]** 直接寫入檔案)*。

4. **自動化填寫 (Antigravity 用戶推薦)**：
   你也可以直接讓 Agent 幫你搞定。拿到 Key 後對 Agent 貼上：
   > "幫我把 Telegram 的 BOT_TOKEN='你的秘鑰' 和 CHAT_ID='你的ID' 加入到 .env 檔案中，並檢查 src/publishers/telegram_publisher.py 是否已正確配置。"

5. **啟動機器人 (⚠️ 非常重要)**：
   **發佈之前，請務必先在自己的 Telegram App 中搜尋您的機器人（例如 `@您的機器人帳號`），並點擊下方的「Start (開始)」** 或傳送一句話給它。
   *(Telegram 防垃圾機制規定：機器人不能主動密未曾互動過的用戶，否則會發生 `chat not found` 錯誤！)*

6. **測試發佈**：
   回到 **[Pipeline 操作]**，選取已摘要的文章點擊 **[Publish]**。 ✅

---

## 🛠️ 常見問題與排除 (Troubleshooting)

    *   **原因**：免費版 Gemini API 每分鐘請求次數有限。
    *   **解法**：
        1. 專案內建 **模型自動降級 (Fallback)**，遇到 429 會自動切換模型，請稍候片刻。
        2. 在 **[2_publish]** 頁面，將「摘要數量上限」拉桿調低（預設已設為 1，建議測試時不要調太高）。
*   **2. Agent 找不到資料表 (Hallucinate SQLite Table)**：
    *   **原因**：Agent 可能沒讀到 `AGENTS.md` 或是工作目錄縮在子目錄。
    *   **解法**：請確保在 `digest-agent` 根目錄啟動 Agent。如果它還是亂寫 SQL，可以提醒它：「請參考 AGENTS.md 中的資料庫架構，使用 ArticleDB 資料表」。
*   **3. Telegram `chat not found`**：
    *   **解法**：請檢查是否已經對 Bot 按下 **[Start]**。機器人無法主動發訊給沒互動過的用戶。
