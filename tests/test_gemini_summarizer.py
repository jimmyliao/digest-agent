"""Tests for GeminiSummarizer — uses mocks only, no real API calls."""

import asyncio
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "digest-agent"))

from src.llm.gemini_summarizer import GeminiSummarizer, SummaryResult, RateLimiter
from src.llm.prompt_manager import PromptManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ARTICLE = {
    "title": "Google Announces Gemini 3.0 with Advanced Reasoning",
    "content": (
        "Google today unveiled Gemini 3.0, the latest version of its flagship "
        "large language model. The new model features significantly improved "
        "reasoning capabilities, better code generation, and native multimodal "
        "understanding. Sundar Pichai said it represents a major leap forward."
    ),
}

VALID_JSON_RESPONSE = json.dumps(
    {
        "title_zh": "Google 發布 Gemini 3.0 搭載進階推理能力",
        "summary_zh": "Google推出Gemini 3.0，具備更強推理、程式碼生成和多模態能力。",
        "key_points": [
            "Gemini 3.0 推理能力大幅提升",
            "程式碼生成效能改善",
            "原生多模態理解",
        ],
        "tags": ["AI", "Google", "Gemini", "LLM"],
    }
)


def _make_mock_response(text: str = VALID_JSON_RESPONSE, input_tokens: int = 500, output_tokens: int = 150):
    """Build a mock Gemini API response object."""
    resp = MagicMock()
    resp.text = text
    resp.usage_metadata = MagicMock()
    resp.usage_metadata.prompt_token_count = input_tokens
    resp.usage_metadata.candidates_token_count = output_tokens
    return resp


# ---------------------------------------------------------------------------
# PromptManager Tests
# ---------------------------------------------------------------------------


class TestPromptManager:
    def test_version_is_set(self):
        pm = PromptManager()
        assert pm.VERSION == "v1"

    def test_system_prompt_not_empty(self):
        pm = PromptManager()
        assert len(pm.SYSTEM_PROMPT) > 50

    def test_get_user_prompt_contains_title_and_content(self):
        pm = PromptManager()
        prompt = pm.get_user_prompt("My Title", "My Content")
        assert "My Title" in prompt
        assert "My Content" in prompt

    def test_get_user_prompt_truncates_content(self):
        pm = PromptManager()
        long_content = "x" * 5000
        prompt = pm.get_user_prompt("Title", long_content)
        # Content truncated to 3000 chars
        assert "x" * 3000 in prompt
        assert "x" * 3001 not in prompt


# ---------------------------------------------------------------------------
# SummaryResult Tests
# ---------------------------------------------------------------------------


class TestSummaryResult:
    def test_defaults(self):
        sr = SummaryResult()
        assert sr.title_zh == ""
        assert sr.summary_zh == ""
        assert sr.key_points == []
        assert sr.tags == []
        assert sr.language == "zh-TW"
        assert sr.model_used == "gemini-2.5-flash"
        assert sr.cost_estimate_usd == 0.0
        assert sr.raw_response is None

    def test_custom_values(self):
        sr = SummaryResult(
            title_zh="測試標題",
            summary_zh="測試摘要",
            key_points=["點1", "點2"],
            tags=["AI"],
        )
        assert sr.title_zh == "測試標題"
        assert len(sr.key_points) == 2


# ---------------------------------------------------------------------------
# Mock Mode Tests
# ---------------------------------------------------------------------------


class TestMockMode:
    def test_auto_mock_when_no_api_key(self):
        summarizer = GeminiSummarizer(api_key="")
        assert summarizer.mock_mode is True

    def test_explicit_mock_mode(self):
        summarizer = GeminiSummarizer(api_key="real-key", mock_mode=True)
        assert summarizer.mock_mode is True

    def test_no_mock_with_api_key(self):
        summarizer = GeminiSummarizer(api_key="real-key")
        assert summarizer.mock_mode is False

    @pytest.mark.asyncio
    async def test_mock_summarize_returns_result(self):
        summarizer = GeminiSummarizer(api_key="", mock_mode=True)
        result = await summarizer.summarize(SAMPLE_ARTICLE)

        assert isinstance(result, SummaryResult)
        assert "[Mock]" in result.title_zh
        assert result.model_used == "mock"
        assert result.cost_estimate_usd == 0.0
        assert len(result.key_points) == 3
        assert "mock" in result.tags

    @pytest.mark.asyncio
    async def test_mock_batch_summarize(self):
        summarizer = GeminiSummarizer(api_key="", mock_mode=True)
        articles = [SAMPLE_ARTICLE, {"title": "Article 2", "content": "Content 2"}]
        results = await summarizer.summarize_batch(articles)

        assert len(results) == 2
        assert all(isinstance(r, SummaryResult) for r in results)
        assert all(r.model_used == "mock" for r in results)


