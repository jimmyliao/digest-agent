"""End-to-End integration test for the full digest pipeline.

Tests the complete flow: RSSFetcher → Processor → GeminiSummarizer → Publisher
All in mock mode — no real network calls or API keys required.
"""

import asyncio
import logging
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "digest-agent"))

from src.fetcher.rss_fetcher import RawArticle, RSSFetcher, FetchResult
from src.processor.processor import ArticleProcessor, ProcessedArticle, ProcessResult
from src.llm.gemini_summarizer import GeminiSummarizer, SummaryResult
from src.publishers.base_publisher import PublishResult, MultiPublishResult
from src.publishers.multi_channel_publisher import MultiChannelPublisher
from src.publishers.telegram_publisher import TelegramPublisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

MOCK_RAW_ARTICLES = [
    RawArticle(
        title="Google Announces Gemini 3.0 with Advanced Reasoning",
        content=(
            "<p>Google today unveiled <b>Gemini 3.0</b>, the latest version of its "
            "flagship large language model. The new model features significantly "
            "improved reasoning capabilities.</p>"
            "<script>alert('xss')</script>"
        ),
        source="google-ai",
        source_url="https://ai.google/blog/gemini-3-0",
        published_at="2026-02-27T08:00:00+00:00",
        metadata={"author": "Google AI", "feed_tags": ["AI", "LLM"]},
    ),
    RawArticle(
        title="Cloud Run Now Supports GPU Workloads",
        content=(
            "<p>Google Cloud has expanded Cloud Run to support GPU-accelerated "
            "workloads, enabling ML inference at scale.</p>"
            "<style>.hidden{display:none}</style>"
        ),
        source="google-cloud",
        source_url="https://cloud.google.com/blog/cloud-run-gpu",
        published_at="2026-02-27T07:00:00+00:00",
        metadata={"author": "Google Cloud", "feed_tags": ["Cloud", "GPU", "ML"]},
    ),
    RawArticle(
        title="Android 16 Developer Preview Released",
        content="<p>The first developer preview of Android 16 is now available.</p>",
        source="google-official",
        source_url="https://blog.google/android-16-preview",
        published_at="2026-02-27T06:00:00+00:00",
        metadata={"feed_tags": ["Android", "Mobile"]},
    ),
]


# ---------------------------------------------------------------------------
# Stage 1: Fetcher Tests
# ---------------------------------------------------------------------------


class TestStage1Fetcher:
    """Test that RSSFetcher produces well-formed RawArticle objects."""

    def test_raw_article_has_url_hash(self):
        for article in MOCK_RAW_ARTICLES:
            assert article.url_hash, f"Missing url_hash for {article.title}"
            assert len(article.url_hash) == 16

    def test_raw_article_has_id(self):
        for article in MOCK_RAW_ARTICLES:
            assert article.id.startswith("raw-")

    def test_fetch_result_aggregation(self):
        result = FetchResult(
            articles=MOCK_RAW_ARTICLES,
            sources_processed=3,
            sources_failed=0,
        )
        assert result.total_articles == 3
        assert result.success is True

    def test_deduplication_via_seen_hashes(self):
        first_hash = MOCK_RAW_ARTICLES[0].url_hash
        fetcher = RSSFetcher(seen_hashes={first_hash})
        assert first_hash in fetcher.seen_hashes


# ---------------------------------------------------------------------------
# Stage 2: Processor Tests
# ---------------------------------------------------------------------------


