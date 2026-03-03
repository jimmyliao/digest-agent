from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.fetcher.rss_fetcher import RSSFetcher
from src.llm.gemini_summarizer import GeminiSummarizer, SummaryResult
from src.models.database import ArticleDB, SessionLocal
from src.processor.processor import ArticleProcessor
from src.publishers.base_publisher import (
    MultiPublishResult as ChannelMultiResult,
)
from src.publishers.discord_publisher import DiscordPublisher
from src.publishers.email_publisher import EmailPublisher
from src.publishers.line_publisher import LinePublisher
from src.publishers.multi_channel_publisher import MultiChannelPublisher
from src.publishers.telegram_publisher import TelegramPublisher

logger = logging.getLogger(__name__)


@dataclass
class FetchResult:
    source_ids: List[str] = field(default_factory=list)
    articles_fetched: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True


@dataclass
class SummarizeResult:
    article_ids: List[str] = field(default_factory=list)
    summaries_generated: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True


@dataclass
class PublishResult:
    channels: List[str] = field(default_factory=list)
    published_count: int = 0
    errors: List[str] = field(default_factory=list)
    success: bool = True
    channel_results: Optional[ChannelMultiResult] = None


@dataclass
class FullPipelineResult:
    fetch: FetchResult = field(default_factory=FetchResult)
    summarize: SummarizeResult = field(default_factory=SummarizeResult)
    publish: PublishResult = field(default_factory=PublishResult)
    success: bool = True


def _get_channel_configs() -> Dict[str, Dict]:
    """Build channel configs: DB values override env var defaults."""
    import json
    from src.models.database import SessionLocal, ChannelConfigDB

    # Env var defaults
    env_configs = {
        "email": {
            "smtp_server": os.environ.get("SMTP_SERVER", ""),
            "smtp_port": os.environ.get("SMTP_PORT", "587"),
            "username": os.environ.get("SMTP_USER", ""),
            "password": os.environ.get("SMTP_PASSWORD", ""),
            "from_address": os.environ.get("SMTP_USER", ""),
            "from_name": os.environ.get("SMTP_FROM_NAME", "Digest Agent"),
            "to_address": os.environ.get("EMAIL_TO", "") or os.environ.get("SMTP_USER", ""),
        },
        "telegram": {
            "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            "chat_id": os.environ.get("TELEGRAM_CHAT_ID", ""),
        },
        "line": {
            "channel_access_token": os.environ.get("LINE_CHANNEL_TOKEN", ""),
            "to": os.environ.get("LINE_USER_ID", ""),
        },
        "discord": {
            "webhook_url": os.environ.get("DISCORD_WEBHOOK_URL", ""),
        },
    }

    # Override with DB values (non-empty DB fields win)
    try:
        db = SessionLocal()
        try:
            rows = db.query(ChannelConfigDB).all()
            for row in rows:
                db_cfg = json.loads(row.config_json) if row.config_json else {}
                if row.id in env_configs:
                    for key, value in db_cfg.items():
                        if value:  # only override if DB value is non-empty
                            env_configs[row.id][key] = value
        finally:
            db.close()
    except Exception as e:
        logger.warning("Could not load channel configs from DB, using env vars: %s", e)

    # Email: if to_address not set, default to username (send to self)
    email_cfg = env_configs["email"]
    if not email_cfg.get("to_address") and email_cfg.get("username"):
        email_cfg["to_address"] = email_cfg["username"]
        email_cfg["from_address"] = email_cfg["username"]

    return env_configs


def build_multi_publisher() -> MultiChannelPublisher:
    """Build a MultiChannelPublisher with all available channels registered."""
    configs = _get_channel_configs()
    multi = MultiChannelPublisher()
    multi.register_publisher("email", EmailPublisher(config=configs["email"]))
    multi.register_publisher("telegram", TelegramPublisher(config=configs["telegram"]))
    multi.register_publisher("line", LinePublisher(config=configs["line"]))
    multi.register_publisher("discord", DiscordPublisher(config=configs["discord"]))
    return multi