# ---------------------------------------------------------------------------
# Real API (Mocked) Tests
# ---------------------------------------------------------------------------


def _make_summarizer_with_mocks(mock_response):
    """Create a GeminiSummarizer with _get_model and _call_with_retry mocked."""
    summarizer = GeminiSummarizer(api_key="test-key", mock_mode=False)
    summarizer._get_model = MagicMock(return_value=MagicMock())
    summarizer._call_with_retry = AsyncMock(return_value=mock_response)
    summarizer._rate_limiter = MagicMock()
    summarizer._rate_limiter.acquire = AsyncMock()
    return summarizer


class TestSummarizeWithMockedAPI:
    @pytest.mark.asyncio
    async def test_summarize_parses_json_response(self):
        mock_response = _make_mock_response()
        summarizer = _make_summarizer_with_mocks(mock_response)

        result = await summarizer.summarize(SAMPLE_ARTICLE)

        assert result.title_zh == "Google 發布 Gemini 3.0 搭載進階推理能力"
        assert "Gemini 3.0" in result.summary_zh
        assert len(result.key_points) == 3
        assert "AI" in result.tags
        assert result.cost_estimate_usd > 0
        assert result.raw_response == VALID_JSON_RESPONSE

    @pytest.mark.asyncio
    async def test_summarize_handles_markdown_wrapped_json(self):
        wrapped = "```json\n" + VALID_JSON_RESPONSE + "\n```"
        mock_response = _make_mock_response(text=wrapped)
        summarizer = _make_summarizer_with_mocks(mock_response)

        result = await summarizer.summarize(SAMPLE_ARTICLE)

        assert result.title_zh == "Google 發布 Gemini 3.0 搭載進階推理能力"

    @pytest.mark.asyncio
    async def test_summarize_fallback_on_invalid_json(self):
        mock_response = _make_mock_response(text="This is not JSON at all")
        summarizer = _make_summarizer_with_mocks(mock_response)

        result = await summarizer.summarize(SAMPLE_ARTICLE)

        assert result.summary_zh == "This is not JSON at all"
        assert result.title_zh == ""

    @pytest.mark.asyncio
    async def test_usage_tracking(self):
        mock_response = _make_mock_response(input_tokens=1000, output_tokens=200)
        summarizer = _make_summarizer_with_mocks(mock_response)

        await summarizer.summarize(SAMPLE_ARTICLE)

        assert summarizer.total_input_tokens == 1000
        assert summarizer.total_output_tokens == 200
        assert summarizer.total_cost_usd > 0
        assert summarizer.total_calls == 1

        usage = summarizer.get_usage_summary()
        assert usage["total_calls"] == 1
        assert usage["mock_mode"] is False