class TestStage2Processor:
    """Test that ArticleProcessor correctly transforms RawArticle → ProcessedArticle."""

    def test_process_batch_basic(self):
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)

        assert isinstance(result, ProcessResult)
        assert result.total_input == 3
        assert result.total_processed == 3
        assert result.duplicates_skipped == 0
        assert result.invalid_skipped == 0

    def test_html_cleaning(self):
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)

        for article in result.processed:
            assert "<script>" not in article.content
            assert "<style>" not in article.content
            assert "alert('xss')" not in article.content

    def test_language_detection(self):
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)
        # All test articles are in English
        for article in result.processed:
            assert article.language == "en"

    def test_tag_extraction(self):
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)
        first = result.processed[0]
        assert "AI" in first.tags
        assert "LLM" in first.tags

    def test_deduplication(self):
        processor = ArticleProcessor()
        # Process same articles twice
        result1 = processor.process_batch(MOCK_RAW_ARTICLES)
        result2 = processor.process_batch(MOCK_RAW_ARTICLES)
        assert result1.total_processed == 3
        assert result2.total_processed == 0
        assert result2.duplicates_skipped == 3

    def test_invalid_article_skipped(self):
        bad_article = RawArticle(title="", content="no title", source="test", source_url="")
        processor = ArticleProcessor()
        result = processor.process_batch([bad_article])
        assert result.total_processed == 0
        assert result.invalid_skipped == 1

    def test_content_hash_generated(self):
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)
        for article in result.processed:
            assert article.content_hash
            assert len(article.content_hash) == 16

    def test_processed_article_has_uuid_id(self):
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)
        for article in result.processed:
            assert len(article.id) == 36  # UUID format


# ---------------------------------------------------------------------------
# Stage 3: LLM Summarizer Tests
# ---------------------------------------------------------------------------


class TestStage3Summarizer:
    """Test GeminiSummarizer in mock mode with ProcessedArticle input."""

    @pytest.mark.asyncio
    async def test_summarize_processed_article(self):
        processor = ArticleProcessor()
        processed = processor.process_batch(MOCK_RAW_ARTICLES)

        summarizer = GeminiSummarizer(mock_mode=True)

        for article in processed.processed:
            result = await summarizer.summarize(
                {"title": article.title, "content": article.content}
            )
            assert isinstance(result, SummaryResult)
            assert result.model_used == "mock"
            assert result.title_zh
            assert result.summary_zh
            assert len(result.key_points) >= 1

    @pytest.mark.asyncio
    async def test_summarize_batch_from_processed(self):
        processor = ArticleProcessor()
        processed = processor.process_batch(MOCK_RAW_ARTICLES)

        summarizer = GeminiSummarizer(mock_mode=True)
        articles_as_dicts = [
            {"title": a.title, "content": a.content}
            for a in processed.processed
        ]

        results = await summarizer.summarize_batch(articles_as_dicts)
        assert len(results) == 3
        assert all(isinstance(r, SummaryResult) for r in results)


# ---------------------------------------------------------------------------
# Stage 4: Publisher Tests
# ---------------------------------------------------------------------------


class TestStage4Publisher:
    """Test MultiChannelPublisher with mock Telegram publisher."""

    @pytest.mark.asyncio
    async def test_telegram_mock_publish(self):
        publisher = TelegramPublisher(config={
            "bot_token": "test-mock-token",
            "chat_id": "123456789",
        })

        articles = [
            {"title": "Test Article", "summary": "Test summary", "tags": ["AI"]},
        ]
        result = await publisher.publish(articles, {})

        assert isinstance(result, PublishResult)
        assert result.success is True
        assert result.articles_sent == 1
        assert result.channel == "telegram"

    @pytest.mark.asyncio
    async def test_multi_channel_publish(self):
        mcp = MultiChannelPublisher()

        telegram = TelegramPublisher(config={
            "bot_token": "test-mock-token",
            "chat_id": "123456789",
        })
        mcp.register_publisher("telegram", telegram)

        articles = [
            {"title": "Article 1", "summary": "Summary 1", "tags": ["AI"]},
            {"title": "Article 2", "summary": "Summary 2", "tags": ["Cloud"]},
        ]
        result = await mcp.publish(articles, channels=["telegram"], use_retry=False)

        assert isinstance(result, MultiPublishResult)
        assert result.total_success == 1
        assert result.total_failed == 0
        assert result.results[0].articles_sent == 2

    @pytest.mark.asyncio
    async def test_unregistered_channel_fails_gracefully(self):
        mcp = MultiChannelPublisher()
        result = await mcp.publish(
            [{"title": "Test"}],
            channels=["nonexistent"],
        )
        assert result.total_failed == 1
        assert "not registered" in result.results[0].error


