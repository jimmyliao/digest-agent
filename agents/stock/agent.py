"""Root Orchestrator Agent — 個股綜合分析系統的主控 Agent。

支援兩種路徑：
- 有安裝 leapcore → 使用 LeapCore 完整功能（resilience, cost tracking 等）
- 無 leapcore → 使用 ADK 原生（workshop 參加者走這條）
"""

try:
    from leapcore.backends.adk import create_orchestrator

    HAS_LEAPCORE = True
except ImportError:
    HAS_LEAPCORE = False

from google.adk.agents import LlmAgent

from .news_agent import news_agent
from .industry_agent import industry_agent
from .market_agent import market_agent

_INSTRUCTION = """你是一位資深投資分析總監，負責統籌個股綜合分析報告。

你管理三位專業分析師：
1. **news_collector** — 負責蒐集與整理個股相關新聞（會從本地 DB 和 RSS 搜尋）
2. **industry_analyst** — 負責分析公司所屬產業趨勢
3. **market_analyst** — 負責分析整體市場環境與總經趨勢

**嚴格工作流程（必須遵守）：**
你絕對不可以自己撰寫分析內容。你必須：
1. 將任務委派給 news_collector → 等待其回覆
2. 將任務委派給 industry_analyst → 等待其回覆
3. 將任務委派給 market_analyst → 等待其回覆
4. 收到三份報告後，整合成最終報告

❌ 禁止：跳過委派、自己猜測內容、產出「待分析師提供」的空殼
✅ 必須：委派每位分析師，用他們回傳的實際內容撰寫報告

**最終報告格式：**

## 📊 個股綜合分析報告

### 一、新聞面分析
（整合 news_collector 回傳的實際新聞與分析）

### 二、產業面分析
（整合 industry_analyst 回傳的實際產業分析）

### 三、市場面分析
（整合 market_analyst 回傳的實際市場分析）

### 四、綜合評估
- **投資評級**: 買進/持有/賣出
- **關鍵觀察點**: 列出 3-5 個最重要的觀察重點
- **風險提示**: 列出潛在風險因素

### 五、結論與建議
（綜合所有面向的最終分析結論）

**重要提醒：**
- 所有回覆使用繁體中文
- 分析僅供參考，不構成投資建議
- 明確標註資料來源與分析時間
"""

if HAS_LEAPCORE:
    # LeapCore 路徑：多 backend 支援、resilience、cost tracking
    root_agent = create_orchestrator(
        name="stock_orchestrator",
        backend="adk",
        model="gemini-2.5-flash",
        instruction=_INSTRUCTION,
        sub_agents=[news_agent, industry_agent, market_agent],
        output_key="final_analysis",
        resilience={"retry": 3, "fallback_model": "gemini-2.5-flash-lite-preview-06-17"},
        cost_tracking=True,
    )
else:
    # ADK 原生路徑：workshop 參加者、無 leapcore 時
    root_agent = LlmAgent(
        name="stock_orchestrator",
        model="gemini-2.5-flash",
        instruction=_INSTRUCTION,
        sub_agents=[news_agent, industry_agent, market_agent],
        output_key="final_analysis",
    )