class DigestOrchestrator:
    """Orchestrates the full digest pipeline: fetch -> summarize -> publish."""

    def __init__(self):
        self.multi_publisher = build_multi_publisher()
        self.summarizer = GeminiSummarizer()
        self.fetcher = RSSFetcher()
        self.processor = ArticleProcessor()

    def _save_articles(self, processed_articles: list, force_refresh: bool = False) -> int:
        """Persist processed articles to DB, skipping duplicates by source_url."""
        import json
        from datetime import datetime, timezone

        db = SessionLocal()
        saved = 0
        try:
            for article in processed_articles:
                exists = db.query(ArticleDB).filter(
                    ArticleDB.source_url == article.source_url
                ).first()
                if exists and not force_refresh:
                    continue
                if exists and force_refresh:
                    db.delete(exists)
                    db.flush()

                row = ArticleDB(
                    id=article.id,
                    title=article.title,
                    content=article.content,
                    source=article.source,
                    source_url=article.source_url,
                    url_hash=article.url_hash,
                    content_hash=article.content_hash,
                    published_at=datetime.fromisoformat(article.published_at) if article.published_at else None,
                    tags=json.dumps(article.tags),
                    language=article.language,
                    publish_status="pending",
                    metadata_json=json.dumps(article.metadata),
                )
                db.add(row)
                saved += 1

            db.commit()
            logger.info("Saved %d new articles to DB", saved)
        except Exception as e:
            db.rollback()
            logger.exception("Failed to save articles: %s", e)
        finally:
            db.close()
        return saved

    async def run_fetch_pipeline(
        self,
        sources: list | None = None,
        source_ids: List[str] | None = None,
        force_refresh: bool = False,
    ) -> FetchResult:
        """Fetch articles from RSS sources and process them.

        Args:
            sources: List of source dicts with 'id', 'url', 'enabled' keys.
            source_ids: Legacy parameter for backwards compatibility.
            force_refresh: Skip deduplication if True.
        """
        logger.info("Starting fetch pipeline for sources: %s", source_ids or "all")
        if not sources:
            return FetchResult(source_ids=source_ids or [], success=True)

        try:
            fetch_result = await self.fetcher.fetch_all(sources, force_refresh=force_refresh)
            process_result = self.processor.process_batch(fetch_result.articles)

            # Persist processed articles to DB
            saved = self._save_articles(process_result.processed, force_refresh=force_refresh)

            return FetchResult(
                source_ids=[s.get("id", "") for s in sources],
                articles_fetched=saved,
                errors=fetch_result.errors,
                success=fetch_result.sources_failed == 0,
            )
        except Exception as e:
            logger.exception("Fetch pipeline failed: %s", e)
            return FetchResult(
                source_ids=source_ids or [],
                errors=[str(e)],
                success=False,
            )

    async def run_summarize_pipeline(
        self,
        articles: list | None = None,
        article_ids: List[str] | None = None,
        language: str = "zh-TW",
    ) -> SummarizeResult:
        """Generate AI summaries for articles using GeminiSummarizer.

        Args:
            articles: List of article dicts with 'title' and 'content'.
            article_ids: Legacy parameter for backwards compatibility.
            language: Target language (default: zh-TW).
        """
        logger.info("Starting summarize pipeline for %d articles", len(articles or []))
        if not articles:
            return SummarizeResult(article_ids=article_ids or [], success=True)

        try:
            summaries = await self.summarizer.summarize_batch(articles)
            errors = [
                s.raw_response
                for s in summaries
                if s.raw_response and s.raw_response.startswith("ERROR:")
            ]

            return SummarizeResult(
                article_ids=article_ids or [a.get("id", "") for a in articles],
                summaries_generated=len(summaries) - len(errors),
                errors=errors,
                success=len(errors) == 0,
            )
        except Exception as e:
            logger.exception("Summarize pipeline failed: %s", e)
            return SummarizeResult(
                article_ids=article_ids or [],
                errors=[str(e)],
                success=False,
            )

    async def summarize_pending(
        self,
        articles: list,
        language: str = "zh-TW",
    ) -> List[SummaryResult]:
        """Summarize a list of articles and return SummaryResult objects.

        Convenience method for direct API route integration.
        """
        return await self.summarizer.summarize_batch(
            [{"title": a.get("title", ""), "content": a.get("content", "")} for a in articles]
        )

    async def run_publish_pipeline(
        self,
        articles: list | None = None,
        channels: List[str] | None = None,
    ) -> PublishResult:
        """Publish articles to configured channels via MultiChannelPublisher.

        Args:
            articles: List of article dicts (title, summary, url, source, tags).
            channels: Target channel IDs. Defaults to all registered channels.
        """
        if not articles:
            logger.warning("No articles to publish")
            return PublishResult(channels=channels or [], success=True)

        target_channels = channels or self.multi_publisher.list_channels()
        logger.info(
            "Starting publish pipeline: %d articles → %s",
            len(articles), target_channels,
        )

        try:
            multi_result = await self.multi_publisher.publish(
                articles=articles,
                channels=target_channels,
                use_retry=True,
            )

            errors = [
                f"[{r.channel}] {r.error}"
                for r in multi_result.results
                if not r.success
            ]

            overall_success = multi_result.total_failed == 0

            logger.info(
                "Publish pipeline complete: %d success, %d failed",
                multi_result.total_success, multi_result.total_failed,
            )

            return PublishResult(
                channels=target_channels,
                published_count=multi_result.total_success,
                errors=errors,
                success=overall_success,
                channel_results=multi_result,
            )

        except Exception as e:
            logger.exception("Publish pipeline failed: %s", e)
            return PublishResult(
                channels=target_channels,
                errors=[str(e)],
                success=False,
            )

    async def run_full_pipeline(
        self,
        sources: list | None = None,
        channels: List[str] | None = None,
    ) -> FullPipelineResult:
        """Run the complete digest pipeline: fetch -> summarize -> publish.

        Args:
            sources: RSS source dicts. If None, fetch is skipped (returns empty).
            channels: Publish channels. Defaults to all registered.
        """
        logger.info("Starting full digest pipeline")

        # Stage 1: Fetch
        fetch_result = await self.run_fetch_pipeline(sources=sources)
        if not fetch_result.success:
            return FullPipelineResult(fetch=fetch_result, success=False)

        # Stage 2: Summarize (uses processor's last batch if available)
        articles_for_summary = [
            {"title": a.title, "content": a.content}
            for a in (self.processor.process_batch([]).processed if not sources else [])
        ]
        summarize_result = await self.run_summarize_pipeline(articles=articles_for_summary)

        # Stage 3: Publish
        publish_result = await self.run_publish_pipeline(channels=channels)

        return FullPipelineResult(
            fetch=fetch_result,
            summarize=summarize_result,
            publish=publish_result,
            success=publish_result.success,
        )