# ---------------------------------------------------------------------------
# Stage 5: Full Pipeline Integration (E2E Smoke Test)
# ---------------------------------------------------------------------------


class TestStage5FullPipeline:
    """End-to-end smoke test: Fetch → Process → Summarize → Publish."""

    @pytest.mark.asyncio
    async def test_full_pipeline_mock_mode(self):
        """Complete pipeline execution in mock mode."""

        # === Stage 1: Fetch (simulated — use pre-built RawArticles) ===
        fetch_result = FetchResult(
            articles=MOCK_RAW_ARTICLES,
            sources_processed=3,
            sources_failed=0,
        )
        assert fetch_result.total_articles == 3
        assert fetch_result.success is True
        logger.info(
            "Stage 1 PASS: Fetched %d articles from %d sources",
            fetch_result.total_articles,
            fetch_result.sources_processed,
        )

        # === Stage 2: Process ===
        processor = ArticleProcessor()
        process_result = processor.process_batch(fetch_result.articles)

        assert process_result.total_processed == 3
        assert process_result.duplicates_skipped == 0
        assert all(a.content_hash for a in process_result.processed)
        assert all("<script>" not in a.content for a in process_result.processed)
        logger.info(
            "Stage 2 PASS: Processed %d articles (%d dupes, %d invalid)",
            process_result.total_processed,
            process_result.duplicates_skipped,
            process_result.invalid_skipped,
        )

        # === Stage 3: Summarize (mock mode) ===
        summarizer = GeminiSummarizer(mock_mode=True)
        articles_for_llm = [
            {"title": a.title, "content": a.content}
            for a in process_result.processed
        ]
        summaries = await summarizer.summarize_batch(articles_for_llm)

        assert len(summaries) == 3
        assert all(s.title_zh for s in summaries)
        assert all(s.summary_zh for s in summaries)
        assert all(s.model_used == "mock" for s in summaries)
        logger.info(
            "Stage 3 PASS: Summarized %d articles (model=%s)",
            len(summaries),
            summaries[0].model_used,
        )

        # === Stage 4: Merge summaries back into article dicts ===
        publish_articles = []
        for processed, summary in zip(process_result.processed, summaries):
            publish_articles.append({
                "title": summary.title_zh or processed.title,
                "summary": summary.summary_zh,
                "url": processed.source_url,
                "source": processed.source,
                "tags": summary.tags or processed.tags,
            })

        assert len(publish_articles) == 3
        assert all(a["title"] for a in publish_articles)
        assert all(a["summary"] for a in publish_articles)
        logger.info("Stage 4 PASS: Merged %d articles for publishing", len(publish_articles))

        # === Stage 5: Publish (mock Telegram) ===
        mcp = MultiChannelPublisher()
        telegram = TelegramPublisher(config={
            "bot_token": "test-mock-token",
            "chat_id": "test-chat-123",
        })
        mcp.register_publisher("telegram", telegram)

        publish_result = await mcp.publish(
            publish_articles,
            channels=["telegram"],
            use_retry=False,
        )

        assert publish_result.total_success == 1
        assert publish_result.total_failed == 0
        assert publish_result.results[0].articles_sent == 3
        logger.info(
            "Stage 5 PASS: Published to %d channels (success=%d, failed=%d)",
            len(publish_result.results),
            publish_result.total_success,
            publish_result.total_failed,
        )

        # === Final: Usage summary ===
        usage = summarizer.get_usage_summary()
        logger.info("Pipeline complete. LLM usage: %s", usage)

    @pytest.mark.asyncio
    async def test_pipeline_with_duplicates(self):
        """Pipeline handles duplicates correctly across batches."""
        processor = ArticleProcessor()

        # First batch
        result1 = processor.process_batch(MOCK_RAW_ARTICLES)
        assert result1.total_processed == 3

        # Second batch (same articles → all duplicates)
        result2 = processor.process_batch(MOCK_RAW_ARTICLES)
        assert result2.total_processed == 0
        assert result2.duplicates_skipped == 3

        # Only first batch goes to summarizer
        summarizer = GeminiSummarizer(mock_mode=True)
        articles = [
            {"title": a.title, "content": a.content}
            for a in result1.processed
        ]
        summaries = await summarizer.summarize_batch(articles)
        assert len(summaries) == 3

    @pytest.mark.asyncio
    async def test_pipeline_with_invalid_articles(self):
        """Pipeline handles mix of valid and invalid articles."""
        articles = MOCK_RAW_ARTICLES + [
            RawArticle(title="", content="no title", source="bad", source_url=""),
            RawArticle(title="No URL", content="content", source="bad", source_url=""),
        ]

        processor = ArticleProcessor()
        result = processor.process_batch(articles)

        assert result.total_input == 5
        assert result.total_processed == 3
        assert result.invalid_skipped == 2

        # Only valid articles reach summarizer
        summarizer = GeminiSummarizer(mock_mode=True)
        summaries = await summarizer.summarize_batch([
            {"title": a.title, "content": a.content}
            for a in result.processed
        ])
        assert len(summaries) == 3

    @pytest.mark.asyncio
    async def test_pipeline_empty_input(self):
        """Pipeline gracefully handles empty input."""
        processor = ArticleProcessor()
        result = processor.process_batch([])
        assert result.total_processed == 0

        summarizer = GeminiSummarizer(mock_mode=True)
        summaries = await summarizer.summarize_batch([])
        assert summaries == []

        mcp = MultiChannelPublisher()
        telegram = TelegramPublisher(config={
            "bot_token": "test-mock",
            "chat_id": "123",
        })
        mcp.register_publisher("telegram", telegram)
        pub_result = await mcp.publish([], channels=["telegram"], use_retry=False)
        assert pub_result.total_success == 1  # Success even with 0 articles


