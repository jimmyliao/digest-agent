"""產業分析工具 — 使用 Google Search 進行產業趨勢研究。"""

from google.adk.tools import google_search


def analyze_industry_trends(industry: str, company_name: str = "") -> dict:
    """分析特定產業的發展趨勢與競爭態勢。透過 Google 搜尋蒐集產業報告與分析資訊。

    Args:
        industry: 產業名稱（例如「半導體」、「AI 伺服器」、「電動車」）
        company_name: 選填的公司名稱，用來聚焦該公司在產業中的定位

    Returns:
        包含產業分析資料的字典
    """
    query_parts = [f"{industry} 產業趨勢分析 2026"]
    if company_name:
        query_parts.append(company_name)

    query = " ".join(query_parts)

    return {
        "tool": "google_search",
        "query": query,
        "instruction": (
            f"請使用 google_search 工具搜尋：{query}，"
            f"並整理出 {industry} 產業的關鍵趨勢、競爭格局、"
            f"以及未來展望。"
        ),
    }
