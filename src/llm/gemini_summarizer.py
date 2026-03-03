"""Gemini-based article summarizer with rate limiting and mock mode.

Provides structured Chinese summaries of technology news articles
using Google's Gemini API (gemini-2.5-flash).
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    title_zh: str = ""
    summary_zh: str = ""  # 100字以內
    key_points: List[str] = field(default_factory=list)  # 3-5條
    tags: List[str] = field(default_factory=list)
    language: str = "zh-TW"
    model_used: str = "gemini-2.5-flash"
    cost_estimate_usd: float = 0.0
    raw_response: Optional[str] = None


class RateLimiter:
    """Token-bucket style rate limiter: max N calls per minute."""

    def __init__(self, max_per_minute: int = 10):
        self.max_per_minute = max_per_minute
        self._timestamps: List[float] = []

    async def acquire(self) -> None:
        """Wait until a call slot is available."""
        now = time.monotonic()
        # Remove timestamps older than 60s
        self._timestamps = [t for t in self._timestamps if now - t < 60.0]
        if len(self._timestamps) >= self.max_per_minute:
            wait_time = 60.0 - (now - self._timestamps[0])
            if wait_time > 0:
                logger.info("Rate limit reached (%d/min), waiting %.1fs", self.max_per_minute, wait_time)
                await asyncio.sleep(wait_time)
        self._timestamps.append(time.monotonic())


class GeminiSummarizer:
    """Gemini-based article summarizer.

    Uses Google's Gemini API to generate structured Chinese summaries
    of technology news articles. Falls back to mock mode when
    GEMINI_API_KEY is not set.
    """

    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_CONCURRENT = 3
    RATE_LIMIT_PER_MINUTE = int(os.environ.get("GEMINI_RATE_LIMIT_PER_MINUTE", "14"))

    def __init__(self, api_key: Optional[str] = None, mock_mode: Optional[bool] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model = "gemini-2.5-flash"
        self.prompt_manager = PromptManager()
        self._rate_limiter = RateLimiter(self.RATE_LIMIT_PER_MINUTE)

        # Mock mode: explicit flag or auto-detect when no API key
        if mock_mode is not None:
            self.mock_mode = mock_mode
        else:
            self.mock_mode = not bool(self.api_key)

        if self.mock_mode:
            logger.warning("GeminiSummarizer running in MOCK mode (no API key)")

        # Cumulative usage tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.total_calls = 0

    async def summarize(self, article, language: str = "zh-TW") -> SummaryResult:
        """使用 Gemini 生成文章摘要。

        Args:
            article: Article object with 'title' and 'content' attributes,
                     or a dict with 'title' and 'content' keys.
            language: Target language for the summary (default: zh-TW).

        Returns:
            SummaryResult with structured summary data.
        """
        title = article.get("title", "") if isinstance(article, dict) else getattr(article, "title", "")
        content = article.get("content", "") if isinstance(article, dict) else getattr(article, "content", "")

        if self.mock_mode:
            return self._mock_summarize(title, content, language)

        client = self._get_client()
        user_prompt = self.prompt_manager.get_user_prompt(title, content)

        await self._rate_limiter.acquire()
        response = await self._call_with_retry(client, user_prompt)
        result = self._parse_response(response, language)
        self._track_usage(response)
        self.total_calls += 1
        return result

    def _get_client(self):
        """Initialize and return a google-genai Client."""
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai package is required. "
                "Install it with: pip install google-genai"
            )
        return genai.Client(api_key=self.api_key)

    async def summarize_batch(
        self, articles: list, max_concurrent: int = 3
    ) -> List[SummaryResult]:
        """批量摘要多篇文章（使用 semaphore 控制並發）。

        Args:
            articles: List of article objects or dicts.
            max_concurrent: Maximum concurrent API calls (default: 3).

        Returns:
            List of SummaryResult for each article. Failed articles
            return a SummaryResult with empty fields and error in raw_response.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _limited_summarize(article):
            async with semaphore:
                try:
                    return await self.summarize(article)
                except Exception as e:
                    title = (
                        article.get("title", "")
                        if isinstance(article, dict)
                        else getattr(article, "title", "unknown")
                    )
                    logger.error("Failed to summarize '%s': %s", title, e)
                    return SummaryResult(
                        model_used=self.model,
                        raw_response=f"ERROR: {e}",
                    )

        tasks = [_limited_summarize(article) for article in articles]
        return await asyncio.gather(*tasks)

    async def _call_with_retry(self, client, prompt: str):
        """Call Gemini API with exponential backoff on rate limit errors."""
        from google.genai import types
        config = types.GenerateContentConfig(
            system_instruction=self.prompt_manager.SYSTEM_PROMPT,
        )
        for attempt in range(self.MAX_RETRIES):
            try:
                return await client.aio.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
            except Exception as e:
                error_str = str(e).lower()
                is_retryable = (
                    "429" in error_str
                    or "rate" in error_str
                    or "quota" in error_str
                    or "resource_exhausted" in error_str
                )
                if not is_retryable or attempt == self.MAX_RETRIES - 1:
                    raise
                delay = self.BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Gemini API rate limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    self.MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)

    def _mock_summarize(self, title: str, content: str, language: str) -> SummaryResult:
        """Return a mock SummaryResult for testing without API key."""
        return SummaryResult(
            title_zh=f"[Mock] {title[:50]}",
            summary_zh=f"這是「{title[:20]}」的模擬摘要，用於測試環境。",
            key_points=["模擬重點 1", "模擬重點 2", "模擬重點 3"],
            tags=["mock", "test"],
            language=language,
            model_used="mock",
            cost_estimate_usd=0.0,
            raw_response=None,
        )

    def _parse_response(self, response, language: str) -> SummaryResult:
        """Parse Gemini API response into SummaryResult."""
        raw_text = response.text
        # Try to extract JSON from markdown code blocks if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json) and last line (```)
            json_lines = []
            for line in lines[1:]:
                if line.strip() == "```":
                    break
                json_lines.append(line)
            cleaned = "\n".join(json_lines)

        try:
            data = json.loads(cleaned)
            return SummaryResult(
                title_zh=data.get("title_zh", ""),
                summary_zh=data.get("summary_zh", ""),
                key_points=data.get("key_points", []),
                tags=data.get("tags", []),
                language=language,
                model_used=self.model,
                cost_estimate_usd=self._estimate_cost(response),
                raw_response=raw_text,
            )
        except (json.JSONDecodeError, AttributeError):
            logger.warning("Failed to parse Gemini response as JSON, using raw text")
            return SummaryResult(
                summary_zh=raw_text[:200] if raw_text else "",
                language=language,
                model_used=self.model,
                raw_response=raw_text,
            )

    def _track_usage(self, response) -> None:
        """Accumulate token usage across calls."""
        try:
            usage = response.usage_metadata
            self.total_input_tokens += getattr(usage, "prompt_token_count", 0)
            self.total_output_tokens += getattr(usage, "candidates_token_count", 0)
            self.total_cost_usd += self._estimate_cost(response)
        except (AttributeError, TypeError):
            pass

    def _estimate_cost(self, response) -> float:
        """Estimate API call cost in USD based on token usage."""
        try:
            usage = response.usage_metadata
            input_tokens = getattr(usage, "prompt_token_count", 0)
            output_tokens = getattr(usage, "candidates_token_count", 0)
            # Gemini 2.5 Flash pricing (approximate)
            input_cost = input_tokens * 0.00000015
            output_cost = output_tokens * 0.0000006
            return round(input_cost + output_cost, 6)
        except (AttributeError, TypeError):
            return 0.0

    def get_usage_summary(self) -> dict:
        """Return cumulative usage statistics."""
        return {
            "total_calls": self.total_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "model": self.model,
            "mock_mode": self.mock_mode,
        }