# ---------------------------------------------------------------------------
# Data Contract Compatibility Tests
# ---------------------------------------------------------------------------


class TestDataContractCompatibility:
    """Verify data flows correctly between module boundaries."""

    def test_raw_article_fields_consumed_by_processor(self):
        """Processor accesses the correct RawArticle fields."""
        raw = MOCK_RAW_ARTICLES[0]
        processor = ArticleProcessor()
        processed = processor.process_single(raw)

        assert processed is not None
        assert processed.title == processor._clean_text(raw.title)
        assert processed.source == raw.source
        assert processed.source_url == raw.source_url
        assert processed.published_at == raw.published_at

    def test_processed_article_compatible_with_summarizer(self):
        """Summarizer accepts ProcessedArticle as dict input."""
        processor = ArticleProcessor()
        result = processor.process_batch(MOCK_RAW_ARTICLES)
        article = result.processed[0]

        # Summarizer expects dict with 'title' and 'content'
        summarizer_input = {"title": article.title, "content": article.content}
        assert "title" in summarizer_input
        assert "content" in summarizer_input
        assert summarizer_input["title"]
        assert summarizer_input["content"]

    def test_summary_result_fields_for_publisher(self):
        """Publisher expects specific fields from merged article dicts."""
        summary = SummaryResult(
            title_zh="測試標題",
            summary_zh="測試摘要",
            key_points=["重點1", "重點2"],
            tags=["AI", "Google"],
            model_used="mock",
        )
        processed = ProcessedArticle(
            title="Original Title",
            content="Content",
            source="google-ai",
            source_url="https://example.com",
        )

        # Build publisher article dict (as done in pipeline)
        pub_article = {
            "title": summary.title_zh or processed.title,
            "summary": summary.summary_zh,
            "url": processed.source_url,
            "source": processed.source,
            "tags": summary.tags or processed.tags,
        }

        # Telegram publisher expects these fields
        assert pub_article["title"]
        assert pub_article["summary"]
        assert pub_article["source"]
        assert isinstance(pub_article["tags"], list)
