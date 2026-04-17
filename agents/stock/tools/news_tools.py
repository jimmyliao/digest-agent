"""新聞搜尋工具 — 包裝現有 RSSFetcher 提供個股新聞查詢。"""

import asyncio
from typing import Optional


# 預設台股財經 RSS 來源
DEFAULT_FINANCE_SOURCES = [
    {
        "id": "moneyudn",
        "url": "https://money.udn.com/rssfeed/news/1001/5710?ch=money",
        "enabled": True,
    },
    {
        "id": "cnyes",
        "url": "https://news.cnyes.com/news/cat/tw_stock/rss",
        "enabled": True,
    },
    {
        "id": "technews_finance",
        "url": "https://technews.tw/feed/",
        "enabled": True,
    },
]


def search_company_news(company_name: str, ticker: str = "") -> dict:
    """搜尋特定公司的近期新聞。會從 RSS 財經來源抓取後篩選含有公司名稱或代號的文章。

    Args:
        company_name: 公司名稱（中文或英文皆可，例如「台積電」或「TSMC」）
        ticker: 選填的股票代號（例如 "2330"）

    Returns:
        包含搜尋結果的字典，含 articles 列表與 metadata
    """
    from src.fetcher.rss_fetcher import RSSFetcher

    fetcher = RSSFetcher()

    try:
        result = asyncio.run(
            fetcher.fetch_all(DEFAULT_FINANCE_SOURCES, force_refresh=True)
        )
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "articles": [],
            "total": 0,
        }

    # 篩選包含公司名稱或代號的文章
    keywords = [company_name]
    if ticker:
        keywords.append(ticker)

    matched = []
    for article in result.articles:
        text = f"{article.title} {article.content}".lower()
        if any(kw.lower() in text for kw in keywords):
            matched.append(
                {
                    "title": article.title,
                    "source": article.source,
                    "url": article.source_url,
                    "published_at": article.published_at,
                    "snippet": article.content[:300] if article.content else "",
                }
            )

    return {
        "status": "success",
        "company": company_name,
        "ticker": ticker,
        "articles": matched[:10],  # 最多回傳 10 篇
        "total": len(matched),
        "sources_checked": result.sources_processed,
    }


def fetch_financial_news_feeds(max_articles: int = 20) -> dict:
    """抓取台股財經 RSS 來源的最新新聞，不做篩選。

    Args:
        max_articles: 最多回傳的文章數量，預設 20

    Returns:
        包含最新財經新聞的字典
    """
    from src.fetcher.rss_fetcher import RSSFetcher

    fetcher = RSSFetcher()

    try:
        result = asyncio.run(
            fetcher.fetch_all(DEFAULT_FINANCE_SOURCES, force_refresh=True)
        )
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "articles": [],
            "total": 0,
        }

    articles = [
        {
            "title": a.title,
            "source": a.source,
            "url": a.source_url,
            "published_at": a.published_at,
            "snippet": a.content[:300] if a.content else "",
        }
        for a in result.articles[:max_articles]
    ]

    return {
        "status": "success",
        "articles": articles,
        "total": len(articles),
        "sources_processed": result.sources_processed,
        "sources_failed": result.sources_failed,
    }
