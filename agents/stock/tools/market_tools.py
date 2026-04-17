"""市場趨勢工具 — 使用 Google Search 進行市場與總經分析。"""

from google.adk.tools import google_search


def analyze_market_trends(market: str = "台股", focus_area: str = "") -> dict:
    """分析市場整體趨勢與總體經濟環境。透過 Google 搜尋蒐集市場數據與專家觀點。

    Args:
        market: 市場名稱（預設「台股」，也可指定如「美股」、「港股」）
        focus_area: 選填的關注領域（例如「利率政策」、「外資動向」、「技術面」）

    Returns:
        包含市場趨勢分析資料的字典
    """
    query_parts = [f"{market} 市場趨勢 最新動態"]
    if focus_area:
        query_parts.append(focus_area)

    query = " ".join(query_parts)

    return {
        "tool": "google_search",
        "query": query,
        "instruction": (
            f"請使用 google_search 工具搜尋：{query}，"
            f"並整理出 {market} 的市場趨勢、重要指標變化、"
            f"以及影響後市的關鍵因素。"
        ),
    }
