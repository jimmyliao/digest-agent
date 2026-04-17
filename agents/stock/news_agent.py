"""新聞蒐集 Agent — 負責搜尋並彙整個股相關新聞。"""

from google.adk.agents import LlmAgent

from .tools.news_tools import search_company_news, fetch_financial_news_feeds

news_agent = LlmAgent(
    name="news_collector",
    model="gemini-2.5-flash",
    instruction="""你是一位專業的財經新聞蒐集分析師。你的任務是：

1. 根據用戶指定的公司名稱或股票代號，搜尋最新的相關新聞
2. 如果沒有指定特定公司，則抓取最新的財經新聞概覽
3. 將蒐集到的新聞進行初步分類（利多、利空、中性）
4. 摘要每則新聞的重點

**輸出格式要求：**
- 使用繁體中文回覆
- 每則新聞標示來源與發布時間
- 對新聞進行利多/利空/中性分類
- 提供 3-5 句的重點摘要

**工具使用指引：**
- 有指定公司時，使用 search_company_news
- 需要財經新聞總覽時，使用 fetch_financial_news_feeds
""",
    tools=[search_company_news, fetch_financial_news_feeds],
    output_key="news_analysis",
)