# ---------------------------------------------------------------------------
# Retry Logic Tests
# ---------------------------------------------------------------------------


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self):
        """Should retry on 429 errors with exponential backoff."""
        mock_model = MagicMock()
        ok_response = _make_mock_response()

        call_count = 0

        async def side_effect(prompt):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("429 Resource exhausted: rate limit")
            return ok_response

        mock_model.generate_content_async = side_effect

        summarizer = GeminiSummarizer(api_key="test-key", mock_mode=False)
        # Use tiny delays for test speed
        summarizer.BASE_DELAY = 0.01

        result = await summarizer._call_with_retry(mock_model, "test prompt")
        assert result == ok_response
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self):
        """Should NOT retry on non-rate-limit errors."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("Invalid API key")
        )

        summarizer = GeminiSummarizer(api_key="test-key", mock_mode=False)
        summarizer.BASE_DELAY = 0.01

        with pytest.raises(Exception, match="Invalid API key"):
            await summarizer._call_with_retry(mock_model, "test prompt")

        assert mock_model.generate_content_async.call_count == 1

    @pytest.mark.asyncio
    async def test_exhausts_retries(self):
        """Should raise after MAX_RETRIES exhausted."""
        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("429 rate limit exceeded")
        )

        summarizer = GeminiSummarizer(api_key="test-key", mock_mode=False)
        summarizer.BASE_DELAY = 0.01

        with pytest.raises(Exception, match="429"):
            await summarizer._call_with_retry(mock_model, "test prompt")

        assert mock_model.generate_content_async.call_count == 3


# ---------------------------------------------------------------------------
# Batch Processing Tests
# ---------------------------------------------------------------------------


class TestBatchProcessing:
    @pytest.mark.asyncio
    async def test_batch_returns_correct_count(self):
        mock_response = _make_mock_response()
        summarizer = _make_summarizer_with_mocks(mock_response)

        articles = [
            {"title": f"Article {i}", "content": f"Content {i}"}
            for i in range(5)
        ]
        results = await summarizer.summarize_batch(articles, max_concurrent=2)

        assert len(results) == 5
        assert summarizer._call_with_retry.call_count == 5

    @pytest.mark.asyncio
    async def test_batch_handles_partial_failure(self):
        """Batch should return error results for failed articles, not crash."""
        call_count = 0
        ok_response = _make_mock_response()

        async def mock_call_with_retry(model, prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("API error for article 2")
            return ok_response

        summarizer = GeminiSummarizer(api_key="test-key", mock_mode=False)
        summarizer._get_model = MagicMock(return_value=MagicMock())
        summarizer._call_with_retry = mock_call_with_retry
        summarizer._rate_limiter = MagicMock()
        summarizer._rate_limiter.acquire = AsyncMock()

        articles = [
            {"title": f"Article {i}", "content": f"Content {i}"}
            for i in range(3)
        ]
        results = await summarizer.summarize_batch(articles)

        assert len(results) == 3
        # One article should have error
        error_results = [r for r in results if r.raw_response and "ERROR" in r.raw_response]
        assert len(error_results) == 1


# ---------------------------------------------------------------------------
# RateLimiter Tests
# ---------------------------------------------------------------------------


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        limiter = RateLimiter(max_per_minute=5)
        for _ in range(5):
            await limiter.acquire()
        # Should not block for 5 calls

    @pytest.mark.asyncio
    async def test_rate_limiter_tracks_timestamps(self):
        limiter = RateLimiter(max_per_minute=3)
        await limiter.acquire()
        await limiter.acquire()
        assert len(limiter._timestamps) == 2


# ---------------------------------------------------------------------------
# Cost Estimation Tests
# ---------------------------------------------------------------------------


class TestCostEstimation:
    def test_cost_calculation(self):
        summarizer = GeminiSummarizer(api_key="test-key", mock_mode=True)
        mock_response = _make_mock_response(input_tokens=1000, output_tokens=500)
        cost = summarizer._estimate_cost(mock_response)
        # 1000 * 0.00000015 + 500 * 0.0000006 = 0.00015 + 0.0003 = 0.00045
        assert abs(cost - 0.00045) < 0.000001

    def test_cost_with_no_usage_metadata(self):
        summarizer = GeminiSummarizer(api_key="test-key", mock_mode=True)
        mock_response = MagicMock()
        mock_response.usage_metadata = None
        cost = summarizer._estimate_cost(mock_response)
        assert cost == 0.0


# ---------------------------------------------------------------------------
# Article Input Format Tests
# ---------------------------------------------------------------------------


class TestArticleInputFormats:
    @pytest.mark.asyncio
    async def test_dict_input(self):
        summarizer = GeminiSummarizer(mock_mode=True)
        result = await summarizer.summarize({"title": "Test", "content": "Content"})
        assert "Test" in result.title_zh

    @pytest.mark.asyncio
    async def test_object_input(self):
        class FakeArticle:
            title = "Object Title"
            content = "Object Content"

        summarizer = GeminiSummarizer(mock_mode=True)
        result = await summarizer.summarize(FakeArticle())
        assert "Object Title" in result.title_zh
