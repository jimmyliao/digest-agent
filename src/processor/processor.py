import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Set

from src.fetcher.rss_fetcher import RawArticle

logger = logging.getLogger(__name__)


@dataclass
class ProcessedArticle:
    """An article cleaned, deduplicated, and ready for the database."""

    id: str = ""
    title: str = ""
    content: str = ""
    source: str = ""
    source_url: str = ""
    published_at: Optional[str] = None
    content_hash: str = ""
    url_hash: str = ""
    tags: List[str] = field(default_factory=list)
    language: str = ""
    publish_status: str = "pending"
    metadata: dict = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class ProcessResult:
    """Aggregated result of processing a batch of raw articles."""

    processed: List[ProcessedArticle] = field(default_factory=list)
    duplicates_skipped: int = 0
    invalid_skipped: int = 0
    total_input: int = 0

    @property
    def total_processed(self) -> int:
        return len(self.processed)


class ArticleProcessor:
    """Processes raw articles into clean, deduplicated, database-ready form."""

    def __init__(self, known_hashes: Optional[Set[str]] = None):
        self.known_hashes: Set[str] = known_hashes or set()

    def process_batch(self, raw_articles: List[RawArticle]) -> ProcessResult:
        """Process a list of raw articles."""
        result = ProcessResult(total_input=len(raw_articles))

        for raw in raw_articles:
            if not self._validate(raw):
                result.invalid_skipped += 1
                continue

            content_hash = self._compute_content_hash(raw.title, raw.content)
            if content_hash in self.known_hashes:
                result.duplicates_skipped += 1
                continue

            self.known_hashes.add(content_hash)

            processed = ProcessedArticle(
                title=self._clean_text(raw.title),
                content=self._clean_html(raw.content),
                source=raw.source,
                source_url=raw.source_url,
                url_hash=raw.url_hash,
                published_at=raw.published_at,
                content_hash=content_hash,
                tags=self._extract_tags(raw),
                language=self._detect_language(raw.title + " " + raw.content),
                metadata=raw.metadata,
            )
            result.processed.append(processed)

        logger.info(
            "Processed %d/%d articles (%d duplicates, %d invalid)",
            result.total_processed,
            result.total_input,
            result.duplicates_skipped,
            result.invalid_skipped,
        )
        return result

    def process_single(self, raw: RawArticle) -> Optional[ProcessedArticle]:
        """Process a single raw article. Returns None if invalid or duplicate."""
        result = self.process_batch([raw])
        return result.processed[0] if result.processed else None

    def _validate(self, raw: RawArticle) -> bool:
        if not raw.title or not raw.title.strip():
            return False
        if not raw.source_url or not raw.source_url.strip():
            return False
        return True

    def _compute_content_hash(self, title: str, content: str) -> str:
        normalized = (title.strip().lower() + content.strip().lower()).encode()
        return hashlib.sha256(normalized).hexdigest()[:16]

    def _clean_html(self, html: str) -> str:
        if not html:
            return ""
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _detect_language(self, text: str) -> str:
        if not text:
            return "en"
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        total_alpha = len(re.findall(r"\w", text)) or 1
        if cjk_count / total_alpha > 0.1:
            return "zh"
        return "en"

    def _extract_tags(self, raw: RawArticle) -> List[str]:
        tags = []
        feed_tags = raw.metadata.get("feed_tags", [])
        for tag in feed_tags:
            cleaned = tag.strip()
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
        return tags
