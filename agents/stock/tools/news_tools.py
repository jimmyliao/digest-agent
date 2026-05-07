"""新聞搜尋工具 — 包裝現有 RSSFetcher 提供個股新聞查詢。

RSS 來源統一由 config/settings.yaml 管理（category: finance_tw），
Phase 1-3 Fetch 和 Phase 4 個股分析共用同一組財經來源。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import requests
import yaml

logger = logging.getLogger(__name__)


def _load_finance_sources() -> list[dict]:
    """從 config/settings.yaml 讀取 category=finance_tw 的 RSS 來源。"""
    settings_path = Path(__file__).resolve().parents[3] / "config" / "settings.yaml"
    if not settings_path.exists():
        return _FALLBACK_SOURCES

    with open(settings_path) as f:
        cfg = yaml.safe_load(f)

    sources = [
        {"id": s["id"], "url": s["url"], "enabled": s.get("enabled", True)}
        for s in cfg.get("sources", [])
        if s.get("category") == "finance_tw" and s.get("enabled", True)
    ]
    return sources if sources else _FALLBACK_SOURCES


# settings.yaml 讀不到時的 fallback
_FALLBACK_SOURCES = [
    {
        "id": "yahoo-tw-stock",
        "url": "https://tw.stock.yahoo.com/rss",
        "enabled": True,
    },
    {
        "id": "twse-news",
        "url": "https://www.twse.com.tw/rwd/zh/news/feed?type=rss",
        "enabled": True,
    },
    {
        "id": "technews-finance",
        "url": "https://technews.tw/feed/",
        "enabled": True,
    },
]


def search_db_articles(company_name: str, ticker: str = "", limit: int = 10) -> dict:
    """從 DB 搜尋已抓取的文章（Phase 1-3 Fetch 存入的資料）。
    這是最快的方式，因為資料已經在本地 DB，不需要重新抓取 RSS。

    若環境變數 DIGEST_API_URL 有設定，先嘗試 HTTP 模式呼叫 remote
    `/api/articles` endpoint；失敗（5xx / timeout / network error）時
    自動 fallback 至本地 SQLite。

    Args:
        company_name: 公司名稱（例如「台積電」）
        ticker: 選填的股票代號（例如 "2330"）
        limit: 最多回傳幾篇，預設 10

    Returns:
        包含搜尋結果的字典
    """
    api_url = os.environ.get("DIGEST_API_URL")
    using_http = bool(api_url)
    if using_http:
        print("[search_db_articles] mode=HTTP")
    else:
        print("[search_db_articles] mode=SQLite (local_db)")

    if using_http:
        # If the remote UI is gated by HTTP Basic Auth (Cloud Run + Next.js
        # middleware), the agent must authenticate too. Read creds from
        # DIGEST_API_USER / DIGEST_API_PASSWORD; absent → unauthenticated
        # request (works only against ungated dev deployments).
        api_user = os.environ.get("DIGEST_API_USER")
        api_pass = os.environ.get("DIGEST_API_PASSWORD")
        auth = (api_user, api_pass) if api_user and api_pass else None
        try:
            resp = requests.get(
                f"{api_url.rstrip('/')}/api/articles",
                params={"company": company_name, "limit": limit},
                timeout=10,
                auth=auth,
            )
            if 200 <= resp.status_code < 300:
                payload = resp.json()
                remote_articles = payload.get("articles", []) or []
                # Normalize remote schema to our return schema
                normalized = []
                for a in remote_articles:
                    content = a.get("content") or ""
                    summary = a.get("summary") or ""
                    normalized.append(
                        {
                            "title": a.get("title"),
                            "source": a.get("source"),
                            "url": a.get("source_url") or a.get("url"),
                            "published_at": a.get("published_at"),
                            "snippet": content[:300] if content else "",
                            "has_summary": bool(summary),
                            "summary_preview": summary[:200] if summary else None,
                        }
                    )
                total_in_db = payload.get("count", len(normalized))
                return {
                    "status": "success",
                    "source": "remote_api",
                    "company": company_name,
                    "ticker": ticker,
                    "articles": normalized,
                    "total_matched": len(normalized),
                    "total_in_db": total_in_db,
                }
            else:
                logger.warning(
                    "DIGEST_API_URL returned status %s; falling back to local SQLite",
                    resp.status_code,
                )
        except requests.Timeout:
            logger.warning("DIGEST_API_URL request timed out; falling back to local SQLite")
        except requests.RequestException as e:
            logger.warning(
                "DIGEST_API_URL request failed (%s); falling back to local SQLite", e
            )
        except Exception as e:  # JSON parse or unexpected
            logger.warning(
                "DIGEST_API_URL response handling failed (%s); falling back to local SQLite",
                e,
            )

    # Local SQLite fallback. The deployed-on-GEAP code path does NOT bundle
    # src/ (extra_packages=["agents"] only), so this import will fail in
    # production. Catch and return a graceful empty result rather than
    # crashing the agent stream.
    try:
        from src.models.database import SessionLocal, ArticleDB
    except ImportError as e:
        logger.warning(
            "src/ unavailable (likely deployed env without bundled src). "
            "Returning empty result. Cause: %s",
            e,
        )
        return {
            "status": "success",
            "source": "local_db_unavailable",
            "company": company_name,
            "ticker": ticker,
            "articles": [],
            "total_matched": 0,
            "total_in_db": 0,
        }

    keywords = [company_name]
    if ticker:
        keywords.append(ticker)

    db = SessionLocal()
    try:
        articles = db.query(ArticleDB).order_by(ArticleDB.created_at.desc()).all()

        matched = []
        for a in articles:
            text = f"{a.title} {a.content or ''}"
            if any(kw in text for kw in keywords):
                matched.append(
                    {
                        "title": a.title,
                        "source": a.source,
                        "url": a.source_url,
                        "published_at": str(a.published_at) if a.published_at else None,
                        "snippet": (a.content or "")[:300],
                        "has_summary": bool(a.summary),
                        "summary_preview": (a.summary or "")[:200] if a.summary else None,
                    }
                )
                if len(matched) >= limit:
                    break

        return {
            "status": "success",
            "source": "local_db",
            "company": company_name,
            "ticker": ticker,
            "articles": matched,
            "total_matched": len(matched),
            "total_in_db": len(articles),
        }
    finally:
        db.close()


def search_company_news(company_name: str, ticker: str = "") -> dict:
    """搜尋特定公司的近期新聞。會從 RSS 財經來源抓取後篩選含有公司名稱或代號的文章。

    Args:
        company_name: 公司名稱（中文或英文皆可，例如「台積電」或「TSMC」）
        ticker: 選填的股票代號（例如 "2330"）

    Returns:
        包含搜尋結果的字典，含 articles 列表與 metadata
    """
    try:
        from src.fetcher.rss_fetcher import RSSFetcher
    except ImportError as e:
        logger.warning(
            "src/fetcher unavailable (likely deployed env). RSS fallback skipped. Cause: %s",
            e,
        )
        return {
            "status": "success",
            "source": "rss_unavailable",
            "company": company_name,
            "ticker": ticker,
            "articles": [],
            "total": 0,
        }

    fetcher = RSSFetcher()

    try:
        result = asyncio.run(
            fetcher.fetch_all(_load_finance_sources(), force_refresh=True)
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
    try:
        from src.fetcher.rss_fetcher import RSSFetcher
    except ImportError as e:
        logger.warning(
            "src/fetcher unavailable (likely deployed env). RSS feed fetch skipped. Cause: %s",
            e,
        )
        return {
            "status": "success",
            "source": "rss_unavailable",
            "articles": [],
            "total": 0,
        }

    fetcher = RSSFetcher()

    try:
        result = asyncio.run(
            fetcher.fetch_all(_load_finance_sources(), force_refresh=True)
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
