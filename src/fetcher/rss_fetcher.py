import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RawArticle:
    """A single article fetched from an RSS source."""

    id: str = ""
    title: str = ""
    content: str = ""
    source: str = ""
    source_url: str = ""
    published_at: Optional[str] = None
    url_hash: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.source_url and not self.url_hash:
            self.url_hash = hashlib.sha256(self.source_url.encode()).hexdigest()[:16]
        if not self.id and self.url_hash:
            self.id = f"raw-{self.url_hash}"


@dataclass
class FetchResult:
    """Aggregated result from fetching one or more RSS sources."""

    articles: List[RawArticle] = field(default_factory=list)
    sources_processed: int = 0
    sources_failed: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def total_articles(self) -> int:
        return len(self.articles)

    @property
    def success(self) -> bool:
        return self.sources_failed == 0


class RSSFetcher:
    """Fetches articles from RSS/Atom feeds using feedparser."""

    MAX_CONCURRENT = 5
    FETCH_TIMEOUT = 30

    def __init__(self, seen_hashes: Optional[set] = None):
        self.seen_hashes: set = seen_hashes or set()

    async def fetch_source(self, source_id: str, source_url: str) -> List[RawArticle]:
        """Fetch articles from a single RSS source."""
        try:
            import feedparser
        except ImportError:
            raise ImportError(
                "feedparser package is required. Install with: pip install feedparser"
            )

        logger.info("Fetching RSS source: %s (%s)", source_id, source_url)

        try:
            feed = await asyncio.to_thread(feedparser.parse, source_url)
        except Exception as e:
            raise FetchError(f"Failed to fetch {source_id}: {e}") from e

        if feed.bozo and not feed.entries:
            raise FetchError(
                f"Feed parse error for {source_id}: {feed.bozo_exception}"
            )

        articles = []
        for entry in feed.entries:
            article = self._parse_entry(entry, source_id)
            if article:
                articles.append(article)

        logger.info("Fetched %d articles from %s", len(articles), source_id)
        return articles

    async def fetch_all(
        self, sources: list, force_refresh: bool = False
    ) -> FetchResult:
        """Fetch articles from all enabled sources concurrently."""
        result = FetchResult()
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT)

        async def _fetch_one(source: dict) -> List[RawArticle]:
            async with semaphore:
                source_id = source.get("id", "unknown")
                source_url = source.get("url", "")
                if not source_url:
                    result.errors.append(f"Source {source_id}: missing URL")
                    result.sources_failed += 1
                    return []
                try:
                    return await asyncio.wait_for(
                        self.fetch_source(source_id, source_url),
                        timeout=self.FETCH_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    msg = f"Source {source_id}: timeout after {self.FETCH_TIMEOUT}s"
                    logger.warning(msg)
                    result.errors.append(msg)
                    result.sources_failed += 1
                    return []
                except Exception as e:
                    msg = f"Source {source_id}: {e}"
                    logger.warning(msg)
                    result.errors.append(msg)
                    result.sources_failed += 1
                    return []

        enabled_sources = [s for s in sources if s.get("enabled", True)]
        tasks = [_fetch_one(s) for s in enabled_sources]
        all_results = await asyncio.gather(*tasks)

        for source_articles in all_results:
            result.sources_processed += 1
            for article in source_articles:
                if force_refresh or article.url_hash not in self.seen_hashes:
                    self.seen_hashes.add(article.url_hash)
                    result.articles.append(article)

        logger.info(
            "Fetch complete: %d articles from %d sources (%d failed)",
            result.total_articles,
            result.sources_processed,
            result.sources_failed,
        )
        return result

    def _parse_entry(self, entry, source_id: str) -> Optional[RawArticle]:
        """Convert a feedparser entry into a RawArticle."""
        link = getattr(entry, "link", "")
        if not link:
            return None

        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary or ""

        published_at = None
        for date_field in ("published_parsed", "updated_parsed"):
            parsed = getattr(entry, date_field, None)
            if parsed:
                try:
                    dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                    published_at = dt.isoformat()
                except (ValueError, TypeError):
                    pass
                break

        metadata = {}
        if hasattr(entry, "author"):
            metadata["author"] = entry.author
        if hasattr(entry, "tags"):
            metadata["feed_tags"] = [
                t.get("term", "") for t in entry.tags if isinstance(t, dict)
            ]

        return RawArticle(
            title=getattr(entry, "title", ""),
            content=content,
            source=source_id,
            source_url=link,
            published_at=published_at,
            metadata=metadata,
        )


class FetchError(Exception):
    """Raised when an RSS fetch operation fails."""
